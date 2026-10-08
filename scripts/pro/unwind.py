"""Crowded Unwind Risk Map.

For each of ten large perpetual-futures markets, a 0-100 score of how
crowded and fragile positioning looks: the higher the score, the more
vulnerable the market is to a leveraged unwind (a liquidation cascade).

Everything is scored on hourly Gate.io contract statistics (free, 30+ days of
history, so the score has real history from the first run), and every
component is a PERCENTILE of the asset's own trailing 30 days, so a coin is
compared with itself, not with Bitcoin.

  OI crowding      30%  open interest (USD) vs its own 30-day range
  Funding          30%  60% extremity of |funding| vs own history + 40%
                        persistence (share of the last 24h at the same sign
                        and at least median size)
  Long/short skew  20%  how far the long/short account ratio sits from its own
                        30-day median, |ln(ratio / median)|, vs own history
  Liquidation heat 10%  24h liquidations (USD) as a share of OI vs own history
  Adverse move     10%  24h price move AGAINST the crowded side (a drop when
                        longs dominate, a rally when shorts dominate): the
                        stress that triggers forced selling/covering

Direction (crowded long / crowded short / balanced) is a vote between the sign
of funding and the sign of the long/short ratio's deviation from its median
(account ratios run long-heavy on every exchange, so level alone is not a signal).

Cross-venue context (current OI and funding on OKX, Hyperliquid, Bitget,
Deribit, Kraken) is attached for display; it does not change the score, so
the live score and its history are computed identically.

Not available for free and therefore NOT modelled: liquidation-price cluster
maps and order-book depth. "Liquidation heat" and "adverse move" are
proxies for that, not substitutes. Liquidation volumes are those observed on
Gate.io (a sample of the market, not the total).
"""
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import derivs
from .stats import percentile_rank, pct_change

WEIGHTS = {"oi": 0.30, "funding": 0.30, "lsr": 0.20, "liq": 0.10, "adverse": 0.10}
MIN_WINDOW = 168      # 7 days of hourly points before a score is produced
WINDOW = 720


def _sign(x, eps=0.0):
    return 1 if x > eps else (-1 if x < -eps else 0)


def _label(score):
    return "Extreme" if score >= 75 else "High" if score >= 55 else "Moderate" if score >= 35 else "Low"


