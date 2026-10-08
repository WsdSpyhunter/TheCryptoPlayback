"""Institutional Positioning Index, Open Edition.

Where are the big, regulated players positioned in Bitcoin, and is money flowing
in or out? Four components, each turned into a trailing z-score (compared only
with its own past, no look-ahead), blended with configurable weights:

  1. CME futures positioning (30%)  The CFTC "Traders in Financial Futures" report for CME Bitcoin
                                    futures: asset managers' net position (long minus short) as a
                                    share of open interest. Weekly, 2018 onward; z-scored against the
                                    trailing 104 weeks. A report counts from the Saturday after the
                                    Tuesday it describes (it is published Friday).
  2. Spot ETF flows (30%)           US spot Bitcoin ETF daily net flow: half 1-day flow, half rolling
                                    5-day sum (the site's own ETF dataset).
  3. On-chain perp funding (20%)    Hyperliquid BTC perpetual funding (per 8h): positive means longs
                                    are paying shorts. Hourly history, z-scored over the past 30 days.
  4. Perp OI x price (20%)          24-hour change in Hyperliquid BTC open interest signed by the
                                    24-hour price direction. Hyperliquid publishes no open-interest
                                    history, so this builds from our own snapshots (data/pro/
                                    hl_btc_snapshots.json) and shows "building" for the first days.

Score: the weighted z (about -2..+2) and its 0-100 percentile. Regime: z >= +1 Bullish positioning,
z <= -1 Bearish positioning, otherwise Neutral. A descriptive gauge, not a forecast.

Also reported (not scored): leveraged funds' and dealers' CME positions. Leveraged funds are
usually net SHORT because many run the ETF-vs-futures "basis trade", so their short is not read as
a bearish view.

Sources, all free: CFTC public reporting API (US government data), the site's ETF dataset, the
Hyperliquid public info endpoint. Coinbase Premium and exchange-order-flow inputs from the earlier
version are intentionally gone (no clean free source).
"""
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone

from . import derivs
from .net import get_json
from .pressure import load_etf_daily, _etf_component, _resample, HOUR
from .stats import zscore_series, pct_change, norm_cdf, clip, mean

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAP_FILE = os.path.join(ROOT, "data", "pro", "hl_btc_snapshots.json")
CFTC = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
WEIGHTS = {"cot": 0.30, "etf": 0.30, "funding": 0.20, "oi": 0.20}
LABELS = {"cot": "CME futures positioning", "etf": "Spot ETF flows", "funding": "On-chain perp funding",
          "oi": "Perp open interest x price"}


