"""
refresh_etf_flow.py — refreshes the Bitcoin ETF Flow indicator on its own
schedule, separate from refresh_indicators.py's 15-minute cron. ETF flow
is a once-per-US-trading-day figure (see etf_data.py) - polling it every
15 minutes would be pointless and would burn through SoSoValue's rate
limit for no benefit, so this runs a few times a day instead (see
.github/workflows/refresh-etf-flow.yml).

Prints a debug summary to the run's own log (source status, validation
result, freshness) - this project has no admin surface/hidden routes, so
the GitHub Actions log is the natural place for that, same as every other
build script's existing print-based diagnostics.
"""
import os

from etf_data import ingest_and_store, compute_indicator
from build_site import ROOT, load_index, render_index, render_indicator_pages


def refresh():
    store = ingest_and_store()
    result = compute_indicator(store)

    if result is None:
        print("ETF Flow: no data available yet (first-ever run and SoSoValue returned nothing).")
        return

    thirty_d = f"${result['flow_30d_usd']:,.0f}" if result["have_30d"] else f"building ({result['available_days']}d so far)"
    print(
        "ETF Flow debug summary\n"
        f"  Primary source:            SoSoValue\n"
        f"  Primary latest ETF date:   {result['latest_date']}\n"
        f"  Primary latest total:      ${result['latest_flow_usd']:,.0f}\n"
        f"  7D / 30D cumulative:       ${result['flow_7d_usd']:,.0f} / {thirty_d}\n"
        f"  Streak:                    {result['streak_count']} trading days, {result['streak_direction']}\n"
        f"  Momentum:                  {result['momentum']}\n"
        f"  Pressure score:            {result['pressure_score']}/100\n"
        f"  Data freshness:            {result['freshness']} ({result['days_old']} days old)\n"
        f"  Secondary source:          XOOMAR (IBIT+BITB+ARKB subset only)\n"
        f"  Validation status:         {result['validation_status']}\n"
        f"  Validation difference:     {result['validation_difference_usd']} "
        f"({result['validation_difference_pct']})\n"
    )

    # Only index.html and etf-flow.html can actually change from this
    # refresh - render_indicator_pages() builds every indicator page, but
    # this script only writes the one this data affects, so it never
    # touches pages the 15-minute refresh (refresh_indicators.py) owns.
    entries = load_index()
    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(render_index(entries))
    pages = render_indicator_pages(entries)
    with open(os.path.join(ROOT, "etf-flow.html"), "w") as f:
        f.write(pages["etf-flow.html"])


if __name__ == "__main__":
    refresh()
