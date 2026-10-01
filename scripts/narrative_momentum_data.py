"""
narrative_momentum_data.py — storage and calculation for the Narrative
Momentum indicator: which crypto sector/narrative has shown the strongest
*sustained* (7-day average) performance, as opposed to Top Sectors' same-day
snapshot ranking. A sector can spike for one day without having been
genuinely strong over the week, or grind steadily upward all week without
topping today's leaderboard - this indicator is about the latter.

Needs zero new API calls: it reuses the sector data refresh_indicators.py
already fetches every 15 minutes (fetch_sectors.py) and just remembers one
snapshot per calendar day, the same "build our own history one day at a
time" pattern market_breadth_data.py uses for its SMA windows - except this
one is cheap enough to run from inside refresh_indicators.py directly
rather than needing its own decoupled workflow, since no extra fetch is
involved.
"""
import json
import os
from datetime import datetime, timezone

NARRATIVE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "narrative_momentum.json")
TREND_WINDOW_DAYS = 7
MAX_STORED_SNAPSHOTS = 30  # comfortably above the 7-day window


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_store():
    if not os.path.exists(NARRATIVE_FILE):
        return {"snapshots": []}
    with open(NARRATIVE_FILE) as f:
        return json.load(f)


def _save_store(store):
    os.makedirs(os.path.dirname(NARRATIVE_FILE), exist_ok=True)
    with open(NARRATIVE_FILE, "w") as f:
        json.dump(store, f, indent=2)


def ingest_and_store(sectors):
    """`sectors` is the list already fetched this refresh (fetch_sectors.py)
    - [{'label': ..., 'change_24h': ...}, ...]. Stores at most one snapshot
    per calendar day (first successful run of the day), same dedup
    reasoning as market_breadth_data.py."""
    store = load_store()
    today = _today()

    if store["snapshots"] and store["snapshots"][-1]["date"] == today:
        return store

    if not sectors:
        return store

    store["snapshots"].append({
        "date": today,
        "sectors": {s["label"]: s["change_24h"] for s in sectors},
    })
    store["snapshots"] = store["snapshots"][-MAX_STORED_SNAPSHOTS:]
    _save_store(store)
    return store


def compute_momentum(store):
    """Returns None only before the first successful ingest. Otherwise
    ranks every sector seen by its trailing-N-day average daily change
    (N = however many days are actually stored, up to TREND_WINDOW_DAYS) -
    `have_7d` is False until a real 7 days of history exists, so a 2-day
    average is never silently mislabeled as "weekly" momentum."""
    snapshots = store.get("snapshots") or []
    if not snapshots:
        return None

    window = snapshots[-TREND_WINDOW_DAYS:]
    available_days = len(window)

    labels = set()
    for snap in window:
        labels.update(snap["sectors"].keys())

    ranked = []
    for label in labels:
        values = [snap["sectors"][label] for snap in window if label in snap["sectors"]]
        if values:
            ranked.append({"label": label, "avg_change_pct": sum(values) / len(values), "days": len(values)})
    ranked.sort(key=lambda r: r["avg_change_pct"], reverse=True)

    # One row per day a full trailing window was available, each showing
    # that day's own leading sector as of that day - not just today's
    # leader repeated, and not a single day's raw change pretending to be
    # a 7-day read. Same "recompute from only the data available at that
    # point" discipline market_breadth_data.py uses for its history.
    history = []
    for i in range(TREND_WINDOW_DAYS - 1, len(snapshots)):
        day_window = snapshots[i - TREND_WINDOW_DAYS + 1:i + 1]
        day_labels = set()
        for snap in day_window:
            day_labels.update(snap["sectors"].keys())
        day_avgs = {}
        for label in day_labels:
            values = [snap["sectors"][label] for snap in day_window if label in snap["sectors"]]
            if values:
                day_avgs[label] = sum(values) / len(values)
        if day_avgs:
            leader_label = max(day_avgs, key=day_avgs.get)
            history.append({"date": snapshots[i]["date"], "leader_label": leader_label,
                             "leader_avg": day_avgs[leader_label]})
    history.reverse()

    return {
        "latest_date": snapshots[-1]["date"],
        "available_days": available_days,
        "have_7d": available_days >= TREND_WINDOW_DAYS,
        "ranked": ranked,
        "history": history[:12],
    }


if __name__ == "__main__":
    s = load_store()
    print(json.dumps(compute_momentum(s), indent=2))
