"""Net Liquidity & Macro Sensitivity.

How much dollar liquidity is the US system supplying, which way is the macro tide running for
Bitcoin, and how tightly has Bitcoin actually followed it? All inputs are US-government or open
data: the Federal Reserve's and Treasury's series from FRED (no key), and Bitcoin's price from
mempool.space.

  Net liquidity   Fed balance sheet (WALCL) minus the Treasury General Account (WTREGEN) minus the
                  overnight reverse-repo facility (RRPONTSYD): the dollars actually available to
                  markets, weekly (Wednesday). Reported as a level, 4- and 13-week changes, and what
                  moved it.
  Macro backdrop  0-100 (higher = more supportive for risk assets), an average of three percentiles
                  over the last ten years:
                     Liquidity impulse  40%  13-week change in net liquidity (% of level)
                     Real-yield pressure 30%  63-trading-day change in the 10-year TIPS yield, inverted
                     Dollar pressure     30%  63-trading-day change in the Fed's broad dollar index, inverted
                  Bands: Headwind <= 38, Mixed, Tailwind >= 62.
  Sensitivity     how Bitcoin has really behaved: correlation and beta of its returns to dollar and
                  real-yield moves (90 days and 1 year), and its correlation with weekly liquidity
                  changes (1 and 3 years).
  Regime study    BTC's median 13-week-forward return after weeks of contracting, mildly expanding and
                  strongly expanding net liquidity (since 2016), with sample sizes.

Limits: net liquidity is a popular approximation, not an official statistic (it ignores bank reserves
detail, foreign repo and other facilities). Correlations move around and are not causation; the regime
study uses overlapping windows and a few market cycles, so treat it as context, not a forecast.
Fed and Treasury data is published with a lag (the latest weekly Fed figures are for last Wednesday).
"""
import csv
import io
import math
import time
from datetime import datetime, timedelta, timezone

import requests

from .net import get_json
from .stats import percentile_rank, mean, stdev

M = "https://mempool.space/api"
DAY = 86400
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def fred(series, since="2013-01-01"):
    for attempt in range(4):
        r = requests.get(FRED, params={"id": series, "cosd": since}, timeout=40, headers={"User-Agent": "The Crypto Playback info@cryptoplayback.com"})
        if r.status_code == 200:
            rows = list(csv.reader(io.StringIO(r.text)))[1:]
            return {d: float(v) for d, v in rows if v not in (".", "")}
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"FRED {series} unavailable")


def btc_daily():
    rows = get_json(f"{M}/v1/historical-price?currency=USD", timeout=90)["prices"]
    px = {}
    for r in sorted(rows, key=lambda r: r["time"]):
        if r.get("USD"):
            px[datetime.fromtimestamp(r["time"], timezone.utc).strftime("%Y-%m-%d")] = float(r["USD"])
    return px


def _asof(series_sorted, date):
    """Last value at or before `date` from a sorted [(date, value)] list (binary search)."""
    lo, hi = 0, len(series_sorted) - 1
    ans = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if series_sorted[mid][0] <= date:
            ans, lo = series_sorted[mid][1], mid + 1
        else:
            hi = mid - 1
    return ans


