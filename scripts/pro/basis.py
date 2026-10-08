"""Basis-Trade Crowding.

When spot Bitcoin ETFs launched, many hedge funds began the "basis trade": buy the ETF, short CME
Bitcoin futures against it, and collect the gap between futures and spot. It is popular because
it looks like free money, and that is exactly why it can become crowded: if the gap closes, ETF
flows turn, or margin tightens, every fund heads for the same exit and the unwind forces
simultaneous ETF selling and futures buying.

This indicator estimates how big and how crowded that trade is, from free public data:

  Source: the CFTC's weekly "Traders in Financial Futures" report for CME Bitcoin futures (US
  government data, 2018 onward): leveraged funds' (hedge funds') long and short positions, open
  interest, and the NUMBER of leveraged-fund traders on each side. Published Fridays for the
  prior Tuesday. ETF capital comes from the site's own ETF dataset (cumulative net inflows).

Components (each a percentile of the same quantity over the trailing 156 weeks, 0-100):
  Size          40%  leveraged funds' NET SHORT as a share of open interest
  Absolute size 30%  leveraged funds' net short in contracts (one contract = 5 BTC)
  Breadth       30%  how many leveraged-fund traders are short (more funds in the trade = more
                     crowded, harder to exit)
Crowding score = weighted percentile, 0-100. Bands: Low < 35, Moderate 35-55, High 55-75, Extreme 75+.

Also reported: net short in BTC and dollars (at the latest Hyperliquid BTC price), the share of the
capital that has flowed into the spot ETFs that the net short equals (a hedge-ratio proxy), the
4-week change (building / unwinding / stable), and the matching asset-manager long (the other side).

Important limits: the CFTC does not label basis trades. A leveraged-fund short is a PROXY (those
funds can also short for directional reasons), ETFs can be hedged elsewhere, and the data is weekly.
This is a gauge of crowding in the regulated futures leg, not a measurement of the whole trade.
"""
import json
import os
import time
from datetime import datetime, timezone

from . import derivs
from .positioning import fetch_cot
from .stats import percentile_rank

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEIGHTS = {"size": 0.40, "absolute": 0.30, "breadth": 0.30}
LABELS = {"size": "Net short, share of open interest", "absolute": "Net short, contracts", "breadth": "Funds in the trade"}
WINDOW = 156
CONTRACT_BTC = 5


def _label(score):
    return "Extreme" if score >= 75 else "High" if score >= 55 else "Moderate" if score >= 35 else "Low"


def _etf_cumulative():
    try:
        obs = json.load(open(os.path.join(ROOT, "data", "etf_flows.json")))["observations"]
        d = sorted(obs)[-1]
        return float(obs[d]["cum_net_inflow_usd"]), d
    except (OSError, ValueError, KeyError, IndexError):
        return None, None


def compute():
    cot = fetch_cot()
    net_short = [r["lf_s"] - r["lf_l"] for r in cot]                     # contracts
    pct_oi = [ns / r["oi"] * 100.0 if r["oi"] else None for ns, r in zip(net_short, cot)]
    breadth = [r["lf_traders_s"] for r in cot]

    def score_at(i):
        lo = max(0, i - WINDOW + 1)
        c = {"size": percentile_rank(pct_oi[i], [x for x in pct_oi[lo:i + 1] if x is not None]),
             "absolute": percentile_rank(net_short[i], net_short[lo:i + 1]),
             "breadth": percentile_rank(breadth[i], breadth[lo:i + 1])}
        num = sum(WEIGHTS[k] * v for k, v in c.items() if v is not None)
        den = sum(WEIGHTS[k] for k, v in c.items() if v is not None)
        return c, (num / den if den else None)

    hist_scores = []
    for i in range(52, len(cot)):
        _, s = score_at(i)
        hist_scores.append((cot[i]["date"], cot[i]["t"], s))
    comps, score = score_at(len(cot) - 1)
    last, prev4 = cot[-1], cot[-5] if len(cot) >= 5 else cot[0]
    chg4 = net_short[-1] - (prev4["lf_s"] - prev4["lf_l"])
    base = max(abs(prev4["lf_s"] - prev4["lf_l"]), 1)
    phase = "Building" if chg4 / base > 0.05 else "Unwinding" if chg4 / base < -0.05 else "Stable"

    price = (derivs.snapshot_hyperliquid().get("BTC") or {}).get("mark")
    ns_btc = net_short[-1] * CONTRACT_BTC
    ns_usd = ns_btc * price if price else None
    etf_cum, etf_date = _etf_cumulative()
    hedge_ratio = (ns_usd / etf_cum * 100.0) if (ns_usd and etf_cum) else None

    am_long_btc = last["am_l"] * CONTRACT_BTC
    readout = {
        "size": f"{pct_oi[-1]:.1f}% of open interest ({last['oi']:,} contracts)",
        "absolute": f"{net_short[-1]:,} contracts = {ns_btc:,.0f} BTC" + (f" (about ${ns_usd/1e9:.1f}B)" if ns_usd else ""),
        "breadth": f"{last['lf_traders_s']} leveraged-fund traders hold shorts ({last['lf_traders_l']} hold longs)",
    }
    comp_out = [{"key": k, "label": LABELS[k], "weight": WEIGHTS[k], "percentile": None if comps[k] is None else round(comps[k]),
                 "readout": readout[k]} for k in WEIGHTS]
    tail = hist_scores[-156:]
    ctail = cot[-156:]
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok",
        "score": round(score, 1), "label": _label(score), "phase": phase,
        "report_date": last["date"], "weights": WEIGHTS, "components": comp_out,
        "current": {
            "lf_long": last["lf_l"], "lf_short": last["lf_s"], "lf_net_short": net_short[-1], "lf_net_short_pct_oi": pct_oi[-1],
            "lf_net_short_btc": ns_btc, "lf_net_short_usd": ns_usd, "btc_price_used": price, "open_interest": last["oi"],
            "change_4w_contracts": chg4, "etf_cumulative_inflow_usd": etf_cum, "etf_data_date": etf_date,
            "hedge_ratio_pct": hedge_ratio, "asset_manager_long_btc": am_long_btc,
        },
        "history": {"d": [r["date"] for r in ctail], "t": [r["t"] for r in ctail],
                    "lf_net_short_pct_oi": [None if (r["oi"] == 0) else round((r["lf_s"] - r["lf_l"]) / r["oi"] * 100.0, 2) for r in ctail],
                    "score": [None if s is None else round(s, 1) for _, _, s in [(None, None, None)] * (len(ctail) - len(tail)) + tail]},
    }


if __name__ == "__main__":
    o = compute()
    print(json.dumps({k: v for k, v in o.items() if k != "history"}, indent=1, default=str)[:2800])
    print(len(o["history"]["d"]), o["history"]["score"][-5:])
