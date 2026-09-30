"""
refresh_market_breadth.py — refreshes the Market Breadth indicator on its
own schedule, separate from refresh_indicators.py's 15-minute cron. A
50/200-day SMA breadth reading only changes once a day at most (see
market_breadth_data.py) - this runs a few times a day so a missed run
doesn't delay picking up that day's snapshot, not because the number
itself moves faster than daily.

Prints a debug summary to the run's own log, same as refresh_etf_flow.py.
"""
import os

from market_breadth_data import ingest_and_store, compute_breadth
from build_site import ROOT, load_index, render_index, render_indicator_pages


def refresh():
    store = ingest_and_store()
    result = compute_breadth(store)

    if result is None:
        print("Market Breadth: no data available yet (first-ever run and CoinGecko returned nothing).")
        return

    two_hundred_d = f"{result['pct_above_200']}%" if result["have_200"] else f"building ({result['available_days']}d so far)"
    print(
        "Market Breadth debug summary\n"
        f"  Universe size:             {result['universe_size']} coins (locked at first ingest)\n"
        f"  Latest snapshot date:      {result['latest_date']}\n"
        f"  Days of history stored:    {result['available_days']}\n"
        f"  % above 50D SMA:           {result['pct_above_50']}% ({result['eligible_50']} eligible coins)"
        if result["have_50"] else
        f"  % above 50D SMA:           building ({result['available_days']}d so far, need 50)\n"
    )
    print(
        f"  % above 200D SMA:          {two_hundred_d}\n"
        f"  Label:                     {result['label']}\n"
    )

    # Only index.html and market-breadth.html can change from this refresh -
    # this script never touches pages the 15-minute refresh owns.
    entries = load_index()
    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(render_index(entries))
    pages = render_indicator_pages(entries)
    with open(os.path.join(ROOT, "market-breadth.html"), "w") as f:
        f.write(pages["market-breadth.html"])


if __name__ == "__main__":
    refresh()
