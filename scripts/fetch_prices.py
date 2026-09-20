"""
fetch_prices.py — pulls the top 5 coins by market cap (excluding stablecoins)
from CoinGecko's free Demo API.

Requires env var: COINGECKO_API_KEY
"""
import os
import requests

STABLECOINS = {"usdt", "usdc", "dai", "fdusd", "usde", "busd", "tusd"}


def get_top_prices(count=5):
    api_key = os.environ["COINGECKO_API_KEY"]
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 20,  # grab extra so we can filter stablecoins and still have 5
        "page": 1,
        "price_change_percentage": "24h",
    }
    headers = {"x-cg-demo-api-key": api_key}
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for coin in data:
        if coin["symbol"].lower() in STABLECOINS:
            continue
        results.append({
            "symbol": coin["symbol"].upper(),
            "name": coin["name"],
            "price": coin["current_price"],
            "change_24h": coin.get("price_change_percentage_24h") or 0,
        })
        if len(results) == count:
            break
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(get_top_prices(), indent=2))
