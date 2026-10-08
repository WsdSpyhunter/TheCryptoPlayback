"""Basic Institutional Pressure Index.

A single read on whether US-institution-style demand is pressing on Bitcoin,
built from four documented components. Each component is turned into a
trailing z-score (compared only with its own PAST values, so there is no
look-ahead), the z-scores are blended with configurable weights, and the
blend is shown both as a z-score (about -2..+2) and a 0-100 percentile.

  1. ETF net flow         spot Bitcoin ETF daily net flow; 50% 1-day flow,
                          50% rolling 5-day sum. A day's flow counts from the
                          next 00:00 UTC (it is published after the US close).
  2. Coinbase Premium     Coinbase BTC-USD vs OKX BTC-USDT (dollar-adjusted);
                          50% 6-hour mean, 50% 24-hour mean.
  3. Funding pressure     OI-weighted perpetual funding (per 8h) across OKX,
                          Gate and Hyperliquid. Positive = longs paying shorts.
  4. OI x price           24h % change in aggregate BTC open interest (Gate +
                          OKX) signed by the 24h price direction. Rising OI in
                          a rising market = new longs (+); rising OI in a
                          falling market = new shorts (-); falling OI in a
                          rising market (short covering) scores weak.

Regime: z >= +1.0 Strong Buy Pressure, z <= -1.0 Strong Sell Pressure,
otherwise Neutral. This is a descriptive gauge, not a forecast.
"""
import json
import os
import time
from datetime import datetime, timezone, timedelta

from . import derivs, premium
from .stats import (zscore_series, rolling_mean, pct_change, ffill, norm_cdf, mean, clip)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_WEIGHTS = {"etf": 0.30, "premium": 0.20, "funding": 0.25, "oi": 0.25}
LABELS = {"etf": "ETF net flow", "premium": "Coinbase Premium",
          "funding": "Funding pressure", "oi": "Open interest x price"}
HOUR = 3600


def _hour(t):
    return int(t) // HOUR * HOUR


def load_etf_daily():
    """[(date, net_flow_usd)] oldest first from the site's own ETF dataset."""
    p = os.path.join(ROOT, "data", "etf_flows.json")
    try:
        obs = json.load(open(p)).get("observations", {})
    except (OSError, ValueError):
        return []
    rows = []
    for d, o in obs.items():
        try:
            rows.append((d, float(o["total_net_flow_usd"])))
        except (KeyError, TypeError, ValueError):
            pass
    return sorted(rows)


def _etf_component(daily, grid):
    """Hourly z-series for ETF flow (with the next-midnight availability lag)."""
    if len(daily) < 10:
        return [None] * len(grid), None
    flows = [f for _, f in daily]
    five = [sum(flows[max(0, i - 4):i + 1]) if i >= 4 else None for i in range(len(flows))]
    z1 = zscore_series(flows, min_window=8, max_window=120)
    z5 = zscore_series(five, min_window=8, max_window=120)
    daily_z = []
    for a, b in zip(z1, z5):
        vals = [x for x in (a, b) if x is not None]
        daily_z.append(sum(vals) / len(vals) if vals else None)
    avail = {}
    for (d, _), z in zip(daily, daily_z):
        t = int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + 86400
        avail[t] = z
    keys = sorted(avail)
    out, j, cur = [], 0, None
    for t in grid:
        while j < len(keys) and keys[j] <= t:
            cur = avail[keys[j]]
            j += 1
        out.append(cur)
    last_day = daily[-1]
    return out, {"date": last_day[0], "flow": last_day[1],
                 "five_day": sum(flows[-5:]), "z": daily_z[-1]}


def _resample(rows, key, grid, hold_hours=None):
    by = {_hour(r["t"]): r[key] for r in rows if r.get(key) is not None}
    out, last, last_t = [], None, None
    for t in grid:
        if t in by:
            last, last_t = by[t], t
        if last is not None and (hold_hours is None or t - last_t <= hold_hours * HOUR):
            out.append(last)
        else:
            out.append(None)
    return out


