"""
fetch_dominance.py — BTC's share of total crypto market cap, straight from
CoinGecko's free /global endpoint (one call, no per-coin math needed - the
endpoint already returns each coin's market_cap_percentage directly).

Requires env var: COINGECKO_API_KEY
"""
import os
import requests


def get_btc_dominance():
    api_key = os.environ["COINGECKO_API_KEY"]
    url = "https://api.coingecko.com/api/v3/global"
    headers = {"x-cg-demo-api-key": api_key}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()["data"]

    return {
        "btc_dominance_pct": data["market_cap_percentage"]["btc"],
        "total_market_cap_usd": data["total_market_cap"]["usd"],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_btc_dominance(), indent=2))
