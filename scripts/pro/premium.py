"""Coinbase Premium, computed from free public prices.

    premium = Coinbase BTC-USD / (OKX BTC-USDT x Kraken USDT-USD) - 1

Coinbase is the US-institutional venue quoted in real dollars. OKX BTC-USDT is
a deep offshore market quoted in Tether; multiplying by the USDT/USD rate
(Kraken) converts it to dollars so a small Tether discount or premium is not
mistaken for a Coinbase premium. (Binance, the usual reference, refuses US IPs.)
Expressed in basis points; positive = US buyers paying up.
"""
from datetime import datetime, timedelta, timezone

from .net import get_json

CB = "https://api.exchange.coinbase.com"
OKX = "https://www.okx.com/api/v5"
KRAKEN = "https://api.kraken.com/0/public"


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def coinbase_hourly(hours=720):
    """{hour_start_ts: close}; Coinbase returns at most 300 candles per call."""
    end = datetime.now(timezone.utc)
    out = {}
    remaining = hours
    while remaining > 0:
        n = min(300, remaining)
        start = end - timedelta(hours=n)
        rows = get_json(f"{CB}/products/BTC-USD/candles",
                        params={"granularity": 3600, "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "end": end.strftime("%Y-%m-%dT%H:%M:%SZ")})
        for r in rows:                       # [time, low, high, open, close, volume]
            out[int(r[0])] = float(r[4])
        end = start
        remaining -= n
    return out


def okx_hourly(hours=720):
    """{hour_start_ts: close} for BTC-USDT via history-candles (100 per page)."""
    out, after = {}, None
    while len(out) < hours:
        params = {"instId": "BTC-USDT", "bar": "1H", "limit": 100}
        if after:
            params["after"] = after
        rows = get_json(f"{OKX}/market/history-candles", params=params)["data"]
        if not rows:
            break
        for r in rows:                       # [ts, o, h, l, c, ...] newest first
            out[int(r[0]) // 1000] = float(r[4])
        after = rows[-1][0]
    return out


def kraken_usdt_usd_hourly():
    res = get_json(f"{KRAKEN}/OHLC", params={"pair": "USDTZUSD", "interval": 60})["result"]
    rows = next(v for k, v in res.items() if k != "last")
    return {int(r[0]): float(r[4]) for r in rows}


def premium_series(hours=720):
    """List of {t, premium_bps, coinbase, okx_usd}, oldest first, on common hours."""
    cb, okx, usdt = coinbase_hourly(hours), okx_hourly(hours), kraken_usdt_usd_hourly()
    out, last_usdt = [], None
    for t in sorted(set(cb) & set(okx)):
        last_usdt = usdt.get(t, last_usdt)
        if last_usdt is None:
            continue
        ref = okx[t] * last_usdt
        out.append({"t": t, "premium_bps": (cb[t] / ref - 1.0) * 1e4, "coinbase": cb[t], "okx_usd": ref})
    return out
