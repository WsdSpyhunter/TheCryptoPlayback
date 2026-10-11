"""Bitcoin Trend & Volatility.

The plainest question about Bitcoin is also the one the other indicators do not answer directly:
which way is the price trending, and how violently is it moving? Mood, flows, leverage and macro
are all read against that backdrop. This module measures it from free, open price history.

Source: mempool.space's public price history (daily, since 2010), the same feed Miner Stress uses.

Measures
  Moving averages   50-day and 200-day simple averages, and where the price sits against each.
  Trend state       0-3 points: price above its 200-day, price above its 50-day, 50-day above 200-day.
                    3 = Uptrend, 0 = Downtrend, 1-2 = Mixed (a trend in transition).
  Cross             Golden cross (50-day rises above 200-day) / death cross (falls below), and how
                    many days ago it happened.
  Momentum          30-day and 90-day price change, plus the 14-day RSI (Wilder).
  Volatility        30-day realized volatility (annualised standard deviation of daily returns),
                    its percentile against every day since 2013, and whether it is expanding or
                    contracting versus the 90-day figure.
  Drawdown          distance below the all-time high.

Event study (descriptive, with sample sizes): what BTC did over the following 30 / 90 days after
every day in each trend state since 2013, versus an average day. Windows overlap, so the number of
independent episodes is far smaller than the number of days. This is context, not a forecast.
"""
import math
import os
from datetime import datetime, timezone

from .net import get_json
from .stats import mean, stdev, percentile_rank, rolling_mean

M = "https://mempool.space/api"
DAY = 86400
STUDY_START = "2013-01-01"


def _day(ts):
    return int(ts) // DAY * DAY


def load_prices():
    raw = get_json(f"{M}/v1/historical-price?currency=USD", timeout=90)["prices"]
    px = {}
    for r in sorted(raw, key=lambda r: r["time"]):          # last price of each UTC day
        if r.get("USD"):
            px[_day(r["time"])] = float(r["USD"])
    ts = sorted(px)
    out_t, out_p, last = [], [], None
    t = ts[0]
    while t <= ts[-1]:                                       # forward-fill missing days
        last = px.get(t, last)
        out_t.append(t)
        out_p.append(last)
        t += DAY
    return out_t, out_p


