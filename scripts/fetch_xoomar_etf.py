"""
fetch_xoomar_etf.py — independent validation source for BTC ETF flow,
derived from issuers' own daily holdings files rather than copied from
Farside. Free, no API key. Currently covers only IBIT (iShares/BlackRock),
BITB (Bitwise), and ARKB (ARK 21Shares) for BTC - NOT the full US spot BTC
ETF universe, so this is only ever used as a same-subset cross-check
against SoSoValue, never as the primary/displayed total.

Attribution (per XOOMAR's terms): data via xoomar.com.
"""
import requests

API_URL = "https://xoomar.com/api/markets/etf-flows"
COVERED_TICKERS = ["IBIT", "BITB", "ARKB"]


def get_btc_flows(days=90):
    """One row per ticker per day: {date, ticker, issuer, flowUsd, aumUsd,
    holdings}. Returns [] (not an exception) on any failure - this is a
    validation source, never something that should block the primary
    SoSoValue reading from publishing."""
    try:
        resp = requests.get(API_URL, params={"asset": "btc", "days": days}, timeout=20)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except (requests.RequestException, ValueError):
        return []


if __name__ == "__main__":
    rows = get_btc_flows(days=7)
    for row in rows[:10]:
        print(row["date"], row["ticker"], row["flowUsd"])
