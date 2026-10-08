"""Basic Stablecoin Velocity & Flows.

Where is dollar liquidity being created, parked and put to work? Data: DefiLlama's
free stablecoin API (supply, per-chain supply, supply one day / week / month ago,
prices) and its DEX-volume series. USD-pegged stablecoins only.

  Supply & net issuance  total circulating supply; change over 1d / 7d / 30d.
                         The dollar change in supply is a net mint-minus-burn
                         proxy (positive = net issuance).
  Major coins            top coins by supply with share, 1d/7d/30d change and
                         peg deviation (bps from $1.00).
  Chain deployment       supply per chain with 7d / 30d net change: where new
                         dollars are landing (Tron, Ethereum, Solana, Base ...).
  Velocity proxy         7-day average daily DEX volume divided by stablecoin
                         supply ("DEX turnover"). Rising turnover means the
                         same dollars are being used more actively on-chain.
  Flow signal            z-score of the latest 7-day supply change versus the
                         last 365 days of 7-day changes (Expanding strongly /
                         Expanding / Flat / Contracting).
  Velocity signal        z-score of turnover versus its trailing 365 days.

Not available for free and therefore NOT modelled: exchange stablecoin
balances / netflows (the reserve feeds are paid), CEX trading volume
attribution, and perpetual-DEX volume (DefiLlama's endpoint was empty on
2026-10-07). "Velocity" here is an on-chain DEX proxy, not payments velocity.
"""
from datetime import datetime, timezone

from .net import get_json
from .stats import mean, stdev, clip

SC = "https://stablecoins.llama.fi"
LLAMA = "https://api.llama.fi"


def _usd(d):
    return (d or {}).get("peggedUSD") or 0.0


def _chg(cur, prev):
    return None if not prev else (cur / prev - 1.0) * 100.0


def _z_label(z, pos, neg):
    if z is None:
        return "Building history"
    return pos[1] if z >= 1.5 else pos[0] if z >= 0.5 else neg[1] if z <= -1.5 else neg[0] if z <= -0.5 else "Flat"


