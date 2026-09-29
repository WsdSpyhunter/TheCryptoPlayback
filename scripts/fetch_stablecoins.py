"""
fetch_stablecoins.py — pulls aggregate stablecoin market cap from DefiLlama's
free public stablecoins API (no key needed) and derives the 7-day change.
"""
import requests

API_URL = "https://stablecoins.llama.fi/stablecoincharts/all"


def get_stablecoin_liquidity():
    """Returns {'total_usd': float, 'change_7d_pct': float}. The endpoint
    returns one row per day, oldest first, so the 7-days-ago reading is
    just 8 rows back from the latest (today + 7 full days)."""
    resp = requests.get(API_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if len(data) < 8:
        raise ValueError(f"expected at least 8 days of stablecoin history, got {len(data)}")

    total_now = float(data[-1]["totalCirculating"]["peggedUSD"])
    total_week_ago = float(data[-8]["totalCirculating"]["peggedUSD"])
    change_7d_pct = (total_now - total_week_ago) / total_week_ago * 100

    return {
        "total_usd": total_now,
        "change_7d_pct": change_7d_pct,
    }


if __name__ == "__main__":
    print(get_stablecoin_liquidity())
