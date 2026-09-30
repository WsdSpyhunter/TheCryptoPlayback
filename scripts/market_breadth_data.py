"""
market_breadth_data.py — storage and calculation for the Market Breadth
indicator: the share of a fixed universe of major coins trading above
their own 50-day and 200-day simple moving average. Same style as the
S&P 500 "% of stocks above their 200-day MA" breadth reading traders use
for stocks, applied to crypto.

Why we don't just call CoinGecko's per-coin historical-price endpoint:
computing a real 200-day SMA that way would mean 40 separate historical
lookups every refresh, for no benefit (the data doesn't change retroactively
enough to justify re-fetching it). Instead we build our own history
one day at a time: one markets call/day (see fetch_market_breadth.py)
appends one price per tracked coin to data/market_breadth.json, and the
SMA windows are computed from that accumulating store. This means a real
200-day SMA isn't available until ~200 calendar days after this indicator
first shipped - see `have_200`/`available_days` below, which exist so the
site always says how much real history backs a number instead of quietly
mislabeling a shorter window as 200D.

The 40-coin universe is locked in on the very first successful ingest
(the top 40 non-stablecoin, non-wrapped coins by market cap that day) and
never silently reshuffled - a breadth reading only means something if it's
tracking the same set of coins over time, the same reason the S&P 500
itself only rebalances a few times a year instead of daily. A coin that
temporarily drops out of CoinGecko's fetched buffer just has a gap for
that day (excluded from that day's eligible set below) rather than being
swapped out.
"""
import json
import os
from datetime import datetime, timezone

from fetch_market_breadth import get_market_snapshot

MARKET_BREADTH_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "market_breadth.json")
UNIVERSE_SIZE = 40
FETCH_BUFFER = 60  # fetched per call, so filtering stablecoins/wrapped tokens still leaves 40
MAX_STORED_SNAPSHOTS = 400  # comfortably above the 200 the longest SMA needs

BREADTH_LABELS = (
    (70, "Broad Strength"),
    (55, "Above Average"),
    (45, "Mixed"),
    (30, "Below Average"),
)


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_store():
    if not os.path.exists(MARKET_BREADTH_FILE):
        return {"universe": [], "snapshots": []}
    with open(MARKET_BREADTH_FILE) as f:
        return json.load(f)


def _save_store(store):
    os.makedirs(os.path.dirname(MARKET_BREADTH_FILE), exist_ok=True)
    with open(MARKET_BREADTH_FILE, "w") as f:
        json.dump(store, f, indent=2)


def ingest_and_store():
    store = load_store()
    today = _today()

    if store["snapshots"] and store["snapshots"][-1]["date"] == today:
        return store  # already captured today's snapshot - this runs a few times a day

    fetched = get_market_snapshot(fetch_count=FETCH_BUFFER)
    if not fetched:
        return store  # transient API failure - never write a partial/empty snapshot

    if not store["universe"]:
        store["universe"] = [c["id"] for c in fetched[:UNIVERSE_SIZE]]

    universe = set(store["universe"])
    prices_today = {c["id"]: c["price"] for c in fetched if c["id"] in universe}
    store["snapshots"].append({"date": today, "prices": prices_today})
    store["snapshots"] = store["snapshots"][-MAX_STORED_SNAPSHOTS:]

    _save_store(store)
    return store


def _breadth_label(pct):
    for threshold, label in BREADTH_LABELS:
        if pct >= threshold:
            return label
    return "Broad Weakness"


def compute_breadth(store):
    """Returns None only before the very first successful ingest. Otherwise
    always returns a dict - pct_above_50 is None until day 50, at which
    point it becomes the headline reading; pct_above_200 stays None
    (with have_200=False) until day 200."""
    universe = store.get("universe") or []
    snapshots = store.get("snapshots") or []
    if not universe or not snapshots:
        return None

    available_days = len(snapshots)
    today_prices = snapshots[-1]["prices"]

    coin_series = {}
    for coin_id in universe:
        series = [snap["prices"][coin_id] for snap in snapshots if coin_id in snap["prices"]]
        coin_series[coin_id] = series

    def _pct_above(window):
        eligible = [cid for cid in universe if cid in today_prices and len(coin_series[cid]) >= window]
        if not eligible:
            return None, 0
        above = sum(1 for cid in eligible if today_prices[cid] > sum(coin_series[cid][-window:]) / window)
        return round(100 * above / len(eligible)), len(eligible)

    pct_50, eligible_50 = _pct_above(50)
    pct_200, eligible_200 = _pct_above(200)
    have_200 = pct_200 is not None

    history = [
        {"date": snap["date"], "pct_above_50": None}
        for snap in snapshots
    ]
    # Recompute each historical day's pct_above_50 from that day's own trailing
    # window rather than reusing today's, so the sparkline reflects what
    # breadth actually was that day, not a flat repeat of today's number.
    for i, snap in enumerate(snapshots):
        day_prices = snap["prices"]
        eligible = [cid for cid in universe if cid in day_prices and
                    sum(1 for s in snapshots[:i + 1] if cid in s["prices"]) >= 50]
        if not eligible:
            continue
        above = 0
        for cid in eligible:
            series_to_day = [s["prices"][cid] for s in snapshots[:i + 1] if cid in s["prices"]]
            if day_prices[cid] > sum(series_to_day[-50:]) / 50:
                above += 1
        history[i]["pct_above_50"] = round(100 * above / len(eligible))

    history = [h for h in reversed(history) if h["pct_above_50"] is not None][:12]

    return {
        "latest_date": snapshots[-1]["date"],
        "available_days": available_days,
        "universe_size": len(universe),
        "pct_above_50": pct_50,
        "eligible_50": eligible_50,
        "have_50": pct_50 is not None,
        "pct_above_200": pct_200,
        "eligible_200": eligible_200,
        "have_200": have_200,
        "label": _breadth_label(pct_50) if pct_50 is not None else None,
        "history": history,
    }


if __name__ == "__main__":
    s = ingest_and_store()
    print(json.dumps(compute_breadth(s), indent=2))
