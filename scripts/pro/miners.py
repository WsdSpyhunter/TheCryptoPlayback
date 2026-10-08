"""Miner Stress.

Bitcoin miners are the network's forced sellers: they must sell much of what they mine to pay for
power and hardware, and when their margins collapse they switch machines off ("capitulation").
Historically those squeezes have clustered near cycle lows, and the recovery afterwards has been
a well-known signal. This module measures miner economics from free, open data and tests the
classic signals against the whole of Bitcoin's history.

Source: mempool.space's public API (open-source explorer): hashrate since 2009, difficulty
adjustments, block rewards and fees, mining-pool shares, and a price history since 2010. ETF flows
come from the site's own dataset.

Measures
  Hashprice        miner revenue per petahash per day (block subsidy + fees, USD), with percentile
                   versus its own last three years, plus the electricity price at which a miner of a
                   given efficiency (15 / 25 / 35 J/TH) breaks even.
  Hash Ribbons     30-day vs 60-day moving average of network hashrate. 30d below 60d = capitulation;
                   the cross back up = recovery. A "confirmed" buy signal (Capriole's rule) also
                   needs the 10-day price average above the 20-day.
  Puell Multiple   daily issuance value (subsidy x price) divided by its 365-day average. Low =
                   miners are earning far less than usual; high = a revenue windfall.
  Difficulty       progress and projected size of the next adjustment, and the recent run of
                   adjustments (a string of cuts means machines are leaving).
  Fee share        fees as a share of total block rewards (the post-subsidy economy).
  Pool control     share of recent blocks by pool, top-3 share and an HHI concentration index.
  Supply absorption  ETF net inflows (USD) divided by the value of newly mined coin over the same
                   window: how many times over fresh demand covers fresh supply.

Miner Stress score (0-100, higher = more stress), percentile-based so it needs no hand-set limits:
  Hashprice (low = stress)   35%   percentile vs the last three years, inverted
  Hash-ribbon spread         30%   (30d / 60d average - 1), percentile vs three years, inverted
  Puell multiple (low)       20%   percentile vs all history since 2013, inverted
  Difficulty trend           15%   mean of the last three adjustments, percentile vs history, inverted
Bands: Comfortable < 30, Normal 30-50, Under pressure 50-70, Capitulation risk >= 70.

Event studies (shown with their sample sizes): what BTC did over the following 30 / 90 / 180 days
after every hash-ribbon recovery since 2012, and after each Puell-multiple band. These are
descriptive history, not forecasts: samples are small, windows overlap, and halvings and ETFs have
changed miner economics. Hashrate and price are third-party estimates; fees before 2023 are not
included in hashprice history (subsidy-only before then).
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone

from .net import get_json
from .stats import percentile_rank, mean

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
M = "https://mempool.space/api"
DAY = 86400
HALVINGS = [("2012-11-28", 25.0), ("2016-07-09", 12.5), ("2020-05-11", 6.25), ("2024-04-20", 3.125), ("2028-04-17", 1.5625)]
BLOCKS_PER_DAY = 144
EFFICIENCIES = [("Modern fleet", 15.0), ("Average fleet", 25.0), ("Older machines", 35.0)]
REFERENCE_POWER = 0.07            # USD per kWh, a typical industrial rate used for the margin readout
WEIGHTS = {"hashprice": 0.35, "ribbon": 0.30, "puell": 0.20, "difficulty": 0.15}


def _day(ts):
    return int(ts) // DAY * DAY


def _dstr(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def _subsidy(ts):
    s = 50.0
    for d, v in HALVINGS:
        if ts >= int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()):
            s = v
    return s


def load_series():
    hr_raw = get_json(f"{M}/v1/mining/hashrate/all", timeout=90)
    pr_raw = get_json(f"{M}/v1/historical-price?currency=USD", timeout=90)["prices"]
    px = {}
    for r in sorted(pr_raw, key=lambda r: r["time"]):               # last price of each UTC day
        if r.get("USD"):
            px[_day(r["time"])] = float(r["USD"])
    hr = {}
    for r in hr_raw["hashrates"]:
        if r["avgHashrate"] and r["avgHashrate"] > 0:
            hr[_day(r["timestamp"])] = float(r["avgHashrate"])
    start = _day(int(datetime(2012, 1, 1, tzinfo=timezone.utc).timestamp()))
    end = min(max(hr), max(px))
    days, last_h, last_p = [], None, None
    H, P = [], []
    t = start
    while t <= end:
        last_h = hr.get(t, last_h)
        last_p = px.get(t, last_p)
        if last_h and last_p:
            days.append(t)
            H.append(last_h)
            P.append(last_p)
        t += DAY
    return days, H, P, hr_raw


def _ma(vals, n):
    out, run = [], 0.0
    for i, v in enumerate(vals):
        run += v
        if i >= n:
            run -= vals[i - n]
        out.append(run / n if i >= n - 1 else None)
    return out


def _fwd(P, i, n):
    return (P[i + n] / P[i] - 1.0) * 100.0 if i + n < len(P) else None


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def ribbon_events(days, H, P):
    ma30, ma60 = _ma(H, 30), _ma(H, 60)
    pma10, pma20 = _ma(P, 10), _ma(P, 20)
    episodes, in_cap, start_i = [], False, None
    for i in range(61, len(days)):
        cap = ma30[i] < ma60[i]
        if cap and not in_cap:
            in_cap, start_i = True, i
        elif not cap and in_cap:
            in_cap = False
            rec_i = i
            conf_i = next((j for j in range(rec_i, min(rec_i + 60, len(days))) if pma10[j] > pma20[j]), None)
            sig_i = conf_i if conf_i is not None else rec_i
            episodes.append({
                "capitulation_start": _dstr(days[start_i]), "recovery": _dstr(days[rec_i]), "confirmed": _dstr(days[conf_i]) if conf_i is not None else None,
                "days_in_capitulation": rec_i - start_i, "price_at_signal": P[sig_i],
                "fwd_30d": _fwd(P, sig_i, 30), "fwd_90d": _fwd(P, sig_i, 90), "fwd_180d": _fwd(P, sig_i, 180),
                "hashrate_drop_pct": (min(H[start_i:rec_i + 1]) / H[start_i] - 1.0) * 100.0,
            })
    done = [e for e in episodes if e["fwd_90d"] is not None]
    allr = [_fwd(P, i, 90) for i in range(61, len(P))]
    recent = [e for e in done if (e["confirmed"] or e["recovery"]) >= "2025-01-01"]
    summary = {
        "recent_since_2025": {"n": len(recent), "median_90d": _median([e["fwd_90d"] for e in recent]),
                              "hit_rate_90d_pct": (100.0 * sum(1 for e in recent if e["fwd_90d"] > 0) / len(recent)) if recent else None},
        "episodes": len(episodes), "with_90d": len(done),
        "median_90d": _median([e["fwd_90d"] for e in done]),
        "hit_rate_90d_pct": (100.0 * sum(1 for e in done if e["fwd_90d"] > 0) / len(done)) if done else None,
        "median_30d": _median([e["fwd_30d"] for e in done]), "median_180d": _median([e["fwd_180d"] for e in episodes]),
        "baseline_median_90d_all_days": _median(allr),
        "baseline_hit_rate_90d_pct": 100.0 * sum(1 for x in allr if x is not None and x > 0) / max(1, sum(1 for x in allr if x is not None)),
    }
    state = "Capitulation" if in_cap else "Healthy"
    cur = {"state": state, "ma30_eh": ma30[-1] / 1e18, "ma60_eh": ma60[-1] / 1e18, "spread_pct": (ma30[-1] / ma60[-1] - 1.0) * 100.0,
           "price_ma10_above_ma20": pma10[-1] > pma20[-1]}
    if not in_cap and episodes:
        last = episodes[-1]
        rec_days = (days[-1] - int(datetime.strptime(last["recovery"], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())) // DAY
        if rec_days <= 90:
            cur["state"] = "Recovery"
        cur["days_since_recovery"] = rec_days
        cur["last_recovery"] = last["recovery"]
    if in_cap:
        cur["days_in_capitulation"] = len(days) - 1 - start_i
        cur["capitulation_start"] = _dstr(days[start_i])
    return episodes, summary, cur, ma30, ma60


def puell_study(days, P):
    iss = [_subsidy(t) * BLOCKS_PER_DAY * p for t, p in zip(days, P)]
    ma365 = _ma(iss, 365)
    puell = [None if m is None else v / m for v, m in zip(iss, ma365)]
    buckets = [("Below 0.6", 0, 0.6), ("0.6 to 0.9", 0.6, 0.9), ("0.9 to 1.3", 0.9, 1.3), ("1.3 to 2", 1.3, 2.0), ("Above 2", 2.0, 1e9)]
    out = []
    for name, lo, hi in buckets:
        idx = [i for i, v in enumerate(puell) if v is not None and lo <= v < hi]
        f90 = [_fwd(P, i, 90) for i in idx]
        f90 = [x for x in f90 if x is not None]
        out.append({"band": name, "days": len(idx), "median_90d": _median(f90), "positive_pct": (100.0 * sum(1 for x in f90 if x > 0) / len(f90)) if f90 else None})
    return puell, iss, out


def pools_snapshot():
    d = get_json(f"{M}/v1/mining/pools/1w", timeout=40)
    total = d.get("blockCount") or sum(p["blockCount"] for p in d["pools"])
    pools = [{"name": p["name"], "blocks": p["blockCount"], "share_pct": p["blockCount"] / total * 100.0, "empty_blocks": p.get("emptyBlocks", 0)} for p in d["pools"]]
    pools.sort(key=lambda p: -p["blocks"])
    return {"total_blocks": total, "top1_pct": pools[0]["share_pct"], "top3_pct": sum(p["share_pct"] for p in pools[:3]),
            "hhi": round(sum(p["share_pct"] ** 2 for p in pools)), "pools": pools[:8],
            "empty_block_pct": 100.0 * sum(p["empty_blocks"] for p in pools) / total}


def etf_absorption(days, P):
    try:
        obs = json.load(open(os.path.join(ROOT, "data", "etf_flows.json")))["observations"]
    except (OSError, ValueError):
        return None
    flows = {d: float(o["total_net_flow_usd"]) for d, o in obs.items()}
    if not flows:
        return None
    last = max(flows)
    last_dt = datetime.strptime(last, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    price = P[-1]

    def win(n):
        keys = [d for d in flows if (last_dt - datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)).days < n]
        etf = sum(flows[d] for d in keys)
        issuance = sum(_subsidy(days[-1]) * BLOCKS_PER_DAY * price for _ in range(n))
        return etf, issuance, len(keys)
    e7, i7, n7 = win(7)
    e30, i30, n30 = win(30)
    return {"as_of": last, "etf_7d_usd": e7, "issuance_7d_usd": i7, "ratio_7d": e7 / i7 if i7 else None,
            "etf_window_30d_usd": e30, "issuance_30d_usd": i30, "ratio_30d": e30 / i30 if i30 and n30 >= 12 else None, "obs_in_30d": n30}


def compute():
    days, H, P, _ = load_series()
    n = len(days)
    # ---- ribbons, Puell, episodes
    episodes, rsum, rib, ma30, ma60 = ribbon_events(days, H, P)
    puell, iss_usd, buckets = puell_study(days, P)

    # ---- revenue incl. fees (last ~3 years) for hashprice
    rew = get_json(f"{M}/v1/mining/blocks/rewards/3y", timeout=60)
    fee = get_json(f"{M}/v1/mining/blocks/fees/3y", timeout=60)
    rev_btc = {_day(r["timestamp"]): r["avgRewards"] / 1e8 for r in rew}
    fee_btc = {_day(r["timestamp"]): r["avgFees"] / 1e8 for r in fee}
    hp_series = []                                     # (day, USD per PH per day, fee share)
    for i, t in enumerate(days):
        if t in rev_btc:
            rev_usd = rev_btc[t] * BLOCKS_PER_DAY * P[i]
            hp_series.append((t, rev_usd / (H[i] / 1e15), fee_btc.get(t, 0.0) / rev_btc[t] if rev_btc[t] else 0.0))
    if len(hp_series) < 200:
        raise RuntimeError("fee-inclusive revenue history unexpectedly short")
    hp_vals = [x[1] for x in hp_series]
    hp_now = mean(hp_vals[-3:])
    hp_pct = percentile_rank(hp_now, hp_vals[-1095:])
    hp_30 = mean(hp_vals[-33:-30]) if len(hp_vals) > 40 else None
    fee_share_30 = mean([x[2] for x in hp_series[-30:]]) * 100.0
    fee_share_90 = mean([x[2] for x in hp_series[-90:]]) * 100.0
    breakeven = []
    for label, jth in EFFICIENCIES:
        usd_th_day = hp_now / 1000.0
        kwh_per_th_day = jth * 24.0 / 1000.0
        breakeven.append({"label": label, "joules_per_th": jth, "breakeven_usd_per_kwh": usd_th_day / kwh_per_th_day,
                          "margin_pct_at_reference": (1.0 - (kwh_per_th_day * REFERENCE_POWER) / usd_th_day) * 100.0})

    # ---- difficulty
    now_adj = get_json(f"{M}/v1/difficulty-adjustment", timeout=30)
    hist_adj = get_json(f"{M}/v1/mining/difficulty-adjustments", timeout=40)
    adj = [(r[0], (r[3] - 1.0) * 100.0) for r in hist_adj]                       # newest first
    last_adjs = [a for _, a in adj[:12]][::-1]
    neg_streak = 0
    for _, a in adj:
        if a < 0:
            neg_streak += 1
        else:
            break
    adj_all = [a for _, a in adj]
    diff_trend = mean([a for _, a in adj[:3]])
    diff_pct = percentile_rank(diff_trend, adj_all)

    # ---- stress score
    ribbon_spread_hist = [(a / b - 1.0) for a, b in zip(ma30, ma60) if a and b][-1095:]
    comps = {
        "hashprice": 100.0 - hp_pct,
        "ribbon": 100.0 - percentile_rank(ma30[-1] / ma60[-1] - 1.0, ribbon_spread_hist),
        "puell": 100.0 - percentile_rank(puell[-1], [v for v in puell if v is not None]),
        "difficulty": 100.0 - diff_pct,
    }
    score = sum(WEIGHTS[k] * v for k, v in comps.items())
    label = "Capitulation risk" if score >= 70 else "Under pressure" if score >= 50 else "Normal" if score >= 30 else "Comfortable"
    comp_out = [
        {"key": "hashprice", "label": "Hashprice", "weight": WEIGHTS["hashprice"], "stress": round(comps["hashprice"]),
         "readout": f"${hp_now:,.0f} per PH/s per day, {hp_pct:.0f}th percentile of 3 years"},
        {"key": "ribbon", "label": "Hash-ribbon spread", "weight": WEIGHTS["ribbon"], "stress": round(comps["ribbon"]),
         "readout": f"30d average {rib['spread_pct']:+.1f}% vs 60d ({rib['state'].lower()})"},
        {"key": "puell", "label": "Puell multiple", "weight": WEIGHTS["puell"], "stress": round(comps["puell"]),
         "readout": f"{puell[-1]:.2f} (miner issuance value vs its 365-day average)"},
        {"key": "difficulty", "label": "Difficulty trend", "weight": WEIGHTS["difficulty"], "stress": round(comps["difficulty"]),
         "readout": f"last three adjustments average {diff_trend:+.1f}%" + (f"; {neg_streak} cut{'s' if neg_streak != 1 else ''} in a row" if neg_streak else "")},
    ]

    # ---- chart history (last 2 years daily)
    k = 730
    hist = {"t": days[-k:], "hashrate_eh": [round(h / 1e18, 1) for h in H[-k:]],
            "ma30_eh": [None if v is None else round(v / 1e18, 1) for v in ma30[-k:]], "ma60_eh": [None if v is None else round(v / 1e18, 1) for v in ma60[-k:]],
            "price": [round(p) for p in P[-k:]]}
    hpd = {"t": [x[0] for x in hp_series][-1095:], "hashprice": [round(x[1], 1) for x in hp_series][-1095:]}
    absorb = etf_absorption(days, P)
    avg = next(b for b in breakeven if b["joules_per_th"] == 25.0)
    parts = []
    if hp_pct < 25:
        parts.append(f"Margins are squeezed: hashprice sits in the bottom {max(1, round(hp_pct))}% of the last three years and an average-efficiency fleet "
                     f"({'loses money' if avg['margin_pct_at_reference'] < 0 else 'earns thinly'} at ${REFERENCE_POWER:.2f}/kWh)")
    elif hp_pct > 75:
        parts.append(f"Margins are healthy: hashprice is in the top {max(1, round(100 - hp_pct))}% of the last three years")
    else:
        parts.append("Miner margins are in a normal range")
    if rib["state"] == "Capitulation":
        parts.append("hashrate is falling (30-day average below the 60-day), the pattern of miners switching machines off")
    elif now_adj["difficultyChange"] > 2:
        parts.append(f"yet hashrate is still growing and the next difficulty adjustment is projected {now_adj['difficultyChange']:+.1f}%, so miners are adding machines rather than capitulating")
    elif now_adj["difficultyChange"] < -2:
        parts.append(f"and the next difficulty adjustment is projected {now_adj['difficultyChange']:+.1f}%, a sign that machines are leaving")
    else:
        parts.append("and hashrate is roughly flat")
    read = "; ".join(parts) + "."
    if absorb and absorb.get("ratio_30d"):
        read += f" Over the last 30 days, spot ETF inflows have covered newly mined supply about {absorb['ratio_30d']:.1f}x."
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok", "read": read,
        "stress": {"score": round(score, 1), "label": label, "weights": WEIGHTS, "components": comp_out},
        "ribbon": rib,
        "hashprice": {"usd_per_ph_day": hp_now, "usd_per_th_day": hp_now / 1000.0, "percentile_3y": hp_pct,
                      "change_30d_pct": None if not hp_30 else (hp_now / hp_30 - 1.0) * 100.0, "breakeven": breakeven,
                      "reference_power_usd_per_kwh": REFERENCE_POWER},
        "puell": {"value": puell[-1], "percentile_all": percentile_rank(puell[-1], [v for v in puell if v is not None]), "buckets": buckets},
        "difficulty": {"progress_pct": now_adj["progressPercent"], "estimated_change_pct": now_adj["difficultyChange"],
                       "estimated_retarget": int(now_adj["estimatedRetargetDate"] / 1000), "remaining_blocks": now_adj["remainingBlocks"],
                       "avg_block_time_s": (now_adj.get("timeAvg") or 0) / 1000.0, "previous_pct": now_adj.get("previousRetarget"),
                       "last_adjustments_pct": last_adjs, "negative_streak": neg_streak},
        "fees": {"share_30d_pct": fee_share_30, "share_90d_pct": fee_share_90},
        "pools": pools_snapshot(),
        "absorption": absorb,
        "price_usd": P[-1], "hashrate_eh": H[-1] / 1e18, "subsidy_btc": _subsidy(days[-1]),
        "events": {"ribbon": {"summary": rsum, "episodes": episodes[-10:][::-1]}},
        "history": hist, "hashprice_history": hpd,
        "data_through": _dstr(days[-1]),
    }


if __name__ == "__main__":
    t0 = time.time()
    o = compute()
    print(f"{time.time() - t0:.0f}s")
    print(json.dumps({k: v for k, v in o.items() if k not in ("history", "hashprice_history", "events")}, indent=1, default=str)[:3800])
    print(json.dumps(o["events"]["ribbon"]["summary"], indent=1))
    for e in o["events"]["ribbon"]["episodes"][:6]:
        print(e["capitulation_start"], "->", e["recovery"], "conf", e["confirmed"], f"{e['days_in_capitulation']}d", "fwd90", e["fwd_90d"] and round(e["fwd_90d"]), "fwd180", e["fwd_180d"] and round(e["fwd_180d"]))
    print(o["puell"]["buckets"])
