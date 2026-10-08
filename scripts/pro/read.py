"""The Playback Read: a transparent tally of the Lab's indicators.

No blended score and no invented weights. Each indicator with a clear direction is sorted into
Supportive / Neutral / Caution using fixed thresholds, then counted. The Regulatory Tracker has no
good or bad direction, so it is shown as a note and does not vote.

  Positioning      z >= +1 Supportive, z <= -1 Caution
  Basis crowding   score >= 55 Caution, <= 20 Supportive (little crowding to unwind)
  Miner stress     score >= 70 Caution, < 30 Supportive
  Macro backdrop   score >= 62 Supportive, <= 38 Caution
  Unwind risk      median crowding across the ten tracked markets >= 55 Caution, < 35 Supportive
  Stablecoins      7-day supply change >= +0.5% Supportive, <= -0.5% Caution

"Caution" means stretched or stressed, not "bearish": miner capitulation, for instance, has often
clustered near lows. It is a descriptive summary of the other sections, not a forecast.

Each run saves today's tally (US Central date) to data/pro/read_history.json, so the page can show a
public, timestamped record that starts the day this went live and grows from there.
"""
import json
import os
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
    CT = ZoneInfo("America/Chicago")
except Exception:       # noqa: BLE001
    CT = timezone(timedelta(hours=-5))

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "pro")
HIST = os.path.join(DATA, "read_history.json")
ORDER = ["liquidity", "pressure", "basis", "stables", "unwind", "miners"]
NAMES = {"liquidity": "Macro backdrop", "pressure": "Institutional positioning", "basis": "Basis-trade crowding",
         "stables": "Stablecoin flows", "unwind": "Crowded unwind risk", "miners": "Miner stress"}
ANCHOR = {"liquidity": "liquidity", "pressure": "pressure", "basis": "basis", "stables": "stables", "unwind": "unwind", "miners": "miners"}


def _load(name):
    try:
        return json.load(open(os.path.join(DATA, f"{name}.json")))
    except (OSError, ValueError):
        return None


def _median(xs):
    xs = sorted(xs)
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def classify():
    out = {}
    p = _load("pressure")
    if p:
        z = p["score_z"]
        out["pressure"] = ("Supportive" if z >= 1 else "Caution" if z <= -1 else "Neutral", f"{z:+.2f} · {p['regime']}")
    b = _load("basis")
    if b:
        s = b["score"]
        out["basis"] = ("Caution" if s >= 55 else "Supportive" if s <= 20 else "Neutral", f"{s:.0f} · {b['label']}, {b['phase'].lower()}")
    m = _load("miners")
    if m:
        s = m["stress"]["score"]
        out["miners"] = ("Caution" if s >= 70 else "Supportive" if s < 30 else "Neutral", f"{s:.0f} · {m['stress']['label']}")
    lq = _load("liquidity")
    if lq:
        s = lq["backdrop"]["score"]
        out["liquidity"] = ("Supportive" if s >= 62 else "Caution" if s <= 38 else "Neutral", f"{s:.0f} · {lq['backdrop']['label']}")
    u = _load("unwind")
    if u and u.get("assets"):
        med = _median([a["score"] for a in u["assets"]])
        out["unwind"] = ("Caution" if med >= 55 else "Supportive" if med < 35 else "Neutral", f"median {med:.0f} · highest {u['assets'][0]['symbol']} {u['assets'][0]['score']:.0f}")
    st = _load("stables")
    if st:
        c = st["totals"]["change_7d_pct"]
        out["stables"] = ("Supportive" if c >= 0.5 else "Caution" if c <= -0.5 else "Neutral", f"{c:+.2f}% in 7 days · {st['flow']['label'].lower()}")
    return out


def load_history():
    try:
        return json.load(open(HIST))
    except (OSError, ValueError):
        return []


def compute():
    cls = classify()
    if len(cls) < 3:
        raise RuntimeError("not enough indicators to build the read")
    labels = {k: v[0] for k, v in cls.items()}
    counts = {k: sum(1 for v in labels.values() if v == k) for k in ("Supportive", "Neutral", "Caution")}
    today = datetime.now(CT).strftime("%Y-%m-%d")
    hist = [h for h in load_history() if h["d"] != today]
    hist.append({"d": today, "labels": labels, **{k.lower(): v for k, v in counts.items()}})
    hist = hist[-400:]
    json.dump(hist, open(HIST, "w"), separators=(",", ":"))

    # what changed: compare with the entry closest to 7 days ago, else the previous entry
    prior = None
    if len(hist) > 1:
        want = datetime.strptime(today, "%Y-%m-%d") - timedelta(days=7)
        prior = min(hist[:-1], key=lambda h: abs((datetime.strptime(h["d"], "%Y-%m-%d") - want).days))
    changes = []
    if prior:
        for k in ORDER:
            if k in labels and prior["labels"].get(k) and prior["labels"][k] != labels[k]:
                changes.append({"key": k, "name": NAMES[k], "from": prior["labels"][k], "to": labels[k]})

    sup = [NAMES[k] for k in ORDER if labels.get(k) == "Supportive"]
    cau = [NAMES[k] for k in ORDER if labels.get(k) == "Caution"]
    neu = [NAMES[k] for k in ORDER if labels.get(k) == "Neutral"]
    n = len(labels)
    parts = [f"{counts['Supportive']} of {n} readings {'is' if counts['Supportive'] == 1 else 'are'} supportive, {counts['Neutral']} neutral and {counts['Caution']} cautionary."]
    if sup and cau:
        parts.append(f"The readings disagree: {_join(sup)} {'is' if len(sup) == 1 else 'are'} supportive while {_join(cau)} {'is' if len(cau) == 1 else 'are'} flashing caution.")
    elif cau:
        parts.append(f"Caution is coming from {_join(cau)}.")
    elif sup:
        parts.append(f"Support is coming from {_join(sup)}.")
    else:
        parts.append("Nothing is pushing hard in either direction.")
    if neu and (sup or cau):
        parts.append(f"{_join(neu).capitalize()} {'is' if len(neu) == 1 else 'are'} neutral.")
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok",
        "counts": counts, "total": n, "indicators": [{"key": k, "name": NAMES[k], "label": cls[k][0], "detail": cls[k][1]} for k in ORDER if k in cls],
        "changes": changes, "since": prior["d"] if prior else None, "summary": " ".join(parts),
        "history": [{"d": h["d"], "s": h["supportive"], "n": h["neutral"], "c": h["caution"]} for h in hist[-120:]],
        "tracking_since": hist[0]["d"],
    }


def _join(xs):
    xs = [x.lower() for x in xs]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


if __name__ == "__main__":
    print(json.dumps(compute(), indent=1))
