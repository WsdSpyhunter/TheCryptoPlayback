"""
fetch_liquidations.py — recent BTC perpetual futures liquidations from OKX's
free public API (no key, no auth). Covers OKX's own order flow only, not an
aggregate across every exchange (there's no free, no-key source for that -
the well-known aggregators like Coinglass require a paid plan) - documented
plainly on the indicator's own page, same honesty as XOOMAR only covering
3 of the US spot BTC ETFs for validation.

Returns the most recent 100 filled liquidation events, which is a variable
time window (a few minutes during high volatility, over an hour when quiet)
rather than a fixed lookback - the window length itself is informative.
"""
import requests

LIQUIDATIONS_URL = "https://www.okx.com/api/v5/public/liquidation-orders"
CONTRACT_VALUE_BTC = 0.01  # BTC-USDT-SWAP: 1 contract = 0.01 BTC (see /public/instruments)


def get_recent_liquidations():
    resp = requests.get(LIQUIDATIONS_URL, params={
        "instType": "SWAP", "instFamily": "BTC-USDT", "state": "filled",
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()["data"]
    details = data[0]["details"] if data else []

    long_usd = 0.0
    short_usd = 0.0
    timestamps = []
    for event in details:
        notional = float(event["sz"]) * CONTRACT_VALUE_BTC * float(event["bkPx"])
        if event["posSide"] == "long":
            long_usd += notional
        else:
            short_usd += notional
        timestamps.append(int(event["ts"]))

    window_minutes = (max(timestamps) - min(timestamps)) / 60000 if len(timestamps) >= 2 else 0.0

    return {
        "long_liq_usd": long_usd,
        "short_liq_usd": short_usd,
        "event_count": len(details),
        "window_minutes": window_minutes,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_recent_liquidations(), indent=2))