def _rsi(P, n=14):
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = P[i] - P[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / n, losses / n
    out = [None] * n + [100.0 if al == 0 else 100 - 100 / (1 + ag / al)]
    for i in range(n + 1, len(P)):
        d = P[i] - P[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
        out.append(100.0 if al == 0 else 100 - 100 / (1 + ag / al))
    return out


def _realized_vol(P, n):
    rets = [None] + [math.log(P[i] / P[i - 1]) for i in range(1, len(P))]
    out = []
    for i in range(len(P)):
        w = rets[i - n + 1:i + 1] if i >= n else []
        out.append(stdev(w) * math.sqrt(365) * 100 if len(w) == n and None not in w else None)
    return out


def _state(p, s50, s200):
    if s200 is None or s50 is None:
        return None
    return int(p > s200) + int(p > s50) + int(s50 > s200)


STATE_NAMES = {3: "Uptrend", 0: "Downtrend"}


def _label(pts):
    return "Uptrend" if pts == 3 else "Downtrend" if pts == 0 else "Mixed"


def _ord(x):
    n = int(round(x))
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _fwd(P, i, lag):
    j = i + lag
    return (P[j] / P[i] - 1) * 100 if j < len(P) else None


def _summ(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return {"n": 0, "median": None, "hit": None}
    return {"n": len(xs), "median": xs[len(xs) // 2], "hit": 100.0 * sum(1 for x in xs if x > 0) / len(xs)}


def compute():
    T, P = load_prices()
    if len(P) < 400:
        raise RuntimeError("not enough price history")
    s50 = rolling_mean(P, 50)
    s200 = rolling_mean(P, 200)
    s50 = [v if i >= 49 else None for i, v in enumerate(s50)]
    s200 = [v if i >= 199 else None for i, v in enumerate(s200)]
    rsi = _rsi(P)
    v30, v90 = _realized_vol(P, 30), _realized_vol(P, 90)
    n = len(P) - 1
    price = P[n]
    states = [_state(P[i], s50[i], s200[i]) for i in range(len(P))]
    pts = states[n]

    # cross: last day the 50 vs 200 ordering flipped
    above = [(a > b) if (a is not None and b is not None) else None for a, b in zip(s50, s200)]
    cross_i = None
    for i in range(n, 0, -1):
        if above[i] is not None and above[i - 1] is not None and above[i] != above[i - 1]:
            cross_i = i
            break
    cross = {"state": "Golden cross" if above[n] else "Death cross",
             "days_since": (n - cross_i) if cross_i else None,
             "date": datetime.fromtimestamp(T[cross_i], timezone.utc).strftime("%Y-%m-%d") if cross_i else None}

    # volatility percentile vs every day since 2013
    k0 = next(i for i, t in enumerate(T) if t >= int(datetime.strptime(STUDY_START, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()))
    vol_hist = [v for v in v30[k0:n + 1] if v is not None]
    vol_pct = percentile_rank(v30[n], vol_hist)
    vol_label = ("Extreme" if vol_pct >= 90 else "Elevated" if vol_pct >= 70 else "Calm" if vol_pct < 30 else "Normal")
    vol_dir = "Expanding" if v30[n] > v90[n] * 1.1 else "Contracting" if v30[n] < v90[n] * 0.9 else "Steady"

    ath = max(P)
    ath_i = P.index(ath)
    drawdown = (price / ath - 1) * 100
    dist50 = (price / s50[n] - 1) * 100
    dist200 = (price / s200[n] - 1) * 100
    slope200 = (s200[n] / s200[n - 30] - 1) * 100            # 200-day average, change over 30 days

    # event study by trend state since 2013 (forward returns need data after the day)
    study = {}
    base30 = [_fwd(P, i, 30) for i in range(k0, len(P))]
    base90 = [_fwd(P, i, 90) for i in range(k0, len(P))]
    for key, test in (("Uptrend", lambda s: s == 3), ("Mixed", lambda s: s in (1, 2)), ("Downtrend", lambda s: s == 0)):
        idx = [i for i in range(k0, len(P)) if states[i] is not None and test(states[i])]
        study[key] = {"days": len(idx), "d30": _summ([_fwd(P, i, 30) for i in idx]), "d90": _summ([_fwd(P, i, 90) for i in idx])}
    study["All days"] = {"days": len(base30), "d30": _summ(base30), "d90": _summ(base90)}
    # volatility regimes
    vstudy = {}
    for key, test in (("Calm (bottom 30%)", lambda p: p < 30), ("Normal", lambda p: 30 <= p < 70), ("Elevated (top 30%)", lambda p: p >= 70)):
        idx = []
        for i in range(k0, len(P)):
            if v30[i] is None:
                continue
            if test(percentile_rank(v30[i], vol_hist)):
                idx.append(i)
        vstudy[key] = {"days": len(idx), "d30": _summ([_fwd(P, i, 30) for i in idx]), "d90": _summ([_fwd(P, i, 90) for i in idx])}

    # plain-English read
    side = {3: "above both its 50-day and 200-day averages, with the 50-day above the 200-day",
            0: "below both its 50-day and 200-day averages, with the 50-day below the 200-day"}.get(pts)
    if side is None:
        bits = []
        bits.append("above its 200-day" if price > s200[n] else "below its 200-day")
        bits.append("above its 50-day" if price > s50[n] else "below its 50-day")
        bits.append("with the 50-day " + ("above" if s50[n] > s200[n] else "below") + " the 200-day")
        side = ", ".join(bits)
    read = (f"Bitcoin is {side}: {"an" if pts == 3 else "a"} {_label(pts).lower()} reading. It is {abs(dist200):.0f}% {'above' if dist200 >= 0 else 'below'} its 200-day average and "
            f"{abs(drawdown):.0f}% below its all-time high. Realized volatility is {vol_label.lower()} ({_ord(vol_pct)} percentile since 2013) and {vol_dir.lower()}.")

    k = 730
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok",
        "price_usd": price, "as_of": datetime.fromtimestamp(T[n], timezone.utc).strftime("%Y-%m-%d"),
        "trend": {"points": pts, "label": _label(pts), "above_200": price > s200[n], "above_50": price > s50[n], "ma50_above_200": s50[n] > s200[n],
                  "sma50": s50[n], "sma200": s200[n], "dist50_pct": dist50, "dist200_pct": dist200, "slope200_30d_pct": slope200, "cross": cross},
        "momentum": {"ret_30d": (price / P[n - 30] - 1) * 100, "ret_90d": (price / P[n - 90] - 1) * 100, "rsi14": rsi[n]},
        "volatility": {"vol30": v30[n], "vol90": v90[n], "percentile": vol_pct, "label": vol_label, "direction": vol_dir},
        "drawdown": {"from_ath_pct": drawdown, "ath_usd": ath, "ath_date": datetime.fromtimestamp(T[ath_i], timezone.utc).strftime("%Y-%m-%d")},
        "read": read, "events": {"trend": study, "volatility": vstudy},
        "history": {"t": T[-k:], "price": [round(x) for x in P[-k:]], "sma50": [round(x) if x else None for x in s50[-k:]],
                    "sma200": [round(x) if x else None for x in s200[-k:]], "vol30": [round(x, 1) if x else None for x in v30[-k:]]},
    }


if __name__ == "__main__":
    import json
    o = compute()
    print(json.dumps({k: v for k, v in o.items() if k != "history"}, indent=1, default=str)[:4500])
