"""
fetch_etf_flows.py — primary ETF flow data source, SoSoValue's Open API
(free tier, documented 20 req/min). Requires env var SOSOVALUE_API_KEY.

Docs: https://sosovalue-1.gitbook.io/sosovalue-api-doc
Base URL and auth header are exactly as documented there; verified against
live responses (2026-09-29) rather than assumed from the docs' examples -
the live response wraps the array in {"code","message","data"}, which the
docs' own example does not show.
"""
import os
import requests

BASE_URL = "https://openapi.sosovalue.com/openapi/v1"

# The three issuers XOOMAR (the validation source) currently covers for
# BTC - see fetch_xoomar_etf.py. Kept here so both modules agree on the
# comparable subset without hardcoding it in two places.
XOOMAR_COVERED_TICKERS = ["IBIT", "BITB", "ARKB"]


def _headers():
    return {"x-soso-api-key": os.environ["SOSOVALUE_API_KEY"]}


def _get(path, params=None):
    resp = requests.get(f"{BASE_URL}{path}", headers=_headers(), params=params, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise ValueError(f"SoSoValue API error {body.get('code')}: {body.get('message')}")
    return body["data"]


def get_btc_summary_history(limit=95):
    """Aggregate daily net flow across ALL US spot BTC ETFs (SoSoValue's
    own total, not just the XOOMAR-covered subset). Rows are already
    trading-days-only (weekends/holidays excluded by the API itself), so
    no separate market-calendar logic is needed to compute streaks/windows
    from this list - consecutive rows are consecutive trading days.
    Latest-first, capped at `limit` (API max 300)."""
    rows = _get("/etfs/summary-history", params={
        "symbol": "BTC", "country_code": "US", "limit": min(limit, 300),
    })
    # Defensive: the aggregate endpoint hasn't shown unsettled/null rows in
    # testing, but never treat a missing total as a real zero if it shows up.
    return [r for r in rows if r.get("total_net_inflow") is not None]


def get_ticker_history(ticker, days_back=None):
    """Per-ticker daily net flow. The most recent row is sometimes still
    unsettled (T+1 settlement) and comes back with net_inflow: null while
    value_traded/volume are already populated - those rows are filtered
    out here rather than ever being treated as a real zero flow."""
    params = {}
    resp = requests.get(f"{BASE_URL}/etfs/{ticker}/history", headers=_headers(),
                         params=params, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise ValueError(f"SoSoValue API error {body.get('code')}: {body.get('message')}")
    rows = [r for r in body["data"] if r.get("net_inflow") is not None]
    if days_back:
        rows = rows[:days_back]
    return rows


if __name__ == "__main__":
    history = get_btc_summary_history(limit=5)
    for row in history:
        print(row["date"], row["total_net_inflow"])