def _corr(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 20:
        return None
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return None if not sx or not sy else sum((x - mx) * (y - my) for x, y in pairs) / (sx * sy)


def _beta(y, x):
    pairs = [(a, b) for a, b in zip(y, x) if a is not None and b is not None]
    if len(pairs) < 20:
        return None
    mx = sum(p[1] for p in pairs) / len(pairs)
    my = sum(p[0] for p in pairs) / len(pairs)
    vx = sum((p[1] - mx) ** 2 for p in pairs)
    return None if not vx else sum((p[1] - mx) * (p[0] - my) for p in pairs) / vx


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def compute():
    walcl, tga, rrp = fred("WALCL"), fred("WTREGEN"), fred("RRPONTSYD")
    real, usd10 = fred("DFII10"), None
    dxy = fred("DTWEXBGS")
    px = btc_daily()
    pxs = sorted(px.items())
    rrps = sorted(rrp.items())

    # ---- weekly net liquidity ($ billions) on the Fed's Wednesday dates
    weeks = []
    for d in sorted(walcl):
        if d in tga:
            r = _asof(rrps, d) or 0.0
            nl = walcl[d] / 1000.0 - tga[d] / 1000.0 - r
            weeks.append({"d": d, "nl": nl, "fed": walcl[d] / 1000.0, "tga": tga[d] / 1000.0, "rrp": r, "btc": _asof(pxs, d)})
    weeks = [w for w in weeks if w["d"] >= "2013-06-01" and w["btc"]]
    n = len(weeks)
    if n < 200:
        raise RuntimeError("liquidity history unexpectedly short")
    nl = [w["nl"] for w in weeks]

    def chg(i, k):
        return None if i - k < 0 else nl[i] - nl[i - k]

    def pct(i, k):
        return None if i - k < 0 else (nl[i] / nl[i - k] - 1.0) * 100.0
    imp = [pct(i, 13) for i in range(n)]                                   # 13-week impulse (%)
    cur = weeks[-1]
    comp_rows = []
    for key, label in (("fed", "Fed balance sheet"), ("tga", "Treasury cash account (subtracts)"), ("rrp", "Reverse repo (subtracts)")):
        comp_rows.append({"key": key, "label": label, "level_b": cur[key],
                          "chg_4w_b": cur[key] - weeks[-5][key], "chg_13w_b": cur[key] - weeks[-14][key],
                          "effect_13w_b": (cur[key] - weeks[-14][key]) * (1 if key == "fed" else -1)})

    # ---- macro series: 63-trading-day changes
    def last_n_changes(series, k, pct_change):
        keys = sorted(series)
        vals = [series[x] for x in keys]
        out = []
        for i in range(k, len(vals)):
            out.append((vals[i] / vals[i - k] - 1.0) * 100.0 if pct_change else vals[i] - vals[i - k])
        return keys[k:], out
    _, real_chg = last_n_changes(real, 63, False)
    _, dxy_chg = last_n_changes(dxy, 63, True)
    ten = "2016-01-01"
    imp_hist = [imp[i] for i in range(n) if imp[i] is not None and weeks[i]["d"] >= ten]
    real_hist = [v for k, v in zip(sorted(real)[63:], real_chg) if k >= ten]
    dxy_hist = [v for k, v in zip(sorted(dxy)[63:], dxy_chg) if k >= ten]
    p_liq = percentile_rank(imp[-1], imp_hist)
    p_real = 100.0 - percentile_rank(real_chg[-1], real_hist)
    p_dxy = 100.0 - percentile_rank(dxy_chg[-1], dxy_hist)
    score = 0.40 * p_liq + 0.30 * p_real + 0.30 * p_dxy
    label = "Tailwind" if score >= 62 else "Headwind" if score <= 38 else "Mixed"
    comps = [
        {"key": "liq", "label": "Liquidity impulse", "weight": 0.40, "score": round(p_liq), "readout": f"net liquidity {imp[-1]:+.1f}% over 13 weeks ({chg(n - 1, 13):+,.0f}B)"},
        {"key": "real", "label": "Real-yield pressure", "weight": 0.30, "score": round(p_real),
         "readout": f"10-year real yield {real[sorted(real)[-1]]:.2f}%, {real_chg[-1]:+.2f} pts over ~3 months"},
        {"key": "usd", "label": "Dollar pressure", "weight": 0.30, "score": round(p_dxy),
         "readout": f"broad dollar index {dxy_chg[-1]:+.1f}% over ~3 months"},
    ]

    # ---- sensitivity: weekly liquidity vs BTC, daily dollar / real-yield vs BTC
    wk_btc = [None] + [math.log(weeks[i]["btc"] / weeks[i - 1]["btc"]) for i in range(1, n)]
    wk_nl = [None] + [(nl[i] / nl[i - 1] - 1.0) * 100.0 for i in range(1, n)]
    corr_liq = {"1y": _corr(wk_btc[-52:], wk_nl[-52:]), "3y": _corr(wk_btc[-156:], wk_nl[-156:])}
    days = sorted(set(px) & set(dxy) & set(real))
    r_btc, r_dxy, r_real = [], [], []
    for i in range(1, len(days)):
        a, b = days[i - 1], days[i]
        r_btc.append(math.log(px[b] / px[a]))
        r_dxy.append((dxy[b] / dxy[a] - 1.0) * 100.0)
        r_real.append((real[b] - real[a]) * 100.0)                       # basis points
    sens = {
        "dollar": {"corr_90d": _corr(r_btc[-90:], r_dxy[-90:]), "corr_1y": _corr(r_btc[-252:], r_dxy[-252:]), "beta_1y": _beta([x * 100 for x in r_btc[-252:]], r_dxy[-252:])},
        "real_yield": {"corr_90d": _corr(r_btc[-90:], r_real[-90:]), "corr_1y": _corr(r_btc[-252:], r_real[-252:])},
        "liquidity_weekly": corr_liq,
    }
    # rolling 1-year correlation to the dollar, sampled monthly for the last 3 years
    roll = {"d": [], "dollar": [], "real_yield": []}
    for end in range(len(r_btc) - 252 * 3, len(r_btc), 21):
        if end - 252 < 0:
            continue
        roll["d"].append(days[end + 1])
        roll["dollar"].append(_corr(r_btc[end - 252:end], r_dxy[end - 252:end]))
        roll["real_yield"].append(_corr(r_btc[end - 252:end], r_real[end - 252:end]))

    # ---- regime study: 13-week forward BTC return by liquidity regime since 2016
    fwd = [(weeks[i + 13]["btc"] / weeks[i]["btc"] - 1.0) * 100.0 if i + 13 < n else None for i in range(n)]
    idx = [i for i in range(n) if imp[i] is not None and weeks[i]["d"] >= ten and fwd[i] is not None]
    pos = sorted(imp[i] for i in idx if imp[i] > 0)
    cut = pos[len(pos) // 2] if pos else 0
    buckets = [("Contracting (13-week change below 0)", lambda v: v <= 0), ("Mildly expanding", lambda v: 0 < v <= cut), ("Strongly expanding", lambda v: v > cut)]
    regimes = []
    for name, f in buckets:
        sel = [fwd[i] for i in idx if f(imp[i])]
        regimes.append({"regime": name, "weeks": len(sel), "median_13w": _median(sel), "positive_pct": (100.0 * sum(1 for x in sel if x > 0) / len(sel)) if sel else None})
    which = "Contracting (13-week change below 0)" if imp[-1] <= 0 else ("Mildly expanding" if imp[-1] <= cut else "Strongly expanding")

    # ---- charts: net liquidity vs BTC rebased, last 2 years of weekly points
    k = 104
    base_nl, base_btc = nl[-k], weeks[-k]["btc"]
    chart = {"t": [int(datetime.strptime(w["d"], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) for w in weeks[-k:]],
             "nl_index": [round(w["nl"] / base_nl * 100.0, 1) for w in weeks[-k:]], "btc_index": [round(w["btc"] / base_btc * 100.0, 1) for w in weeks[-k:]],
             "nl_t": [round(w["nl"] / 1000.0, 3) for w in weeks[-156:]],
             "nl_t_ts": [int(datetime.strptime(w["d"], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) for w in weeks[-156:]]}
    lvl_corr_2y = _corr(nl[-104:], [w["btc"] for w in weeks[-104:]])

    read_bits = []
    read_bits.append(f"US net liquidity is ${cur['nl'] / 1000:.2f} trillion, {'up' if imp[-1] > 0 else 'down'} {abs(imp[-1]):.1f}% over 13 weeks")
    if abs(comp_rows[1]["effect_13w_b"]) > 20 or abs(comp_rows[2]["effect_13w_b"]) > 20:
        mover = max(comp_rows, key=lambda r: abs(r["effect_13w_b"]))
        read_bits.append(f"mostly because of the {mover['label'].split(' (')[0].lower()} ({mover['effect_13w_b']:+,.0f}B effect)")
    read_bits.append(f"real yields are {'rising' if real_chg[-1] > 0.05 else 'falling' if real_chg[-1] < -0.05 else 'flat'} and the dollar is {'firming' if dxy_chg[-1] > 0.5 else 'softening' if dxy_chg[-1] < -0.5 else 'steady'}")
    read = ", ".join(read_bits[:1]) + (" " + "; ".join(read_bits[1:]) if len(read_bits) > 1 else "") + f". The overall backdrop reads {label.lower()}."

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok", "read": read,
        "backdrop": {"score": round(score, 1), "label": label, "components": comps},
        "net_liquidity": {"asof": cur["d"], "level_b": cur["nl"], "chg_4w_b": chg(n - 1, 4), "chg_13w_b": chg(n - 1, 13), "chg_13w_pct": imp[-1],
                          "percentile_10y": percentile_rank(cur["nl"], [v for v, w in zip(nl, weeks) if w["d"] >= ten]), "components": comp_rows},
        "macro": {"real_yield": real[sorted(real)[-1]], "real_yield_asof": sorted(real)[-1], "real_yield_chg_3m": real_chg[-1],
                  "dollar": dxy[sorted(dxy)[-1]], "dollar_asof": sorted(dxy)[-1], "dollar_chg_3m_pct": dxy_chg[-1]},
        "sensitivity": sens, "rolling": roll, "level_corr_2y": lvl_corr_2y,
        "regimes": {"current": which, "table": regimes, "since": "2016"},
        "chart": chart,
    }


if __name__ == "__main__":
    import json
    o = compute()
    print(json.dumps({k: v for k, v in o.items() if k not in ("chart", "rolling")}, indent=1, default=str)[:4200])
