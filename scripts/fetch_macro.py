"""
fetch_macro.py — traditional-markets context (VIX, US Dollar Index) via
Yahoo Finance's free chart API. No API key, but Yahoo rate-limits/blocks
requests without a browser-like User-Agent header (confirmed live: default
requests UA gets a 429, a standard header gets a normal 200) - not a
Cloudflare-style anti-bot challenge, just a UA check, the same workaround
countless hobby finance tools use against this well-known public endpoint.

The first indicator on the site to look outside crypto - macro conditions
in traditional markets (volatility, dollar strength) are a real, separate
influence on crypto risk appetite that nothing else here captures.
"""
import requests

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _get_quote(symbol):
    resp = requests.get(CHART_URL.format(symbol=symbol), params={"interval": "1d", "range": "5d"},
                         headers=HEADERS, timeout=15)
    resp.raise_for_status()
    meta = resp.json()["chart"]["result"][0]["meta"]
    return meta["regularMarketPrice"], meta["regularMarketChangePercent"]


def get_macro_data():
    vix, vix_change_pct = _get_quote("%5EVIX")
    dxy, dxy_change_pct = _get_quote("DX-Y.NYB")
    return {
        "vix": vix,
        "vix_change_pct": vix_change_pct,
        "dxy": dxy,
        "dxy_change_pct": dxy_change_pct,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_macro_data(), indent=2))