def compute():
    assets = [a for a in get_json(f"{SC}/stablecoins", params={"includePrices": "true"}, timeout=60)["peggedAssets"]
              if a.get("pegType") == "peggedUSD"]
    cur = {a["symbol"] + ":" + a["id"]: a for a in assets}
    tot = sum(_usd(a["circulating"]) for a in assets)
    prev = {k: sum(_usd(a.get(k)) for a in assets) for k in ("circulatingPrevDay", "circulatingPrevWeek", "circulatingPrevMonth")}
    totals = {
        "supply_usd": tot,
        "change_1d_pct": _chg(tot, prev["circulatingPrevDay"]), "change_7d_pct": _chg(tot, prev["circulatingPrevWeek"]),
        "change_30d_pct": _chg(tot, prev["circulatingPrevMonth"]),
        "net_issuance_1d_usd": tot - prev["circulatingPrevDay"], "net_issuance_7d_usd": tot - prev["circulatingPrevWeek"],
        "net_issuance_30d_usd": tot - prev["circulatingPrevMonth"],
    }

    coins = []
    for a in sorted(assets, key=lambda a: -_usd(a["circulating"]))[:10]:
        c = _usd(a["circulating"])
        price = a.get("price")
        coins.append({
            "symbol": a["symbol"], "name": a["name"], "mechanism": a.get("pegMechanism"),
            "supply_usd": c, "share_pct": c / tot * 100.0,
            "change_1d_pct": _chg(c, _usd(a.get("circulatingPrevDay"))),
            "change_7d_pct": _chg(c, _usd(a.get("circulatingPrevWeek"))),
            "change_30d_pct": _chg(c, _usd(a.get("circulatingPrevMonth"))),
            # A price >3% from $1.00 is a yield-accruing / tokenised-fund coin (e.g. USYC), not a
            # depeg: report it as non-par instead of as a peg break.
            "peg_deviation_bps": None if price is None or abs(price - 1.0) > 0.03 else (price - 1.0) * 1e4,
            "non_par": price is not None and abs(price - 1.0) > 0.03,
        })

    chains = {}
    for a in assets:
        for ch, v in (a.get("chainCirculating") or {}).items():
            row = chains.setdefault(ch, {"now": 0.0, "wk": 0.0, "mo": 0.0})
            row["now"] += _usd(v.get("current"))
            row["wk"] += _usd(v.get("circulatingPrevWeek"))
            row["mo"] += _usd(v.get("circulatingPrevMonth"))
    chain_rows = [{"chain": ch, "supply_usd": r["now"], "share_pct": r["now"] / tot * 100.0,
                   "net_7d_usd": r["now"] - r["wk"], "net_30d_usd": r["now"] - r["mo"],
                   "change_7d_pct": _chg(r["now"], r["wk"])}
                  for ch, r in chains.items() if r["now"] > 0]
    chain_rows.sort(key=lambda r: -r["supply_usd"])
    top_chains = chain_rows[:10]
    movers = sorted(chain_rows[:30], key=lambda r: -abs(r["net_7d_usd"]))[:5]

    # history: total supply (daily) and DEX volume (daily)
    sup_hist = {}
    for p in get_json(f"{SC}/stablecoincharts/all", timeout=60):
        v = _usd(p.get("totalCirculatingUSD"))
        if v:
            sup_hist[int(p["date"])] = v
    dex = get_json(f"{LLAMA}/overview/dexs", params={"excludeTotalDataChartBreakdown": "true"}, timeout=90)
    dex_hist = {int(t): float(v) for t, v in dex["totalDataChart"]}

    days = sorted(set(sup_hist) & set(dex_hist))[:-1]          # drop today's partial DEX day
    sup = [sup_hist[d] for d in days]
    vol = [dex_hist[d] for d in days]
    turn = []
    for i in range(len(days)):
        w = vol[max(0, i - 6):i + 1]
        turn.append(100.0 * (sum(w) / len(w)) / sup[i] if sup[i] else None)
    wk_chg = [(_chg(sup[i], sup[i - 7]) if i >= 7 else None) for i in range(len(days))]

    def trailing_z(series, win=365, minw=60):
        i = len(series) - 1
        past = [x for x in series[max(0, i - win):i] if x is not None]
        if series[i] is None or len(past) < minw or not stdev(past):
            return None
        return clip((series[i] - mean(past)) / stdev(past), -4, 4)

    flow_z, vel_z = trailing_z(wk_chg), trailing_z(turn)
    tail = slice(-180, None)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok",
        "totals": totals, "coins": coins, "chains": top_chains, "chain_movers": movers,
        "flow": {"z": None if flow_z is None else round(flow_z, 2),
                 "label": _z_label(flow_z, ("Expanding", "Expanding strongly"), ("Contracting", "Contracting sharply")),
                 "change_7d_pct": wk_chg[-1]},
        "velocity": {"turnover_pct": turn[-1], "z": None if vel_z is None else round(vel_z, 2),
                     "label": _z_label(vel_z, ("Rising", "Surging"), ("Falling", "Sharply falling")),
                     "dex_volume_7d_avg_usd": sum(vol[-7:]) / 7.0},
        "peg": {"max_abs_deviation_bps": max((abs(c["peg_deviation_bps"]) for c in coins if c["peg_deviation_bps"] is not None), default=None),
                "coins_off_peg_50bps": sum(1 for c in coins if c["peg_deviation_bps"] is not None and abs(c["peg_deviation_bps"]) > 50)},
        "history": {"t": days[tail], "supply_usd": [round(x) for x in sup[tail]],
                    "turnover_pct": [None if x is None else round(x, 3) for x in turn[tail]],
                    "dex_volume_usd": [round(x) for x in vol[tail]]},
    }


if __name__ == "__main__":
    import json
    o = compute()
    print(json.dumps({k: v for k, v in o.items() if k not in ("history", "coins", "chains")}, indent=1, default=str)[:1800])
    for c in o["coins"][:6]:
        print(c["symbol"], round(c["supply_usd"] / 1e9, 1), "B", round(c["share_pct"], 1), "%", c["change_7d_pct"] and round(c["change_7d_pct"], 2), "peg bps", c["peg_deviation_bps"] and round(c["peg_deviation_bps"], 1))
    for c in o["chains"][:6]:
        print(c["chain"], round(c["supply_usd"] / 1e9, 1), "B 7d net", round(c["net_7d_usd"] / 1e6), "M")
    print("history pts", len(o["history"]["t"]))
