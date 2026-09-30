"""
refresh_indicators.py — refreshes the homepage's live indicator data
(prices, Fear & Greed, sectors, stablecoins, and whatever else joins this
list) completely independently of the newsletter's daily/weekly publish
cycle. Run on its own schedule by .github/workflows/refresh-indicators.yml
(every 15 minutes) so Market Snapshot / Signal Confluence / What Changed /
Alerts & Indicators stay current between newsletter issues, not just when
one publishes.

Writes data/live_indicators.json (the current reading) and appends to
data/indicator_history.json (a rolling log, capped at MAX_HISTORY_ENTRIES,
used for each indicator page's Recent Readings and for the "since ~24h
ago" comparison in What Changed). Then regenerates index.html and every
indicator page - NOT posts, archive, or the static pages, which this
script never touches.
"""
import json
import os
from datetime import datetime, timezone

from fetch_prices import get_top_prices
from fetch_sentiment import get_fear_greed
from fetch_sectors import get_top_sectors
from fetch_stablecoins import get_stablecoin_liquidity
from fetch_dominance import get_btc_dominance
from build_site import (
    ROOT, LIVE_DATA_FILE, LIVE_HISTORY_FILE, MAX_HISTORY_ENTRIES,
    compute_biggest_mover, compute_weekly_mover, save_gauge_image,
    load_index, render_index, render_indicator_pages,
)


def refresh():
    prices = get_top_prices()
    fng = get_fear_greed()
    sectors = get_top_sectors()
    stablecoins = get_stablecoin_liquidity()
    dominance = get_btc_dominance()
    mover = compute_biggest_mover(prices)
    week_mover = compute_weekly_mover(prices)
    # Fixed slug ("live", not a post slug) - this is the one gauge image
    # the live dashboard always points at, overwritten every refresh.
    gauge_path = save_gauge_image(fng["value"], "live")
    now = datetime.now(timezone.utc)

    live = {
        "updated_at": now.isoformat(),
        "prices": prices,
        "fng": fng,
        "mover": mover,
        "week_mover": week_mover,
        "sectors": sectors,
        "stablecoins": stablecoins,
        "dominance": dominance,
        "gauge_path": gauge_path,
    }
    with open(LIVE_DATA_FILE, "w") as f:
        json.dump(live, f, indent=2)

    history = []
    if os.path.exists(LIVE_HISTORY_FILE):
        try:
            with open(LIVE_HISTORY_FILE) as f:
                history = json.load(f)
        except (OSError, json.JSONDecodeError):
            history = []
    history.append(live)
    history = history[-MAX_HISTORY_ENTRIES:]
    with open(LIVE_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    entries = load_index()
    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(render_index(entries))
    for filename, html in render_indicator_pages(entries).items():
        with open(os.path.join(ROOT, filename), "w") as f:
            f.write(html)

    print(f"Refreshed live indicators at {live['updated_at']} "
          f"(F&G {fng['value']} {fng['classification']}, "
          f"stablecoins ${stablecoins['total_usd']/1e9:.1f}B, "
          f"BTC dominance {dominance['btc_dominance_pct']:.1f}%, "
          f"{len(history)} history entries)")


if __name__ == "__main__":
    refresh()
