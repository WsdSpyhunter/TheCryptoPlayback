"""
fetch_leverage.py — BTC perpetual futures funding rate + open interest from
OKX's free public API (no key, no auth). Binance's equivalent endpoint is
geo-blocked for US-region requests (confirmed live: "Service unavailable
from a restricted location"), which would silently break on GitHub Actions'
US-hosted runners - OKX's public market-data endpoints have no such
restriction.

Funding is the periodic payment between long and short perpetual futures
holders (positive rate: longs pay shorts) - a direct, real-time read on
which side is more crowded with leverage, not a derived proxy.
"""
import requests

FUNDING_URL = "https://www.okx.com/api/v5/public/funding-rate"
OI_URL = "https://www.okx.com/api/v5/public/open-interest"
INST_ID = "BTC-USDT-SWAP"


def get_funding_and_oi():
    resp = requests.get(FUNDING_URL, params={"instId": INST_ID}, timeout=15)
    resp.raise_for_status()
    funding_data = resp.json()["data"][0]

    resp = requests.get(OI_URL, params={"instId": INST_ID}, timeout=15)
    resp.raise_for_status()
    oi_data = resp.json()["data"][0]

    return {
        "funding_rate_pct": float(funding_data["fundingRate"]) * 100,
        "next_funding_time_ms": int(funding_data["nextFundingTime"]),
        "open_interest_usd": float(oi_data["oiUsd"]),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_funding_and_oi(), indent=2))