def score_at(rows, i, liq_ratio, ret24, direction_hist, lsr_dev):
    """Component percentiles (0-100) and weighted score at hourly index i."""
    lo = max(0, i - WINDOW + 1)
    win = rows[lo:i + 1]
    r = rows[i]
    oi_c = percentile_rank(r["oi_usd"], [x["oi_usd"] for x in win])
    fabs = [abs(x["funding"]) for x in win if x["funding"] is not None]
    f = r["funding"]
    if f is None or not fabs:
        f_c = None
    else:
        ext = percentile_rank(abs(f), fabs)
        med = sorted(fabs)[len(fabs) // 2]
        last24 = [x["funding"] for x in rows[max(0, i - 23):i + 1] if x["funding"] is not None]
        pers = 100.0 * sum(1 for v in last24 if _sign(v) == _sign(f) and abs(v) >= med) / max(1, len(last24))
        f_c = 0.6 * ext + 0.4 * pers
    skew = [abs(v) for v in lsr_dev[lo:i + 1] if v is not None]
    l_c = percentile_rank(abs(lsr_dev[i]), skew) if lsr_dev[i] is not None and skew else None
    liq_c = percentile_rank(liq_ratio[i], [v for v in liq_ratio[lo:i + 1] if v is not None]) if liq_ratio[i] is not None else None
    adv_series = []
    for j in range(lo, i + 1):
        rj = ret24[j]
        d = direction_hist[j]
        adv_series.append(None if rj is None or d == 0 else max(0.0, -rj if d > 0 else rj))
    a_now = adv_series[-1]
    a_c = percentile_rank(a_now, [v for v in adv_series if v is not None]) if a_now is not None else None
    comps = {"oi": oi_c, "funding": f_c, "lsr": l_c, "liq": liq_c, "adverse": a_c}
    num = den = 0.0
    for k, w in WEIGHTS.items():
        if comps[k] is not None:
            num += w * comps[k]
            den += w
    return comps, (num / den if den else None)


def analyse_asset(asset, rows):
    n = len(rows)
    if n < MIN_WINDOW + 24:
        return None
    # rolling 24h liquidation / OI
    liq = [(r["long_liq_usd"] or 0) + (r["short_liq_usd"] or 0) for r in rows]
    liq_ratio = []
    for i in range(n):
        s = sum(liq[max(0, i - 23):i + 1])
        liq_ratio.append(s / rows[i]["oi_usd"] if rows[i]["oi_usd"] else None)
    ret24 = pct_change([r["mark"] for r in rows], 24)
    ln_lsr = [math.log(r["lsr_account"]) if r["lsr_account"] and r["lsr_account"] > 0 else None for r in rows]
    lsr_dev = []
    for i in range(n):
        past = sorted(v for v in ln_lsr[max(0, i - WINDOW + 1):i + 1] if v is not None)
        lsr_dev.append(None if ln_lsr[i] is None or not past else ln_lsr[i] - past[len(past) // 2])
    direction = []
    for i, r in enumerate(rows):
        v = 0
        if r["funding"]:
            v += _sign(r["funding"])
        if lsr_dev[i] is not None:
            v += _sign(lsr_dev[i], 0.03)
        direction.append(_sign(v))
    # daily history (00:00 UTC points) from the first scoreable hour
    hist = []
    for i in range(MIN_WINDOW, n):
        if rows[i]["t"] % 86400 == 0 or i == n - 1:
            c, s = score_at(rows, i, liq_ratio, ret24, direction, lsr_dev)
            if s is not None:
                hist.append({"t": rows[i]["t"], "score": round(s, 1)})
    comps, score = score_at(rows, n - 1, liq_ratio, ret24, direction, lsr_dev)
    last = rows[-1]
    d = direction[-1]
    return {
        "symbol": asset,
        "score": round(score, 1), "label": _label(score),
        "direction": "Crowded long" if d > 0 else "Crowded short" if d < 0 else "Balanced",
        "components": {k: (None if v is None else round(v)) for k, v in comps.items()},
        "oi_gate_usd": last["oi_usd"],
        "oi_vs_30d_avg": last["oi_usd"] / (sum(r["oi_usd"] for r in rows[-WINDOW:]) / len(rows[-WINDOW:])),
        "lsr_gate": last["lsr_account"],
        "liq_24h_usd_gate": sum(liq[-24:]),
        "price_24h_pct": ret24[-1],
        "history": hist[-14:],
    }


def compute():
    snaps, snap_err = derivs.collect_snapshots()

    def one(a):
        try:
            rows = derivs.history_gate(a, WINDOW)
            res = analyse_asset(a, rows)
            try:
                lsr = derivs.history_okx_lsr(a)
                if res and lsr:
                    res["lsr_okx"] = lsr[-1]["lsr"]
            except Exception:       # noqa: BLE001  (OKX ratio is optional context)
                pass
            return res
        except Exception as exc:    # noqa: BLE001
            return {"symbol": a, "error": str(exc)[:140]}

    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(one, derivs.ASSETS))

    assets, failed = [], []
    for r in results:
        if not r or "error" in r:
            failed.append(r["symbol"] if r else "?")
            continue
        agg = derivs.aggregate_asset(snaps, r["symbol"])
        if agg:
            r["oi_all_venues_usd"] = agg["oi_usd"]
            r["funding_8h_agg"] = agg["funding_8h"]
            r["funding_dispersion"] = agg["funding_dispersion"]
            r["venues"] = agg["venues"]
        assets.append(r)
    assets.sort(key=lambda x: -x["score"])
    if not assets:
        raise RuntimeError("no assets could be scored")
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "ok", "weights": WEIGHTS,
        "assets": assets, "failed_assets": failed,
        "venues_ok": sorted(snaps), "venue_errors": snap_err,
    }


if __name__ == "__main__":
    import json
    out = compute()
    for a in out["assets"]:
        print(f"{a['symbol']:5s} {a['score']:5.1f} {a['label']:9s} {a['direction']:13s} {a['components']} "
              f"OI x{a['oi_vs_30d_avg']:.2f} lsr {a['lsr_gate']:.2f} fund8h {a.get('funding_8h_agg', 0)*100:+.4f}% hist {len(a['history'])}")
    print("failed:", out["failed_assets"], "venue errors:", out["venue_errors"])
