"""
fetch_defi_tvl.py — pulls total DeFi Total Value Locked (all chains, all
protocols) from DefiLlama's free public API (no key needed) and derives the
7-day change. Same shape as fetch_stablecoins.py, but a genuinely different
metric: stablecoin supply is dry powder sitting in USD-pegged tokens, TVL is
capital actually deployed/locked into DeFi protocols (and moves with the
price of what's locked, not just fresh capital in/out).
"""
import requests

API_URL = "https://api.llama.fi/v2/historicalChainTvl"


def get_defi_tvl():
    """Returns {'total_usd': float, 'change_7d_pct': float}. The endpoint
    returns one row per day, oldest first, so the 7-days-ago reading is
    just 8 rows back from the latest (today + 7 full days)."""
    resp = requests.get(API_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if len(data) < 8:
        raise ValueError(f"expected at least 8 days of TVL history, got {len(data)}")

    total_now = float(data[-1]["tvl"])
    total_week_ago = float(data[-8]["tvl"])
    change_7d_pct = (total_now - total_week_ago) / total_week_ago * 100

    return {
        "total_usd": total_now,
        "change_7d_pct": change_7d_pct,
    }


if __name__ == "__main__":
    print(get_defi_tvl())