def compute(weights=None, hours=720):
    weights = weights or DEFAULT_WEIGHTS
    now = int(time.time())
    errors = {}

    prem = premium.premium_series(hours)
    gate = derivs.history_gate("BTC", hours)
    okx_oi = derivs.history_okx_oi("BTC")
    okx_f = derivs.history_okx_funding("BTC")
    hl_f = derivs.history_hyperliquid_funding("BTC", 30)
    snaps, snap_err = derivs.collect_snapshots()
    errors.update(snap_err)

    start = _hour(max(prem[0]["t"], gate[0]["t"]))
    grid = list(range(start, _hour(now) + HOUR, HOUR))

    # --- 2. premium
    p_raw = _resample(prem, "premium_bps", grid, hold_hours=3)
    fast, slow = rolling_mean(p_raw, 6), rolling_mean(p_raw, 24)
    zf, zs = zscore_series(fast, 48), zscore_series(slow, 48)
    z_prem = [mean([a, b]) if (a is not None or b is not None) else None for a, b in zip(zf, zs)]

    # --- 3. funding (OI-weighted across OKX / Gate / Hyperliquid, hourly)
    oi_now = {v: (snaps.get(v, {}).get("BTC") or {}).get("oi_usd") for v in ("OKX", "Gate", "Hyperliquid")}
    wsum = sum(x for x in oi_now.values() if x) or 1.0
    wts = {v: (x or 0.0) / wsum for v, x in oi_now.items()}
    gate_f = _resample([{"t": r["t"], "f": r["funding"]} for r in gate], "f", grid, hold_hours=8)
    okx_fs = _resample(okx_f, "funding_8h", grid, hold_hours=9)
    hl_fs = _resample(hl_f, "funding_8h", grid, hold_hours=2)
    f_series = []
    for g, o, h in zip(gate_f, okx_fs, hl_fs):
        parts = [(wts["Gate"], g), (wts["OKX"], o), (wts["Hyperliquid"], h)]
        parts = [(w, x) for w, x in parts if x is not None and w > 0]
        tw = sum(w for w, _ in parts)
        f_series.append(sum(w * x for w, x in parts) / tw if tw else None)
    z_fund = zscore_series(f_series, 72)

    # --- 4. OI x price
    g_oi = _resample(gate, "oi_usd", grid, hold_hours=3)
    o_oi = _resample(okx_oi, "oi_usd", grid, hold_hours=3)
    mark = _resample(gate, "mark", grid, hold_hours=3)
    oi_tot = [(a or 0) + (b or 0) if (a or b) else None for a, b in zip(g_oi, o_oi)]
    oi_chg, px_chg = pct_change(oi_tot, 24), pct_change(mark, 24)
    signed = []
    for a, b in zip(oi_chg, px_chg):
        if a is None or b is None:
            signed.append(None)
        else:
            signed.append(a * (1 if b > 0.05 else -1 if b < -0.05 else 0))
    z_oi = zscore_series(signed, 72)

    # --- 1. ETF
    z_etf, etf_info = _etf_component(load_etf_daily(), grid)

    comps = {"etf": z_etf, "premium": z_prem, "funding": z_fund, "oi": z_oi}
    hist = []
    for i, t in enumerate(grid):
        num = den = 0.0
        n_av = 0
        for k, w in weights.items():
            z = comps[k][i]
            if z is not None:
                num += w * z
                den += w
                n_av += 1
        if n_av >= 3 and den:
            z = clip(num / den, -3, 3)
            hist.append({"t": t, "z": round(z, 3), "pct": round(norm_cdf(z) * 100, 1)})
    if not hist:
        raise RuntimeError("not enough overlapping history to score")

    cur = hist[-1]
    z_now = cur["z"]
    regime = ("Strong Buy Pressure" if z_now >= 1.0 else
              "Strong Sell Pressure" if z_now <= -1.0 else "Neutral")

    agg = derivs.aggregate_asset(snaps, "BTC") or {}
    last = lambda s: next((x for x in reversed(s) if x is not None), None)   # noqa: E731
    etf_flow = etf_info["flow"] if etf_info else None
    comp_out = []
    readout = {
        "etf": (f"{etf_info['flow']/1e6:+,.1f}M 1d | {etf_info['five_day']/1e6:+,.1f}M 5d (as of {etf_info['date']})"
                if etf_info else "building history"),
        "premium": f"{last(p_raw):+.2f} bps now | {last(rolling_mean(p_raw, 24)):+.2f} bps 24h avg",
        "funding": (f"{agg.get('funding_8h', 0)*100:+.4f}% per 8h across {len(agg.get('venues', []))} venues"
                    if agg else f"{(last(f_series) or 0)*100:+.4f}% per 8h"),
        "oi": f"{last(oi_chg):+.2f}% 24h OI vs {last(px_chg):+.2f}% 24h price",
    }
    for k, w in weights.items():
        z = last(comps[k])
        comp_out.append({"key": k, "label": LABELS[k], "weight": w, "z": None if z is None else round(z, 2),
                         "contribution": None if z is None else round(w * z, 3),
                         "readout": readout[k],
                         "history": [None if x is None else round(x, 2) for x in comps[k][-336::4]]})

    step = 4
    hist_out = hist[-720::step] if len(hist) > 180 else hist
    if hist_out[-1]["t"] != hist[-1]["t"]:
        hist_out.append(hist[-1])
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "ok",
        "score_z": z_now, "score_pct": cur["pct"], "regime": regime,
        "weights": weights, "components": comp_out,
        "history": hist_out,
        "venues_ok": sorted(snaps), "venue_errors": errors,
        "inputs": {"btc_funding_agg_8h": agg.get("funding_8h"), "btc_oi_usd_all_venues": agg.get("oi_usd"),
                   "coinbase_premium_bps": last(p_raw)},
    }


if __name__ == "__main__":
    out = compute()
    print(json.dumps({k: v for k, v in out.items() if k not in ("history",)}, indent=2, default=str)[:3000])
    print("history points:", len(out["history"]))
