"""
fetch_market_breadth.py — one CoinGecko Demo API call per day, pulling
current prices for the top ~60 coins by market cap (buffer above the 40
we actually track, so a handful of stablecoin/wrapped-token filters still
leave 40). Reuses the same free key as fetch_prices.py.

Requires env var: COINGECKO_API_KEY
"""
import os
import requests

STABLECOINS = {
    "usdt", "usdc", "dai", "fdusd", "usde", "busd", "tusd", "usds", "pyusd",
    "frax", "gusd", "usdp", "lusd",
}
WRAPPED_OR_STAKED = {
    # Wrapped/staked/bridged versions of a coin already counted natively -
    # counting both would double-weight one underlying asset in the breadth
    # universe.
    "wbtc", "weth", "wsteth", "steth", "wbeth", "cbbtc", "reth",
}


def get_market_snapshot(fetch_count=60):
    """Returns [{id, symbol, price}] ordered by market cap, stablecoins and
    wrapped/staked tokens excluded. `id` is CoinGecko's own coin id - the
    stable key used to track each coin's price history over time."""
    api_key = os.environ["COINGECKO_API_KEY"]
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": fetch_count,
        "page": 1,
    }
    headers = {"x-cg-demo-api-key": api_key}
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for coin in data:
        symbol = coin["symbol"].lower()
        if symbol in STABLECOINS or symbol in WRAPPED_OR_STAKED:
            continue
        if coin.get("current_price") is None:
            continue
        results.append({"id": coin["id"], "symbol": coin["symbol"].upper(), "price": coin["current_price"]})
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(get_market_snapshot()[:10], indent=2))
