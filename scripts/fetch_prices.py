"""
fetch_prices.py — pulls the top 6 coins by market cap (excluding stablecoins)
from CoinGecko's free Demo API.

Requires env var: COINGECKO_API_KEY
"""
import os
import requests

STABLECOINS = {"usdt", "usdc", "dai", "fdusd", "usde", "busd", "tusd", "usds", "usd1", "usdg", "pyusd", "usdtb", "rlusd", "usdd"}

# Not crypto-native price discovery: tokenized loans, treasuries, gold, wrapped/staked copies.
# These would make the Biggest Mover and Top 6 read like something other than the crypto market.
NON_NATIVE = {"figr_heloc", "xaut", "paxg", "buidl", "usyc", "ousg", "wbtc", "cbbtc", "steth", "wsteth", "weth", "weeth", "wbeth", "reth", "jitosol", "msol"}
NON_NATIVE_IDS = {"figure-heloc"}


def _excluded(coin):
    sym = coin["symbol"].lower()
    if sym in STABLECOINS or sym in NON_NATIVE or coin.get("id") in NON_NATIVE_IDS:
        return True
    # Unlisted dollar-pegged coins: sitting on $1 with almost no movement.
    price = coin.get("current_price") or 0
    chg = coin.get("price_change_percentage_24h") or 0
    return 0.97 <= price <= 1.03 and abs(chg) < 0.3

# The Top 6 Market ticker shows the first 6 coins; the Biggest Mover (24H)
# indicator looks at the first 10 (same ranking, stablecoins excluded).
TICKER_COINS = 6
MOVER_POOL = 10


def get_top_prices(count=6):
    api_key = os.environ["COINGECKO_API_KEY"]
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 50,  # grab extra so we can filter out stablecoins/tokenized assets and still fill the pool
        "page": 1,
        "price_change_percentage": "24h,7d",
    }
    headers = {"x-cg-demo-api-key": api_key}
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for coin in data:
        if _excluded(coin):
            continue
        results.append({
            "id": coin["id"],
            "symbol": coin["symbol"].upper(),
            "name": coin["name"],
            "price": coin["current_price"],
            "change_24h": coin.get("price_change_percentage_24h") or 0,
            "change_7d": coin.get("price_change_percentage_7d_in_currency") or 0,
        })
        if len(results) == count:
            break
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(get_top_prices(), indent=2))