def fetch_cot():
    q = {"$where": "cftc_contract_market_code='133741'", "$order": "report_date_as_yyyy_mm_dd ASC", "$limit": "3000"}
    rows = get_json(CFTC + "?" + urllib.parse.urlencode(q), timeout=60)
    out = []
    for r in rows:
        try:
            d = datetime.strptime(r["report_date_as_yyyy_mm_dd"][:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            oi = int(r["open_interest_all"])
            out.append({
                "date": d.strftime("%Y-%m-%d"), "t": int(d.timestamp()), "oi": oi,
                "am_l": int(r["asset_mgr_positions_long"]), "am_s": int(r["asset_mgr_positions_short"]),
                "lf_l": int(r["lev_money_positions_long"]), "lf_s": int(r["lev_money_positions_short"]),
                "dl_l": int(r["dealer_positions_long_all"]), "dl_s": int(r["dealer_positions_short_all"]),
                "lf_traders_s": int(r.get("traders_lev_money_short_all") or 0), "lf_traders_l": int(r.get("traders_lev_money_long_all") or 0),
            })
        except (KeyError, ValueError, TypeError):
            continue
    if len(out) < 60:
        raise RuntimeError("CFTC history unexpectedly short")
    return out


def load_snaps():
    try:
        return json.load(open(SNAP_FILE))
    except (OSError, ValueError):
        return []


def record_snapshot():
    snap = derivs.snapshot_hyperliquid().get("BTC")
    snaps = load_snaps()
    if snap and snap.get("oi_usd") and snap.get("mark"):
        snaps.append([int(time.time()), snap["oi_usd"], snap["mark"]])
    cutoff = time.time() - 40 * 86400
    snaps = [s for s in snaps if s[0] >= cutoff]
    os.makedirs(os.path.dirname(SNAP_FILE), exist_ok=True)
    json.dump(snaps, open(SNAP_FILE, "w"), separators=(",", ":"))
    return snaps, snap


def _net_pct(r):
    return (r["am_l"] - r["am_s"]) / r["oi"] * 100.0 if r["oi"] else None


def compute(weights=None):
    weights = weights or WEIGHTS
    now = int(time.time())
    cot = fetch_cot()
    snaps, hl_now = record_snapshot()
    hl_f = derivs.history_hyperliquid_funding("BTC", 30)

    # grid: last 30 days, hourly
    grid = list(range(now // HOUR * HOUR - 719 * HOUR, now // HOUR * HOUR + HOUR, HOUR))

    # --- 1. CME positioning (weekly z, mapped to hours with the publication lag)
    series = [_net_pct(r) for r in cot]
    zc = zscore_series(series, min_window=26, max_window=104)
    avail = [(r["t"] + 4 * 86400, z) for r, z in zip(cot, zc)]
    z_cot, j, cur = [], 0, None
    for t in grid:
        while j < len(avail) and avail[j][0] <= t:
            cur = avail[j][1]
            j += 1
        z_cot.append(cur)

    # --- 2. ETF
    z_etf, etf_info = _etf_component(load_etf_daily(), grid)

    # --- 3. funding
    f_series = _resample(hl_f, "funding_8h", grid, hold_hours=2)
    z_fund = zscore_series(f_series, 72)

    # --- 4. OI x price from snapshots
    rows = [{"t": s[0], "oi": s[1], "px": s[2]} for s in snaps]
    oi_g = _resample(rows, "oi", grid, hold_hours=3)
    px_g = _resample(rows, "px", grid, hold_hours=3)
    oi_chg, px_chg = pct_change(oi_g, 24), pct_change(px_g, 24)
    signed = [None if a is None or b is None else a * (1 if b > 0.05 else -1 if b < -0.05 else 0) for a, b in zip(oi_chg, px_chg)]
    z_oi = zscore_series(signed, 72)

    comps = {"cot": z_cot, "etf": z_etf, "funding": z_fund, "oi": z_oi}
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
        if n_av >= 2 and den:
            z = clip(num / den, -3, 3)
            hist.append({"t": t, "z": round(z, 3), "pct": round(norm_cdf(z) * 100, 1)})
    if not hist:
        raise RuntimeError("not enough data to score")
    cur_pt = hist[-1]
    z_now = cur_pt["z"]
    regime = "Bullish Positioning" if z_now >= 1.0 else "Bearish Positioning" if z_now <= -1.0 else "Neutral"

    last = lambda s: next((x for x in reversed(s) if x is not None), None)    # noqa: E731
    lc = cot[-1]
    am_net = lc["am_l"] - lc["am_s"]
    readout = {
        "cot": f"Asset managers net {am_net:+,} contracts ({_net_pct(lc):+.1f}% of open interest), report of {lc['date']}",
        "etf": (f"{etf_info['flow']/1e6:+,.1f}M 1d | {etf_info['five_day']/1e6:+,.1f}M 5d (as of {etf_info['date']})" if etf_info else "building history"),
        "funding": f"{(last(f_series) or 0) * 100:+.4f}% per 8h on Hyperliquid",
        "oi": (f"{last(oi_chg):+.2f}% 24h OI vs {last(px_chg):+.2f}% 24h price" if last(oi_chg) is not None and last(px_chg) is not None
               else f"building history ({len(snaps)} snapshots so far)"),
    }
    comp_out = []
    for k, w in weights.items():
        z = last(comps[k])
        comp_out.append({"key": k, "label": LABELS[k], "weight": w, "z": None if z is None else round(z, 2),
                         "contribution": None if z is None else round(w * z, 3), "readout": readout[k],
                         "history": [None if x is None else round(x, 2) for x in comps[k][-336::4]]})

    step = 4
    hist_out = hist[::step]
    if hist_out[-1]["t"] != hist[-1]["t"]:
        hist_out.append(hist[-1])

    # CME block for display (last 104 weeks)
    tail = cot[-104:]
    prev = cot[-2] if len(cot) > 1 else None

    def grp(name, l, s, key):
        net = lc[l] - lc[s]
        pnet = (prev[l] - prev[s]) if prev else None
        return {"name": name, "long": lc[l], "short": lc[s], "net": net,
                "net_pct_oi": net / lc["oi"] * 100.0 if lc["oi"] else None,
                "change_net_w": None if pnet is None else net - pnet}
    cme = {
        "report_date": lc["date"], "open_interest_contracts": lc["oi"], "contract_size_btc": 5,
        "groups": [grp("Asset managers", "am_l", "am_s", "am"), grp("Leveraged funds", "lf_l", "lf_s", "lf"),
                   grp("Dealers", "dl_l", "dl_s", "dl")],
        "history": {"d": [r["date"] for r in tail], "t": [r["t"] for r in tail],
                    "asset_managers_net": [r["am_l"] - r["am_s"] for r in tail],
                    "leveraged_funds_net": [r["lf_l"] - r["lf_s"] for r in tail],
                    "dealers_net": [r["dl_l"] - r["dl_s"] for r in tail]},
    }
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok",
        "score_z": z_now, "score_pct": cur_pt["pct"], "regime": regime,
        "weights": weights, "components": comp_out, "history": hist_out, "cme": cme,
        "inputs": {"hyperliquid_btc_oi_usd": (hl_now or {}).get("oi_usd"), "snapshots": len(snaps)},
    }


if __name__ == "__main__":
    out = compute()
    print(json.dumps({k: v for k, v in out.items() if k not in ("history", "cme")}, indent=1, default=str)[:2600])
    print(json.dumps(out["cme"]["groups"], indent=1))
    print("history points:", len(out["history"]))
