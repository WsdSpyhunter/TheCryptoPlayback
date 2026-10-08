"""Crowded Unwind Risk Map, Open Edition: on-chain perpetuals (Hyperliquid).

For each of ten large markets, a 0-100 score of how crowded and fragile positioning on the
largest on-chain perpetual-futures exchange looks. Higher = more stretched, so a leveraged
unwind (a liquidation cascade) would hit harder. Every component is a percentile of the coin's
OWN trailing 30 days, so a coin is compared with itself, not with Bitcoin.

  Premium            45%  how far the perp trades from its oracle (index) price: |premium| versus its own
                          history. A persistent premium means buyers are paying up to hold leveraged longs
                          (or sellers to hold shorts). This is the main crowding signal on Hyperliquid.
  Funding excess     25%  funding ABOVE OR BELOW Hyperliquid's fixed interest floor (0.01% per 8h; funding
                          sits exactly on that floor whenever the market is balanced, so raw funding would
                          falsely look "elevated"): 60% extremity of |excess| versus its own history +
                          40% persistence (share of the last 24 hours at the same sign and at least
                          median size; nothing counts while funding sits on the floor).
  Open interest      15%  current open interest (USD) versus its own range. Hyperliquid publishes no
                          open-interest history, so this is built from our own snapshots
                          (data/pro/hl_snapshots.json) and shows "building" for roughly the first two
                          days; the other components are re-weighted until then.
  Adverse move       15%  the 24-hour price move AGAINST the crowded side (a fall when longs dominate, a
                          rally when shorts dominate): the stress that forces unwinds.

Direction (crowded long / crowded short / balanced) is a vote between the sign of the premium
(beyond +/-1 bp) and the sign of the funding excess.

Why only Hyperliquid: the other on-chain perp venue checked (dYdX) is 100 to 500 times smaller
(BTC open interest about $19M versus about $3.3B), so it would add noise, not information.

Not modelled (no free data): long/short account ratios, liquidation clusters and order-book
depth, cross-exchange crowding. This map describes ON-CHAIN perp traders, a large and fast-moving
group but not the whole market.
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import derivs
from .net import post_json
from .stats import percentile_rank, pct_change

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAP_FILE = os.path.join(ROOT, "data", "pro", "hl_snapshots.json")
HL = "https://api.hyperliquid.xyz/info"
HOUR = 3600
WEIGHTS = {"premium": 0.45, "funding": 0.25, "oi": 0.15, "adverse": 0.15}
BASE_FUNDING_8H = 0.0001      # Hyperliquid interest floor: 0.01% per 8 hours
MIN_WINDOW = 168
WINDOW = 720
MIN_OI_SNAPS = 48


def _sign(x, eps=0.0):
    return 1 if x > eps else (-1 if x < -eps else 0)


def _label(score):
    return "Extreme" if score >= 75 else "High" if score >= 55 else "Moderate" if score >= 35 else "Low"


def load_snaps():
    try:
        return json.load(open(SNAP_FILE))
    except (OSError, ValueError):
        return {}


def record_snapshots():
    """Append the current open interest and mark price for every tracked asset."""
    snap = derivs.snapshot_hyperliquid()
    store = load_snaps()
    now = int(time.time())
    cutoff = now - 40 * 86400
    for a, d in snap.items():
        if d.get("oi_usd") and d.get("mark"):
            store.setdefault(a, []).append([now, d["oi_usd"], d["mark"]])
    for a in list(store):
        store[a] = [s for s in store[a] if s[0] >= cutoff]
    os.makedirs(os.path.dirname(SNAP_FILE), exist_ok=True)
    json.dump(store, open(SNAP_FILE, "w"), separators=(",", ":"))
    return store, snap


def fetch_funding_premium(asset, days=30):
    """{hour_ts: (funding_8h, premium)} from Hyperliquid fundingHistory (500-row pages)."""
    start = int((time.time() - days * 86400) * 1000)
    out = {}
    for _ in range(6):
        rows = post_json(HL, {"type": "fundingHistory", "coin": asset, "startTime": start})
        if not rows:
            break
        for r in rows:
            t = int(r["time"]) // 1000 // HOUR * HOUR
            out[t] = (float(r["fundingRate"]) * 8.0, float(r["premium"]))
        nxt = int(rows[-1]["time"]) + 1
        if len(rows) < 400 or nxt <= start:
            break
        start = nxt
    return out


def fetch_candles(asset, days=30):
    now = int(time.time() * 1000)
    rows = post_json(HL, {"type": "candleSnapshot", "req": {"coin": asset, "interval": "1h", "startTime": now - days * 86400 * 1000, "endTime": now}})
    return {int(r["t"]) // 1000: float(r["c"]) for r in rows}


def _score_at(i, fund, prem, ret24, oi, direction):
    lo = max(0, i - WINDOW + 1)
    # funding
    fw = [abs(x) for x in fund[lo:i + 1] if x is not None]
    f = fund[i]
    f_c = None
    if f is not None and fw:
        ext = percentile_rank(abs(f), fw)
        med = sorted(fw)[len(fw) // 2]
        last24 = [x for x in fund[max(0, i - 23):i + 1] if x is not None]
        if abs(f) < 1e-9:
            pers = 0.0                      # funding on its floor: no persistence to count
        else:
            pers = 100.0 * sum(1 for v in last24 if _sign(v) == _sign(f) and abs(v) >= max(med, 1e-9)) / max(1, len(last24))
        f_c = 0.6 * ext + 0.4 * pers
    # premium
    pw = [abs(x) for x in prem[lo:i + 1] if x is not None]
    p_c = percentile_rank(abs(prem[i]), pw) if prem[i] is not None and pw else None
    # open interest
    ow = [x for x in oi[lo:i + 1] if x is not None]
    o_c = percentile_rank(oi[i], ow) if oi[i] is not None and len(ow) >= MIN_OI_SNAPS else None
    # adverse move
    adv = []
    for j in range(lo, i + 1):
        rj, d = ret24[j], direction[j]
        adv.append(None if rj is None or d == 0 else max(0.0, -rj if d > 0 else rj))
    a_now = adv[-1]
    a_c = percentile_rank(a_now, [v for v in adv if v is not None]) if a_now is not None else None
    comps = {"funding": f_c, "premium": p_c, "oi": o_c, "adverse": a_c}
    num = den = 0.0
    for k, w in WEIGHTS.items():
        if comps[k] is not None:
            num += w * comps[k]
            den += w
    return comps, (num / den if den else None)


def analyse(asset, snaps):
    fp = fetch_funding_premium(asset)
    px = fetch_candles(asset)
    if len(fp) < MIN_WINDOW + 24 or len(px) < MIN_WINDOW:
        return None
    t0 = max(min(fp), min(px))
    t1 = min(max(fp), max(px))
    grid = list(range(t0, t1 + HOUR, HOUR))
    fund = [fp[t][0] - BASE_FUNDING_8H if t in fp else None for t in grid]       # excess over the interest floor
    prem = [fp[t][1] if t in fp else None for t in grid]
    close = [px.get(t) for t in grid]
    ret24 = pct_change(close, 24)
    # open interest from our snapshots, forward-filled to hours (carry at most 3 hours)
    oi = [None] * len(grid)
    srt = sorted(snaps.get(asset, []))
    k, cur, cur_t = 0, None, None
    for i, t in enumerate(grid):
        while k < len(srt) and srt[k][0] // HOUR * HOUR <= t:
            cur, cur_t = srt[k][1], srt[k][0] // HOUR * HOUR
            k += 1
        oi[i] = cur if cur is not None and t - cur_t <= 3 * HOUR else None
    direction = []
    for f, p in zip(fund, prem):
        v = (_sign(f, 1e-5) if f is not None else 0) + (_sign(p, 1e-4) if p is not None else 0)
        direction.append(_sign(v))
    n = len(grid)
    hist = []
    for i in range(MIN_WINDOW, n):
        if grid[i] % 86400 == 0 or i == n - 1:
            c, s = _score_at(i, fund, prem, ret24, oi, direction)
            if s is not None:
                hist.append({"t": grid[i], "score": round(s, 1)})
    comps, score = _score_at(n - 1, fund, prem, ret24, oi, direction)
    if score is None:
        return None
    d = direction[-1]
    return {
        "symbol": asset, "score": round(score, 1), "label": _label(score),
        "direction": "Balanced" if (d == 0 or _label(score) == "Low") else ("Crowded long" if d > 0 else "Crowded short"),
        "components": {k2: (None if v is None else round(v)) for k2, v in comps.items()},
        "funding_8h": None if fund[-1] is None else fund[-1] + BASE_FUNDING_8H, "funding_excess_8h": fund[-1], "premium_bps": None if prem[-1] is None else prem[-1] * 1e4,
        "price_24h_pct": ret24[-1], "oi_usd": next((x for x in reversed(oi) if x is not None), None),
        "history": hist[-14:],
    }


def compute():
    store, snap = record_snapshots()
    errors = {}

    def one(a):
        try:
            return analyse(a, store)
        except Exception as exc:        # noqa: BLE001
            errors[a] = str(exc)[:120]
            return None

    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(one, derivs.ASSETS))
    assets = [r for r in results if r]
    if not assets:
        raise RuntimeError("no assets could be scored")
    for r in assets:                      # live OI straight from the latest snapshot
        d = snap.get(r["symbol"])
        if d and d.get("oi_usd"):
            r["oi_usd"] = d["oi_usd"]
    assets.sort(key=lambda x: -x["score"])
    n_snaps = max((len(v) for v in store.values()), default=0)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok",
        "weights": WEIGHTS, "assets": assets, "failed_assets": sorted(errors), "errors": errors,
        "oi_snapshots": n_snaps, "oi_building": n_snaps < MIN_OI_SNAPS,
        "venue": "Hyperliquid",
    }


if __name__ == "__main__":
    out = compute()
    for a in out["assets"]:
        print(f"{a['symbol']:5s} {a['score']:5.1f} {a['label']:9s} {a['direction']:13s} {a['components']} "
              f"fund8h {a['funding_8h']*100:+.4f}% (excess {a['funding_excess_8h']*100:+.4f}%) prem {a['premium_bps']:+.1f}bps 24h {a['price_24h_pct']:+.1f}% hist {len(a['history'])}")
    print("failed:", out["failed_assets"], "| OI snapshots:", out["oi_snapshots"], "| building:", out["oi_building"])
