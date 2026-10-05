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
indicator page this workflow actually owns - NOT posts, archive, or the
static pages, and NOT etf-flow.html/market-breadth.html, which belong to
their own decoupled workflows (refresh_etf_flow.py/refresh_market_breadth.py)
and would otherwise get committed here with a stale timestamp context and
without .github/workflows/refresh-indicators.yml's git-add step even
knowing to stage them - the exact mismatch that broke the commit/push step
once Market Breadth and ETF Flow joined the shared indicator registry.
"""
import json
import os
from datetime import datetime, timezone

from fetch_prices import get_top_prices, TICKER_COINS, MOVER_POOL
from fetch_sentiment import get_fear_greed
from fetch_sectors import get_top_sectors
from fetch_stablecoins import get_stablecoin_liquidity
from fetch_dominance import get_btc_dominance
from fetch_leverage import get_funding_and_oi
from fetch_defi_tvl import get_defi_tvl
from fetch_network_health import get_network_health
from fetch_liquidations import get_recent_liquidations
from fetch_whale_activity import get_large_transaction_amounts
from fetch_macro import get_macro_data
from narrative_momentum_data import ingest_and_store as ingest_narrative_momentum
from build_site import (
    ROOT, LIVE_DATA_FILE, LIVE_HISTORY_FILE, MAX_HISTORY_ENTRIES,
    compute_biggest_mover, compute_weekly_mover, save_gauge_image,
    load_index, render_index, render_indicator_pages,
)


def refresh():
    coins = get_top_prices(MOVER_POOL)
    prices = coins[:TICKER_COINS]   # the Top 6 Market ticker (and everything else built on it) is unchanged
    fng = get_fear_greed()
    sectors = get_top_sectors()
    stablecoins = get_stablecoin_liquidity()
    dominance = get_btc_dominance()
    leverage = get_funding_and_oi()
    defi_tvl = get_defi_tvl()
    network_health = get_network_health()
    liquidations = get_recent_liquidations()
    whale_activity = get_large_transaction_amounts()
    macro = get_macro_data()
    ingest_narrative_momentum(sectors)  # at most one new day of history recorded per calendar day
    mover = compute_biggest_mover(coins)   # biggest 24h move among the top 10 coins
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
        "leverage": leverage,
        "defi_tvl": defi_tvl,
        "network_health": network_health,
        "liquidations": liquidations,
        "whale_activity": whale_activity,
        "macro": macro,
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
    # etf-flow.html and market-breadth.html are owned by their own decoupled
    # workflows - writing them here too would leave real, uncommitted
    # modifications in the working tree (their data only changes on their
    # own schedule, but the shared registry still regenerates their HTML
    # every run), which broke `git pull --rebase` in the commit step below
    # since it refuses to rebase over a dirty working tree.
    OTHER_WORKFLOWS_OWN = {"etf-flow.html", "market-breadth.html"}
    for filename, html in render_indicator_pages(entries).items():
        if filename in OTHER_WORKFLOWS_OWN:
            continue
        with open(os.path.join(ROOT, filename), "w") as f:
            f.write(html)

    print(f"Refreshed live indicators at {live['updated_at']} "
          f"(F&G {fng['value']} {fng['classification']}, "
          f"stablecoins ${stablecoins['total_usd']/1e9:.1f}B, "
          f"BTC dominance {dominance['btc_dominance_pct']:.1f}%, "
          f"funding rate {leverage['funding_rate_pct']:+.3f}%, "
          f"DeFi TVL ${defi_tvl['total_usd']/1e9:.1f}B, "
          f"hash rate {network_health['hashrate_eh']:.0f} EH/s, "
          f"liquidations ${(liquidations['long_liq_usd']+liquidations['short_liq_usd'])/1e6:.2f}M, "
          f"largest tx sampled {whale_activity['amounts_btc'][0] if whale_activity['amounts_btc'] else 0:.1f} BTC, "
          f"VIX {macro['vix']:.1f}, "
          f"{len(history)} history entries)")


if __name__ == "__main__":
    refresh()
