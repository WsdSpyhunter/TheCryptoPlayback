"""
fetch_sectors.py — pulls 24h performance for a curated set of major crypto
sector/narrative categories from CoinGecko's free Demo API, and returns the
top N by 24h market cap change.

Requires env var: COINGECKO_API_KEY
"""
import os
import requests

# CoinGecko has 700+ categories, most far too narrow/noisy (e.g. "TikTok
# Meme", "Robinhood Chain Meme") to make a meaningful "top sectors" reading.
# We rank within this curated watchlist of recognizable, broad narrative
# sectors instead of the full unfiltered list.
SECTOR_WATCHLIST = {
    "Real World Assets (RWA)": "RWA",
    "Artificial Intelligence (AI)": "AI",
    "Decentralized Finance (DeFi)": "DeFi",
    "Layer 1 (L1)": "L1",
    "Layer 2 (L2)": "L2",
    "Gaming (GameFi)": "Gaming",
    "Meme": "Memecoins",
    "DePIN": "DePIN",
    "NFT": "NFT",
}


def get_top_sectors(count=3):
    api_key = os.environ["COINGECKO_API_KEY"]
    url = "https://api.coingecko.com/api/v3/coins/categories"
    params = {"order": "market_cap_desc"}
    headers = {"x-cg-demo-api-key": api_key}
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for cat in data:
        label = SECTOR_WATCHLIST.get(cat["name"])
        if not label:
            continue
        change = cat.get("market_cap_change_24h")
        if change is None:
            continue
        results.append({"label": label, "change_24h": change})

    results.sort(key=lambda s: s["change_24h"], reverse=True)
    return results[:count]


if __name__ == "__main__":
    import json
    print(json.dumps(get_top_sectors(), indent=2))
