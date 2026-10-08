"""
build_site.py

Renders every page of the site (index, archive, and individual post pages)
from data/posts_index.json + the per-post JSON files in data/posts/.

This script is pure rendering — it does NOT call any AI or fetch any data.
generate_daily.py and generate_weekly.py call into this after they've
produced a new post's content.
"""
import json
import math
import os
import re
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw
from partials import page, asset_version
import home_v2
import indicator_v2
import post_v2
import seo

HEADER_WEB_VERSION = asset_version("header-web.png")
SECTION_MASCOT_VERSION = asset_version("mascot-color-section.png")
CAMO_VERSION = asset_version("camo-brand.png")
SNAPSHOT_BULL_VERSION = asset_version("mascots/bull.png")
SNAPSHOT_BEAR_VERSION = asset_version("mascots/bear.png")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
POSTS_DATA_DIR = os.path.join(DATA_DIR, "posts")
POSTS_HTML_DIR = os.path.join(ROOT, "posts")
GAUGES_DIR = os.path.join(ROOT, "assets", "gauges")
INDEX_FILE = os.path.join(DATA_DIR, "posts_index.json")
# Live indicator data (see refresh_indicators.py) - refreshed on its own
# schedule, completely independent of when a newsletter issue publishes.
LIVE_DATA_FILE = os.path.join(DATA_DIR, "live_indicators.json")
LIVE_HISTORY_FILE = os.path.join(DATA_DIR, "indicator_history.json")
MAX_HISTORY_ENTRIES = 500  # ~5 days at a 15-minute refresh interval

os.makedirs(POSTS_DATA_DIR, exist_ok=True)
os.makedirs(POSTS_HTML_DIR, exist_ok=True)
os.makedirs(GAUGES_DIR, exist_ok=True)

# House style for dates shown as "TOP NEWS: SEPT. 21, 2026" — shared by the
# website and the email so the two can never drift apart on this again.
MONTH_ABBREV = {
    1: "JAN.", 2: "FEB.", 3: "MAR.", 4: "APR.", 5: "MAY.", 6: "JUN.",
    7: "JUL.", 8: "AUG.", 9: "SEPT.", 10: "OCT.", 11: "NOV.", 12: "DEC.",
}


def format_date_abbrev(dt):
    return f"{MONTH_ABBREV[dt.month]} {dt.day}, {dt.year}"


def load_index():
    if not os.path.exists(INDEX_FILE):
        return []
    with open(INDEX_FILE) as f:
        return json.load(f)


def save_index(entries):
    with open(INDEX_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def compute_biggest_mover(prices):
    """Returns the price dict (symbol, change_24h, ...) with the largest absolute move."""
    return max(prices, key=lambda c: abs(c["change_24h"]))


def compute_weekly_mover(prices):
    """Same idea as compute_biggest_mover but ranked by 7-day change -
    used only for the website's homepage 'Biggest Mover of the Week' card,
    so that label matches a real rolling-7-day figure instead of reusing
    the 24h number. Kept separate from compute_biggest_mover/the shared
    'mover' field so the locked email template's data is untouched."""
    return max(prices, key=lambda c: abs(c.get("change_7d", 0)))


def save_gauge_image(value, slug):
    """Draws the Fear & Greed gauge as a real PNG and saves it to
    assets/gauges/<slug>.png. This ONE file is used by both the website and
    the email — no separate hand-coded copies to drift apart.

    Modern flat-design dial: a thin muted track, a smooth color gradient arc
    (rendered as many small slices rather than hard-edged bands) with rounded
    end caps, and a slim charcoal needle with a two-tone hub — rendered at 4x
    and downsampled for anti-aliased, crisp edges instead of the old chunky,
    jagged 5-band look. Returns the path fragment relative to the site root."""
    scale = 4
    w, h = 200 * scale, 120 * scale
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, int(h * 0.87)
    r_outer = int(w * 0.40)
    thickness = int(w * 0.05)
    bbox = [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer]

    # Muted background track for the full sweep.
    draw.arc(bbox, start=180, end=360, fill=(224, 219, 208, 255), width=thickness)

    # Smooth red -> orange -> yellow -> green -> dark-green gradient, drawn
    # as many thin overlapping slices instead of 5 hard-edged bands.
    anchors = [
        (0.00, (226, 76, 76)), (0.25, (235, 122, 60)), (0.50, (242, 201, 76)),
        (0.75, (143, 191, 92)), (1.00, (37, 107, 50)),
    ]

    def lerp_color(t):
        for (t0, c0), (t1, c1) in zip(anchors, anchors[1:]):
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0)
                return tuple(int(c0[i] + (c1[i] - c0[i]) * f) for i in range(3))
        return anchors[-1][1]

    steps = 180
    for i in range(steps):
        t_mid = (i + 0.5) / steps
        a0 = 180 + (i / steps) * 180
        a1 = 180 + ((i + 1) / steps) * 180 + 0.6  # tiny overlap avoids seams
        draw.arc(bbox, start=a0, end=a1, fill=lerp_color(t_mid) + (255,), width=thickness)

    # Rounded end caps so the arc reads as a smooth pill, not a hard cutoff.
    cap_r = thickness / 2
    for ang, color in ((180, anchors[0][1]), (360, anchors[-1][1])):
        rad = math.radians(ang)
        px = cx + (r_outer - thickness / 2) * math.cos(rad)
        py = cy + (r_outer - thickness / 2) * math.sin(rad)
        draw.ellipse([px - cap_r, py - cap_r, px + cap_r, py + cap_r], fill=color + (255,))

    # Slim charcoal needle with a two-tone brass/charcoal hub.
    angle_deg = 180 + (value / 100) * 180
    angle_rad = math.radians(angle_deg)
    needle_len = r_outer - thickness * 1.4
    nx = cx + needle_len * math.cos(angle_rad)
    ny = cy + needle_len * math.sin(angle_rad)
    draw.line([(cx, cy), (nx, ny)], fill="#171512", width=max(2, w // 90))
    tip_r = max(2, w // 130)
    draw.ellipse([nx - tip_r, ny - tip_r, nx + tip_r, ny + tip_r], fill="#171512")
    hub_r = max(4, w // 32)
    draw.ellipse([cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r], fill="#171512")
    hub_inner_r = hub_r * 0.45
    draw.ellipse([cx - hub_inner_r, cy - hub_inner_r, cx + hub_inner_r, cy + hub_inner_r], fill="#C9974F")

    # The dial (cy near the bottom of the canvas) leaves a much bigger empty
    # margin above it than below — fine for the drawing itself, but it means
    # the visible arc isn't vertically centered in its own frame, so an
    # email/site table cell centering the *image box* still shows the arc
    # sitting low. Recenter the drawn content within the same canvas size
    # (a shift, not a resize) so the visible gauge lines up with vertically
    # centered neighbors like the mover arrow icon.
    content_bbox = img.getbbox()
    if content_bbox:
        top_margin, bottom_margin = content_bbox[1], h - content_bbox[3]
        shift = (top_margin - bottom_margin) // 2
        if shift:
            centered = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            centered.paste(img, (0, -shift), img)
            img = centered

    img = img.resize((200, 120), Image.LANCZOS)
    out_path = os.path.join(GAUGES_DIR, f"{slug}.png")
    img.save(out_path)
    return f"assets/gauges/{slug}.png"


def _fng_color(value):
    if value <= 45:
        return "#E24C4C"
    if value >= 55:
        return "#256B32"
    return "#8A7F5C"


def render_masthead():
    # header-web.png is a website-only edit of the email's header-a.png with
    # the candlestick chart decoration painted out of the corners (user
    # request) - header-a.png itself is left untouched since it's also the
    # shared, already-locked email masthead image.
    return '<img class="post-masthead" src="{root}assets/header-web.png?v=' + HEADER_WEB_VERSION + '" alt="The Crypto Playback">'


def render_ticker_bar(prices, date_abbrev):
    """The full 'Header B' bar: Top 6 Market tab (arrow pointing into a
    centered, evenly-spaced price grid, caption underneath the tab), the
    TOP NEWS date pill, and a subscribe/share row. Matches the approved
    email design exactly — same visual language, website's own CSS classes."""
    row1 = prices[:3]
    row2 = prices[3:]

    def chip(c):
        arrow_color = "#8FBF5C" if c["change_24h"] >= 0 else "#E8837A"
        return (f'<span class="price-chip">{c["symbol"]} ${c["price"]:,.2f} '
                f'<span style="color:{arrow_color};">({c["change_24h"]:+.1f}%)</span></span>')

    prices_html = (
        f'<div class="price-row">{"".join(chip(c) for c in row1)}</div>'
        f'<div class="price-row" style="margin-top:9px;">{"".join(chip(c) for c in row2)}</div>'
    )

    return f"""<div class="ticker-bar">
    <div class="ticker-top5-col">
      <div class="ticker-tab-wrap">
        <span class="ticker-tab">Top 6 Market</span>
        <span class="ticker-arrow"></span>
      </div>
      <span class="ticker-caption">prices as of 6AM (cst)<br>on printed date</span>
    </div>
    <div class="ticker-prices">{prices_html}</div>
  </div>
  <div class="ticker-news-pill">
    <span>TOP NEWS: <em style="color:#F2C94C;">{date_abbrev}</em></span>
  </div>
  <div class="ticker-subscribe-row">
    <span class="ticker-share-prompt">Enjoying this? Share it with a friend &rarr;</span>
    <a class="ticker-subscribe-text" href="https://cryptoplayback.com/#subscribe" style="text-decoration:none;">SUBSCRIBE HERE</a>
    <a class="ticker-icon" href="#" style="background:#B5702E;" aria-label="Email">&#9993;</a>
    <a class="ticker-icon" href="https://x.com/cryptoplayback" style="background:#4A90D9;" aria-label="X">X</a>
  </div>"""


def render_sentiment_combined(fng, mover, tag):
    """The single combined box (Fear & Greed + Biggest Mover on one line,
    separated by a divider) inside a light-grey band. Needs gauge_path and
    root_prefix filled in by the caller since the gauge image path depends
    on where the page lives on the site."""
    fng_color = _fng_color(fng["value"])
    mover_up = mover["change_24h"] >= 0
    mover_color = "#256B32" if mover_up else "#E24C4C"
    mover_sign = "+" if mover_up else ""
    mover_label = "BIGGEST MOVER TODAY" if tag == "Daily" else "BIGGEST MOVER OF THE WEEK"
    icon_path = (
        '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>' if mover_up
        else '<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>'
    )

    return f"""<div class="sentiment-band">
    <div class="sentiment-box" style="border-color:#3A362F;">
      <img class="sentiment-gauge" src="{{gauge_src}}" alt="Fear and Greed gauge">
      <span class="sentiment-label" style="color:#975F25;">FEAR &amp; GREED</span>
      <span class="sentiment-value" style="color:{fng_color};">{fng['value']}</span>
      <span class="sentiment-word" style="color:{fng_color};">{fng['classification']}</span>
      <span class="sentiment-divider"></span>
      <svg class="sentiment-mover-icon" viewBox="0 0 24 24" fill="none" stroke="{mover_color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">{icon_path}</svg>
      <span class="sentiment-label" style="color:#975F25;">{mover_label}</span>
      <span class="sentiment-value" style="color:{mover_color};">{mover['symbol']}</span>
      <span class="sentiment-word-bold" style="color:{mover_color};">{mover_sign}{mover['change_24h']:.1f}%</span>
    </div>
  </div>"""


def render_issue_pill(tag):
    label = "DAILY ISSUE" if tag == "Daily" else "WEEKLY ISSUE"
    return f'<span class="issue-pill">{label}</span>'


def render_top_story_box(intro):
    return f"""<div class="top-story">
    <span class="top-story-tab">TOP STORY</span>
    <p class="top-story-text">{intro}</p>
  </div>"""


def render_post_html(post, root_prefix):
    """The Version 2 issue page for one saved post (see post_v2.py)."""
    return post_v2.render(post, root_prefix, _market_data_from_post(post), load_index(), _footer_indicator_links())


def rebuild_post_pages():
    """Re-render every issue page from data/posts/*.json so prev/next links and the stylesheet
    version stay current. Entries without a saved JSON file are left alone."""
    n = 0
    for e in load_index():
        path = os.path.join(POSTS_DATA_DIR, f"{e['slug']}.json")
        try:
            post = json.load(open(path))
        except (OSError, ValueError):
            continue
        with open(os.path.join(POSTS_HTML_DIR, f"{e['slug']}.html"), "w") as f:
            f.write(render_post_html(post, "../"))
        n += 1
    return n


def _market_data_from_post(post):
    """Raw {prices, fng, mover} for the homepage market-pulse section.

    Posts generated from here on save these fields directly (see
    generate_issue.py). Older posts only ever saved the pre-rendered
    ticker_html/sentiment_html strings, not the numbers behind them, so this
    falls back to pulling the real values back out of that saved HTML with a
    few regexes - nothing here is invented, it's just recovering numbers
    that were always there, formatted differently."""
    if "prices" in post and "fng" in post and "mover" in post:
        return post["prices"], post["fng"], post["mover"]

    prices = [
        {"symbol": sym, "price": float(price.replace(",", "")), "change_24h": float(pct)}
        for sym, price, pct in re.findall(
            r'class="price-chip">(\w+) \$([\d,]+\.\d+) <span[^>]*>\(([+-]?[\d.]+)%\)',
            post.get("ticker_html", ""),
        )
    ]
    values = re.findall(r'class="sentiment-value"[^>]*>([^<]+)<', post.get("sentiment_html", ""))
    words = re.findall(r'class="sentiment-word[^"]*"[^>]*>([^<]+)<', post.get("sentiment_html", ""))
    fng = {"value": int(values[0]), "classification": words[0]} if values and words else {"value": 0, "classification": "Unknown"}
    if len(values) > 1 and len(words) > 1:
        mover = {"symbol": values[1], "change_24h": float(words[1].replace("%", "").replace("+", ""))}
    else:
        mover = {"symbol": "-", "change_24h": 0}
    return prices, fng, mover


def _live_mover_display(mover):
    """Wraps the 24h biggest-mover reading for display - shared by the
    Alerts & Indicators card, Signal Confluence, What Changed, and the
    indicator page so they can never show different numbers for the same
    thing. The live dashboard refreshes independently of the newsletter
    now (see refresh_indicators.py), so there's no Daily/Weekly "tag" to
    switch framing on anymore - always a 24h reading."""
    return {
        "symbol": mover["symbol"],
        "change": mover["change_24h"],
        "label": "BIGGEST MOVER (24H)",
        "caption": "Top 10 coins by market cap, ranked by size of move",
        "period": "the last 24 hours",
    }


def load_indicator_history():
    """Rolling log written by refresh_indicators.py, oldest first, capped
    at MAX_HISTORY_ENTRIES. Used for each indicator page's Recent Readings
    and for finding a real ~24h-ago snapshot to diff against in What
    Changed. Returns [] if the refresh workflow hasn't run yet."""
    try:
        with open(LIVE_HISTORY_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def _find_comparison_snapshot(history, hours_ago=24):
    """The history entry closest to `hours_ago` before the latest one, for
    a real "what changed since about a day ago" diff. Falls back to the
    oldest entry available while the history is still younger than that
    (e.g. the first day after the refresh workflow goes live) rather than
    reporting nothing at all."""
    if len(history) < 2:
        return None
    latest_ts = datetime.fromisoformat(history[-1]["updated_at"])
    target = latest_ts - timedelta(hours=hours_ago)
    best, best_diff = None, None
    for row in history[:-1]:
        ts = datetime.fromisoformat(row["updated_at"])
        diff = abs((ts - target).total_seconds())
        if best_diff is None or diff < best_diff:
            best, best_diff = row, diff
    return best


def _load_dashboard_data(entries):
    """Everything the homepage's live indicator sections need - Market
    Snapshot, Signal Confluence, What Changed, Alerts & Indicators, and
    each indicator's own page. Sourced from data/live_indicators.json,
    refreshed independently of the newsletter by refresh_indicators.py on
    its own schedule (.github/workflows/refresh-indicators.yml) - not tied
    to when a newsletter issue publishes.

    Falls back to the latest published post's saved snapshot only if that
    file doesn't exist yet (e.g. before the refresh workflow has ever run,
    or on a fresh checkout) - the site should never break just because a
    scheduled job hasn't fired."""
    try:
        with open(LIVE_DATA_FILE) as f:
            live = json.load(f)
        if live.get("prices"):
            # "dominance" is a newer field - a live_indicators.json written by an
            # older refresh_indicators.py (before its next scheduled run) won't
            # have it yet, so backfill a harmless placeholder rather than KeyError.
            live.setdefault("dominance", {"btc_dominance_pct": 55.0, "total_market_cap_usd": 2.5e12})
            live.setdefault("leverage", {"funding_rate_pct": 0.01, "next_funding_time_ms": 0, "open_interest_usd": 2.5e9})
            live.setdefault("defi_tvl", {"total_usd": 95e9, "change_7d_pct": 0.0})
            live.setdefault("network_health", {"hashrate_eh": 950.0, "difficulty_change_pct": 0.0,
                                                "fastest_fee_satvb": 5, "pending_tx_count": 10000})
            live.setdefault("liquidations", {"long_liq_usd": 0.0, "short_liq_usd": 0.0,
                                              "event_count": 0, "window_minutes": 0.0})
            live.setdefault("whale_activity", {"amounts_btc": [], "sample_size": 0})
            live.setdefault("macro", {"vix": 16.0, "vix_change_pct": 0.0, "dxy": 100.0, "dxy_change_pct": 0.0})
            return live
    except (OSError, json.JSONDecodeError):
        pass

    if not entries:
        return None
    latest_slug = entries[0]["slug"]
    try:
        with open(os.path.join(POSTS_DATA_DIR, f"{latest_slug}.json")) as f:
            latest_full = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    prices, fng, mover = _market_data_from_post(latest_full)
    if not prices:
        return None
    if len(prices) < 6:
        # Predates the Top-6 change - pad so the design still reviews as a
        # real 6-wide grid. Not a real price; gone the moment a refresh runs.
        prices = prices + [{"symbol": "DOGE", "price": 0.18, "change_24h": 3.4}]
    sectors = latest_full.get("sectors") or [
        {"label": "RWA", "change_24h": 12.4},
        {"label": "AI", "change_24h": 8.7},
        {"label": "DeFi", "change_24h": 5.2},
    ]
    stablecoins = latest_full.get("stablecoins") or {"total_usd": 312400000000, "change_7d_pct": 1.8}
    dominance = latest_full.get("dominance") or {"btc_dominance_pct": 55.0, "total_market_cap_usd": 2.5e12}
    leverage = latest_full.get("leverage") or {"funding_rate_pct": 0.01, "next_funding_time_ms": 0, "open_interest_usd": 2.5e9}
    defi_tvl = latest_full.get("defi_tvl") or {"total_usd": 95e9, "change_7d_pct": 0.0}
    network_health = latest_full.get("network_health") or {"hashrate_eh": 950.0, "difficulty_change_pct": 0.0,
                                                             "fastest_fee_satvb": 5, "pending_tx_count": 10000}
    liquidations = latest_full.get("liquidations") or {"long_liq_usd": 0.0, "short_liq_usd": 0.0,
                                                         "event_count": 0, "window_minutes": 0.0}
    whale_activity = latest_full.get("whale_activity") or {"amounts_btc": [], "sample_size": 0}
    macro = latest_full.get("macro") or {"vix": 16.0, "vix_change_pct": 0.0, "dxy": 100.0, "dxy_change_pct": 0.0}
    return {
        "updated_at": None,
        "prices": prices,
        "fng": fng,
        "mover": mover,
        "sectors": sectors,
        "stablecoins": stablecoins,
        "dominance": dominance,
        "leverage": leverage,
        "defi_tvl": defi_tvl,
        "network_health": network_health,
        "liquidations": liquidations,
        "whale_activity": whale_activity,
        "macro": macro,
        "gauge_path": latest_full.get("gauge_path", ""),
    }


def _format_live_updated(updated_at_iso, fallback_display):
    """'Sept. 29, 2026 - 2:45 PM UTC' from the live refresh timestamp, or
    the post's own date_display if there's no live timestamp yet (the
    fallback-to-latest-post path in _load_dashboard_data)."""
    if not updated_at_iso:
        return fallback_display
    dt = datetime.fromisoformat(updated_at_iso)
    return f"{format_date_abbrev(dt)} &middot; {dt.strftime('%-I:%M %p')} UTC"


def _format_date_only(date_str):
    """'Sept. 30, 2026' from a plain 'YYYY-MM-DD' string - used for the
    handful of indicators (ETF Flow, Market Breadth, Narrative Momentum)
    whose own data only carries a date, not a time of day, so showing a
    time for them would fabricate precision the data doesn't have."""
    return format_date_abbrev(datetime.strptime(date_str, "%Y-%m-%d"))


def _load_etf_dashboard():
    """The Bitcoin ETF Flow indicator, computed from data/etf_flows.json
    (see etf_data.py) - refreshed on its own low-frequency schedule
    (refresh_etf_flow.py / .github/workflows/refresh-etf-flow.yml), since
    it's a once-per-trading-day figure, not something that needs the
    15-minute cadence the other live indicators use. Returns None before
    the first successful ingest, or if etf_data.py isn't importable for
    any reason - callers render an honest "awaiting data" state in that
    case rather than a fabricated number."""
    try:
        from etf_data import load_store, compute_indicator
        return compute_indicator(load_store())
    except Exception:
        return None


def _load_market_breadth_dashboard():
    """The Market Breadth indicator (% of a locked 40-coin universe above
    its own 50/200-day SMA), computed from data/market_breadth.json (see
    market_breadth_data.py) - refreshed a few times a day by its own
    workflow, same reasoning as _load_etf_dashboard() above: a moving-average
    breadth reading only changes once a day at most."""
    try:
        from market_breadth_data import load_store, compute_breadth
        return compute_breadth(load_store())
    except Exception:
        return None


def _load_narrative_momentum_dashboard():
    """The Narrative Momentum indicator (sectors ranked by trailing 7-day
    average daily change, not today's snapshot) - computed from
    data/narrative_momentum.json (see narrative_momentum_data.py), which
    refresh_indicators.py appends to once per day using the same sector
    data it already fetches every 15 minutes."""
    try:
        from narrative_momentum_data import load_store, compute_momentum
        return compute_momentum(load_store())
    except Exception:
        return None


def _compute_derived_signals(prices, fng, sectors):
    """Risk Radar and Capital Flow, computed here instead of hardcoded.

    Both used to be fixed placeholder values (risk_level="low" and
    inst_flow_score=72 every single time, regardless of the real market).
    These are deterministic, documented calculations built only from data
    we already fetch for real (CoinGecko prices/sectors, Alternative.me
    Fear & Greed) - no external "risk" or "institutional flow" API, and the
    exact formula is spelled out on each indicator's own page so the label
    never claims more than the math behind it actually measures.
    """
    sectors = sectors or []
    avg_abs_change = (sum(abs(c["change_24h"]) for c in prices) / len(prices)) if prices else 0.0

    risk_score = 0
    if fng["value"] >= 80 or fng["value"] <= 20:
        risk_score += 2
    elif fng["value"] >= 70 or fng["value"] <= 30:
        risk_score += 1
    if avg_abs_change >= 8:
        risk_score += 2
    elif avg_abs_change >= 4:
        risk_score += 1
    risk_level = "elevated" if risk_score >= 4 else ("moderate" if risk_score >= 2 else "low")

    breadth_pool = prices + sectors
    positive = sum(1 for x in breadth_pool if x["change_24h"] >= 0)
    breadth_pct = (positive / len(breadth_pool)) if breadth_pool else 0.5
    capital_flow_score = max(0, min(100, round(0.6 * breadth_pct * 100 + 0.4 * fng["value"])))
    if capital_flow_score >= 60:
        capital_flow_signal = "Accumulation"
    elif capital_flow_score >= 40:
        capital_flow_signal = "Mixed"
    else:
        capital_flow_signal = "Distribution"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "avg_abs_change": avg_abs_change,
        "breadth_pct": breadth_pct,
        "breadth_positive": positive,
        "breadth_total": len(breadth_pool),
        "capital_flow_score": capital_flow_score,
        "capital_flow_signal": capital_flow_signal,
    }


# The one green and one red used across every live indicator's "positive"/
# "negative" reading - defined once here so a future indicator can't
# introduce a slightly-different shade (this is exactly how DeFi Pulse's
# shrinking color ended up as a different red, #E8837A, than Liquidations'
# #E24C4C, before this constant existed). Amber (#F2C94C) for a middle
# "neutral/moderate" state isn't a red/green question, so it stays
# hardcoded per indicator rather than living here.
INDICATOR_GREEN = "#8FBF5C"
INDICATOR_RED = "#E24C4C"


def _stablecoin_signal(stablecoins):
    """'Expanding'/'Contracting' from real DefiLlama data (fetch_stablecoins.py)
    - dry powder entering or leaving the crypto ecosystem, not a price
    call. Positive 7-day change reads Expanding, negative reads
    Contracting; there's no 'flat' band since even a hair of real
    movement is a real, if small, directional data point."""
    expanding = stablecoins["change_7d_pct"] >= 0
    return {
        "expanding": expanding,
        "signal": "Expanding" if expanding else "Contracting",
        "color": INDICATOR_GREEN if expanding else INDICATOR_RED,
    }


def _defi_tvl_signal(defi_tvl):
    """'Growing'/'Shrinking' from real DefiLlama TVL data (fetch_defi_tvl.py)
    - a different metric than Stablecoin Liquidity's dry-powder read: TVL is
    capital actually deployed/locked into DeFi protocols, and moves with the
    price of what's locked (a broad crypto rally can lift TVL even with zero
    net new deposits), not purely a fresh-capital signal."""
    growing = defi_tvl["change_7d_pct"] >= 0
    return {
        "growing": growing,
        "signal": "Growing" if growing else "Shrinking",
        "color": INDICATOR_GREEN if growing else INDICATOR_RED,
    }


NETWORK_HEALTH_THRESHOLD = 5.0  # % estimated change at the next difficulty retarget


def _network_health_signal(network_health):
    """'Hash Rate Rising'/'Stable'/'Hash Rate Falling' from the Bitcoin
    network's own next-difficulty-retarget estimate (mempool.space) - a
    real, forward-looking figure computed directly from actual observed
    block times since the last retarget, not a derived guess. Rising hash
    rate means more mining power is actively securing the network."""
    change = network_health["difficulty_change_pct"]
    if change >= NETWORK_HEALTH_THRESHOLD:
        label = "Hash Rate Rising"
    elif change <= -NETWORK_HEALTH_THRESHOLD:
        label = "Hash Rate Falling"
    else:
        label = "Stable"
    return {
        "label": label,
        "positive": change >= 0,
        "color": INDICATOR_GREEN if change >= 0 else INDICATOR_RED,
    }


LIQUIDATION_DOMINANCE_THRESHOLD = 0.65  # share of total liquidated USD on one side


def _liquidation_signal(liquidations):
    """'Long/Short Liquidations Dominant' vs 'Balanced'/'Quiet' from OKX's
    most recent ~100 BTC perpetual liquidation events (fetch_liquidations.py).
    Heavy liquidations in EITHER direction represent forced, cascading
    market action (long-dominant: a hard drop; short-dominant: a short
    squeeze) - same "either direction is the risk state" convention as
    Leverage Heat, not a directional call."""
    total = liquidations["long_liq_usd"] + liquidations["short_liq_usd"]
    if total <= 0:
        return {"label": "Quiet", "positive": True, "color": INDICATOR_GREEN}
    long_share = liquidations["long_liq_usd"] / total
    if long_share >= LIQUIDATION_DOMINANCE_THRESHOLD:
        return {"label": "Long Liquidations Dominant", "positive": False, "color": INDICATOR_RED}
    if long_share <= (1 - LIQUIDATION_DOMINANCE_THRESHOLD):
        return {"label": "Short Liquidations Dominant", "positive": False, "color": INDICATOR_RED}
    return {"label": "Balanced", "positive": True, "color": INDICATOR_GREEN}


WHALE_THRESHOLD_USD = 1_000_000  # standard "whale transaction" floor


def _whale_signal(whale_activity, prices):
    """Counts how many of the sampled mempool transactions moved >=$1M in
    BTC, using the current BTC price to convert the raw BTC amounts
    fetch_whale_activity.py returns. Deliberately has no positive/negative
    read (confluence_positive is always None, excluded from Signal
    Confluence) - a large transfer's total output value doesn't tell us
    whether it's accumulation, distribution, or just an exchange moving
    coins between its own wallets, so scoring it either way would be a
    fabricated directional call."""
    btc_entry = next((p for p in prices if p["symbol"] == "BTC"), None)
    btc_price = btc_entry["price"] if btc_entry else 0
    whale_amounts = [a for a in whale_activity["amounts_btc"] if a * btc_price >= WHALE_THRESHOLD_USD]
    whale_count = len(whale_amounts)
    whale_total_usd = sum(a * btc_price for a in whale_amounts)

    if whale_count == 0:
        label = "Quiet"
    elif whale_count < 5:
        label = "Active"
    else:
        label = "Elevated"

    return {
        "label": label,
        "positive": None,
        "color": "#8A7F5C",
        "whale_count": whale_count,
        "whale_total_usd": whale_total_usd,
    }


def _macro_risk_signal(macro):
    """Low/Moderate/Elevated from traditional-markets conditions - VIX
    (equity volatility/fear) and the US Dollar Index's daily move - same
    points-based scoring style as Risk Radar, but reading macro conditions
    instead of crypto's own volatility/sentiment. VIX >=30 (equities'
    classic "high fear" threshold) adds 2 points, >=20 (above its
    long-run average) adds 1. A dollar move of >=0.5% in a single day
    (large for an index this size) adds 1 point, in either direction,
    since a sharp FX move either way reflects macro turbulence."""
    score = 0
    if macro["vix"] >= 30:
        score += 2
    elif macro["vix"] >= 20:
        score += 1
    if abs(macro["dxy_change_pct"]) >= 0.5:
        score += 1

    level = "elevated" if score >= 3 else ("moderate" if score >= 1 else "low")
    return {
        "level": level,
        "score": score,
        "positive": level == "low",
    }


DOMINANCE_ROTATION_THRESHOLD = 3.0  # percentage points of 24h-change gap between BTC and the alt average


def _dominance_signal(prices, dominance):
    """Altcoin Rotation / BTC Dominance's signal: not a history lookback,
    just BTC's own 24h price change vs. the average 24h change of the
    other tracked coins - reusing data this refresh already fetched, so
    the reading is real from the very first run instead of waiting on
    accumulated history like ETF Flow or Market Breadth need to.

    A positive gap (alts up more than BTC over the same 24 hours) reads
    as alts gaining ground; a negative gap reads as BTC gaining ground.
    +-3 percentage points is the threshold for calling it a real gap
    rather than ordinary day-to-day noise between two return series."""
    btc = next((p for p in prices if p["symbol"] == "BTC"), None)
    alts = [p for p in prices if p is not btc]
    if btc is None or not alts:
        return {"gap": None, "label": "Insufficient Data", "positive": None}

    alt_avg_change = sum(a["change_24h"] for a in alts) / len(alts)
    gap = alt_avg_change - btc["change_24h"]
    if gap >= DOMINANCE_ROTATION_THRESHOLD:
        label, positive = "Alts Outperforming", True
    elif gap <= -DOMINANCE_ROTATION_THRESHOLD:
        label, positive = "BTC Outperforming", False
    else:
        # A genuinely neutral read shouldn't force a green or red Signal
        # Confluence dot - "In Line" sits out of confluence entirely, same
        # as an indicator still awaiting its first real data.
        label, positive = "In Line", None
    return {"gap": gap, "label": label, "positive": positive}


LEVERAGE_ELEVATED_THRESHOLD = 0.01  # % per funding period
LEVERAGE_EXTREME_THRESHOLD = 0.05   # % per funding period


def _leverage_signal(leverage):
    """BTC perpetual futures funding rate -> a plain-language crowding
    label. Positive funding means longs are paying shorts (long side more
    crowded with leverage); negative means the reverse. Thresholds are
    symmetric and based on typical historical funding ranges - OKX's own
    "normal" range hovers near +-0.01%/period, with +-0.05%+ historically
    coinciding with crowded, liquidation-prone positioning.

    Unlike Risk Radar (low risk = positive), "positive" here specifically
    means balanced/uncrowded leverage - elevated leverage in EITHER
    direction raises liquidation-cascade risk, so both directions read as
    the non-positive state, not just the "short" side."""
    rate = leverage["funding_rate_pct"]
    if rate >= LEVERAGE_EXTREME_THRESHOLD:
        return {"label": "Extreme Long Leverage", "positive": False}
    if rate >= LEVERAGE_ELEVATED_THRESHOLD:
        return {"label": "Elevated Long Leverage", "positive": False}
    if rate <= -LEVERAGE_EXTREME_THRESHOLD:
        return {"label": "Extreme Short Leverage", "positive": False}
    if rate <= -LEVERAGE_ELEVATED_THRESHOLD:
        return {"label": "Elevated Short Leverage", "positive": False}
    return {"label": "Balanced", "positive": True}


def _etf_pressure_label(pressure_score, flow_m):
    """Documented, symmetric mapping from the 0-100 pressure score (see
    etf_data.py) to a plain-language label - deliberately never says
    "buy"/"sell"/"bullish"/"bearish", only describes the flow itself."""
    direction = "Inflow" if flow_m >= 0 else "Outflow"
    if pressure_score >= 75 or pressure_score <= 25:
        return f"Strong {direction}"
    if pressure_score >= 55 or pressure_score <= 45:
        return direction
    return "Neutral"


# ============================================================================
# Shared indicator-visual renderers
#
# Every indicator's "current value" is one of a small number of visual
# shapes (a big colored number + word, a colored badge, a symbol + signed
# percent, or a list of rows) - and each shape needs to render twice: once
# small for its Alerts & Indicators card, once large for its own page's
# hero. Before this, those two renderings were hand-typed separately for
# every indicator (14 near-identical f-strings for 7 indicators), so a
# future layout change would mean finding and editing every one of them
# individually, and the card/hero versions could quietly drift apart.
#
# These four functions are the ONLY place that HTML shape is defined. A
# future redesign that changes what a "big value" or a "badge" looks like
# is a change in ONE function, not a hunt through render_index() and
# render_indicator_pages(). `context` ("card" or "hero") only ever
# switches which CSS class prefix is used - the class names themselves
# (and therefore the actual visual design) still live entirely in
# assets/styles.css, untouched by this file.
# ============================================================================

def _value_visual(value, word, color, context, prefix_html="", stacked=False):
    """Big colored number + smaller word next to it - Fear & Greed,
    Capital Flow, Stablecoin Liquidity, and ETF Flow all use this shape.
    `prefix_html` is for anything that goes before the number itself,
    e.g. Fear & Greed's gauge image. `stacked=True` (Liquidations' long
    "Long/Short Liquidations Dominant" word) centers the word under the
    value instead of wrapping it awkwardly beside it - the side-by-side
    layout only reads cleanly for a single short word."""
    value_class = "pulse-card-value" if context == "card" else "indicator-value"
    word_class = "pulse-card-word" if context == "card" else "indicator-value-word"
    if stacked:
        value_class += " stacked-value"
    return (f'{prefix_html}<div class="{value_class}" style="color:{color};">{value}'
            f'<span class="{word_class}">{word}</span></div>')


def _badge_visual(text, badge_class, context):
    """A single colored pill - Risk Radar's LOW/MODERATE/ELEVATED, and the
    "AWAITING DATA" placeholder state any indicator can show before its
    first real reading exists."""
    extra = " indicator-risk-badge" if context == "hero" else ""
    return f'<span class="pulse-risk-badge {badge_class}{extra}">{text}</span>'


def _mover_visual(symbol, change, context):
    """Symbol + signed percent, side by side - Biggest Mover's shape."""
    color = INDICATOR_GREEN if change >= 0 else INDICATOR_RED
    sign = "+" if change >= 0 else ""
    if context == "card":
        return (f'<span class="pulse-mover-symbol">{symbol}</span>'
                f'<span class="pulse-mover-change" style="color:{color};">{sign}{change:.1f}%</span>')
    return (f'<div class="indicator-value"><span class="indicator-mover-symbol">{symbol}</span>'
            f'<span style="color:{color};">{sign}{change:.1f}%</span></div>')


def _sector_list_visual(sectors, context):
    """A short list of name/change rows - Top Sectors' shape."""
    rows = "".join(
        f'<div class="pulse-sector-row"><span class="pulse-sector-name">{s["label"]}</span>'
        f'<span class="pulse-sector-change" style="color:{INDICATOR_GREEN if s["change_24h"] >= 0 else INDICATOR_RED};">'
        f'{s["change_24h"]:+.1f}%</span></div>'
        for s in sectors
    )
    extra_class = " indicator-sector-list" if context == "hero" else ""
    return f'<div class="pulse-sector-list{extra_class}">{rows}</div>'


def _build_indicator_registry(dashboard, gauge_src):
    """The single source of truth for every real indicator - one list,
    built once, consumed four ways (Alerts & Indicators cards, Signal
    Confluence rows, Decode The Dashboard cards, and each indicator's own
    page). Before this, the same 7 indicators were defined independently
    in four separate places across render_index() and
    render_indicator_pages(), which both had to independently reload and
    recompute the live dashboard/signals/ETF data too - real drift risk
    if any one of those four spots was ever updated without the others.
    Now render_index() and render_indicator_pages() both just call this
    and loop over the result.

    Each entry is a plain dict - no indicator-specific classes or
    inheritance, just data - so adding an 8th/9th/10th indicator later
    means appending one more dict here, not touching four render
    functions. A future layout redesign changes assets/styles.css and, at
    most, the small shared _*_visual() renderers above; it never needs to
    touch this function or the indicator-specific text below."""
    prices = dashboard["prices"]
    fng = dashboard["fng"]
    mover = dashboard["mover"]
    sectors = dashboard["sectors"]
    stablecoins = dashboard["stablecoins"]
    dominance = dashboard["dominance"]
    leverage = dashboard["leverage"]
    defi_tvl = dashboard["defi_tvl"]
    network_health = dashboard["network_health"]
    liquidations = dashboard["liquidations"]
    whale_activity = dashboard["whale_activity"]
    macro = dashboard["macro"]
    signals = _compute_derived_signals(prices, fng, sectors)
    resolved_mover = _live_mover_display(mover)
    stable_signal = _stablecoin_signal(stablecoins)
    rotation = _dominance_signal(prices, dominance)
    lev_signal = _leverage_signal(leverage)
    defi_signal = _defi_tvl_signal(defi_tvl)
    net_signal = _network_health_signal(network_health)
    liq_signal = _liquidation_signal(liquidations)
    whale_signal = _whale_signal(whale_activity, prices)
    macro_signal = _macro_risk_signal(macro)
    etf = _load_etf_dashboard()
    breadth = _load_market_breadth_dashboard()
    narrative = _load_narrative_momentum_dashboard()

    fng_color = INDICATOR_RED if fng["value"] <= 45 else (INDICATOR_GREEN if fng["value"] >= 55 else "#8A7F5C")
    flow_color = {"accumulation": INDICATOR_GREEN, "mixed": "#F2C94C", "distribution": INDICATOR_RED}.get(
        signals["capital_flow_signal"].lower(), "#8A7F5C"
    )
    rotation_color = {"Alts Outperforming": INDICATOR_GREEN, "BTC Outperforming": INDICATOR_RED}.get(rotation["label"], "#F2C94C")
    lev_color = INDICATOR_GREEN if lev_signal["label"] == "Balanced" else (
        INDICATOR_RED if "Extreme" in lev_signal["label"] else "#F2C94C")

    registry = [
        {
            "id": "fear_greed",
            "page": "fear-greed-index.html",
            "card_label": "Fear &amp; Greed Index",
            "card_main_html": _value_visual(
                fng["value"], fng["classification"], fng_color, "card",
                prefix_html=f'<img class="pulse-gauge" src="{gauge_src}" alt="Fear and Greed gauge">'),
            "card_caption": "Daily fear and greed sentiment indicator",
            "confluence_name": "Fear &amp; Greed",
            "confluence_positive": fng["value"] >= 55,
            "confluence_display": f"{fng['value']} {fng['classification']}",
            "explainer_icon": f'<img class="explainer-icon-img" src="{gauge_src}" alt="">',
            "explainer_text": (
                "A 0&ndash;100 read on overall market mood, from Extreme Fear to Extreme Greed. "
                "Calculated daily from real volatility, momentum, and social data, not opinion. "
                "Extremes often line up with emotional turning points, not rational ones."),
            "page_title": "Fear &amp; Greed Index",
            "page_hero_html": _value_visual(
                fng["value"], fng["classification"], fng_color, "hero",
                prefix_html=f'<img class="indicator-gauge" src="{gauge_src}" alt="Fear and Greed gauge">'),
            "page_sections": [
                ("What It Measures", "<p>Overall crypto market sentiment on a 0&ndash;100 scale, from Extreme "
                 "Fear to Extreme Greed.</p>"),
                ("How It's Calculated", "<p>Pulled directly from Alternative.me's Crypto Fear &amp; Greed "
                 "Index, which blends volatility, market momentum and volume, social media activity, market "
                 "dominance, and search trends into a single score. We don't calculate this ourselves &mdash; "
                 "we display their published reading as of each issue.</p>"),
                ("Why It Matters", "<p>Extreme readings often &mdash; not always &mdash; line up with "
                 "emotional turning points: extreme fear near local bottoms, extreme greed near local tops. "
                 "It's a sentiment gauge, not a price prediction.</p>"),
                ("Data Source &amp; Update Frequency", "<p>Alternative.me Crypto Fear &amp; Greed Index "
                 "(api.alternative.me/fng). Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: f"{row['fng']['value']} {row['fng']['classification']}",
        },
        {
            "id": "biggest_mover",
            "page": "biggest-mover.html",
            "card_label": resolved_mover["label"].title(),
            "card_main_html": _mover_visual(resolved_mover["symbol"], resolved_mover["change"], "card"),
            "card_caption": resolved_mover["caption"] or "Top 10 coins by market cap, ranked by size of move",
            "confluence_name": resolved_mover["label"].title(),
            "confluence_positive": resolved_mover["change"] >= 0,
            "confluence_display": f"{resolved_mover['symbol']} {resolved_mover['change']:+.1f}%",
            "explainer_icon": "&#128200;",
            "explainer_text": (
                "Whichever of the top 10 coins in the crypto market (by market cap, stablecoins excluded) "
                "moved the most \u2014 up or down \u2014 over the last 24 hours. "
                "Ranked purely by the size of the move, not its direction. "
                "A quick read on where the action is happening right now."),
            "page_title": resolved_mover["label"].title(),
            "page_hero_html": _mover_visual(resolved_mover["symbol"], resolved_mover["change"], "hero"),
            "page_sections": [
                ("What It Measures", "<p>Whichever of the top 10 coins in the crypto market (by market cap, "
                 "stablecoins excluded) moved the most &mdash; up or down &mdash; over the last 24 hours.</p>"),
                ("How It's Calculated", "<p>We take the 10 largest coins by market cap (stablecoins excluded), "
                 "rank them by the absolute size of their 24-hour price change, and surface the single biggest "
                 "mover, in either direction. The Top 6 Market ticker is a separate, smaller list.</p>"),
                ("Why It Matters", "<p>Highlights where the action is actually concentrated, instead of just "
                 "reporting that \"the market was up.\"</p>"),
                ("Data Source &amp; Update Frequency", "<p>CoinGecko public markets API. "
                 "Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: f"{row['mover']['symbol']} {row['mover']['change']:+.1f}%",
        },
        {
            "id": "risk_radar",
            "page": "risk-radar.html",
            "card_label": "&#9888;&#65039; Risk Radar",
            "card_main_html": _badge_visual(signals["risk_level"].upper(), f'pulse-risk-{signals["risk_level"]}', "card"),
            "card_caption": "Overall crypto market risk indicator",
            "confluence_name": "Risk Radar",
            "confluence_positive": signals["risk_level"] == "low",
            "confluence_display": signals["risk_level"].upper(),
            "explainer_icon": "&#9888;&#65039;",
            "explainer_text": (
                "A simple Low, Moderate, or Elevated snapshot of how turbulent the market is right now, "
                "built from volatility and sentiment extremes. "
                "It's a temperature check on current conditions, not a forecast of what happens next."),
            "page_title": "Risk Radar",
            "page_hero_html": _badge_visual(signals["risk_level"].upper(), f'pulse-risk-{signals["risk_level"]}', "hero"),
            "page_sections": [
                ("What It Measures", "<p>A simple read on how turbulent current market conditions are "
                 "&mdash; Low, Moderate, or Elevated.</p>"),
                ("How It's Calculated", "<p>A Crypto Playback score built from two real inputs: how extreme "
                 "the Fear &amp; Greed reading is, and the average size of the 24-hour price move across our "
                 "6 tracked coins. Extreme sentiment (Fear &amp; Greed &ge;80 or &le;20) adds 2 points, "
                 "borderline extreme (&ge;70 or &le;30) adds 1. Average 24h volatility &ge;8% adds 2 points, "
                 "&ge;4% adds 1. 0&ndash;1 points reads Low, 2&ndash;3 reads Moderate, 4+ reads Elevated.</p>"),
                ("Why It Matters", "<p>A temperature check on current conditions, not a forecast of what "
                 "happens next.</p>"),
                ("Data Source &amp; Update Frequency", "<p>Computed by The Crypto Playback from Alternative.me "
                 "and CoinGecko data &mdash; not pulled from any third-party \"risk\" API. "
                 "Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: row["risk_level"].upper(),
        },
        {
            "id": "capital_flow",
            "page": "capital-flow.html",
            "card_label": "&#128176; Capital Flow",
            "card_main_html": _value_visual(signals["capital_flow_score"], signals["capital_flow_signal"], flow_color, "card"),
            "card_caption": "Price &amp; sector breadth vs. sentiment",
            "confluence_name": "Capital Flow",
            "confluence_positive": signals["capital_flow_signal"] == "Accumulation",
            "confluence_display": f"{signals['capital_flow_score']} {signals['capital_flow_signal']}",
            "explainer_icon": "&#128176;",
            "explainer_text": (
                "A Crypto Playback composite score built from price and sector breadth weighted against "
                "sentiment &mdash; not institutional transaction data. A higher score leans toward "
                "accumulation, a lower score toward distribution."),
            "page_title": "Capital Flow",
            "page_hero_html": _value_visual(signals["capital_flow_score"], signals["capital_flow_signal"], flow_color, "hero"),
            "page_sections": [
                ("What It Measures", "<p>Whether price and sector breadth, weighted against sentiment, "
                 "currently lean toward accumulation or distribution.</p>"),
                ("How It's Calculated", "<p>60% weight on breadth (the share of our 6 tracked coins and "
                 "tracked sectors that are positive over 24 hours) plus 40% weight on the Fear &amp; Greed "
                 "value, scaled 0&ndash;100. A score of 60+ reads Accumulation, 40&ndash;59 reads Mixed, "
                 "below 40 reads Distribution.</p>"),
                ("An Honest Note On The Name", "<p>This is <strong>not</strong> built from ETF flows, "
                 "exchange order flow, or on-chain institutional transaction data &mdash; it's a composite of "
                 "price/sector breadth and sentiment.</p>"),
                ("Why It Matters", "<p>Distinguishes whether a move is broad-based across many assets, or "
                 "being carried by just a couple of large coins.</p>"),
                ("Data Source &amp; Update Frequency", "<p>Computed by The Crypto Playback from CoinGecko and "
                 "Alternative.me data. Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: f"{row['capital_flow_score']} {row['capital_flow_signal']}",
        },
        {
            "id": "top_sectors",
            "page": "top-sectors.html",
            "card_label": "&#128202; Top Sectors",
            "card_main_html": _sector_list_visual(sectors, "card"),
            "card_caption": "Best-performing sectors, 24H",
            "confluence_name": "Top Sectors",
            "confluence_positive": bool(sectors) and sum(1 for s in sectors if s["change_24h"] >= 0) > len(sectors) / 2,
            "confluence_display": (f"{sum(1 for s in sectors if s['change_24h'] >= 0)}/{len(sectors)} positive"
                                    if sectors else "&ndash;"),
            "explainer_icon": "&#128202;",
            "explainer_text": (
                "Ranks major crypto narratives, like AI, RWA, and DeFi, by 24-hour performance. Pulled from a "
                "curated list of major sectors so tiny micro-categories can't skew the results. "
                "Shows where money is rotating inside the market, not just up or down overall."),
            "page_title": "Top Sectors",
            "page_hero_html": _sector_list_visual(sectors, "hero"),
            "page_sections": [
                ("What It Measures", "<p>Which major crypto narrative categories &mdash; AI, RWA, DeFi, L1, "
                 "L2, Gaming, Memecoins, DePIN, NFT &mdash; are performing best over the last 24 hours.</p>"),
                ("How It's Calculated", "<p>Ranked by 24-hour market-cap change within a curated watchlist of "
                 "recognizable sectors, so a narrow, noisy micro-category can't crowd out the real "
                 "narratives.</p>"),
                ("Why It Matters", "<p>Shows where money is rotating within the market, not just whether the "
                 "market overall is up or down.</p>"),
                ("Data Source &amp; Update Frequency", "<p>CoinGecko categories API. "
                 "Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: (f"{row['sectors'][0]['label']} {row['sectors'][0]['change_24h']:+.1f}%"
                                               if row.get("sectors") else "&ndash;"),
        },
        {
            "id": "dominance_rotation",
            "page": "btc-dominance.html",
            "card_label": "&#129517; Altcoin Rotation",
            "card_main_html": _value_visual(f'{dominance["btc_dominance_pct"]:.1f}%', rotation["label"], rotation_color, "card"),
            "card_caption": (f'{"Alts" if rotation["gap"] >= 0 else "BTC"} leading by {abs(rotation["gap"]):.1f}pp over 24h'
                             if rotation["gap"] is not None else "BTC share of total crypto market cap"),
            "confluence_name": "Altcoin Rotation",
            "confluence_positive": rotation["positive"],
            "confluence_display": f'{dominance["btc_dominance_pct"]:.1f}% BTC dom. ({rotation["label"]})',
            "explainer_icon": "&#129517;",
            "explainer_text": (
                "Bitcoin's share of total crypto market cap, plus whether the other tracked coins are "
                "outperforming or underperforming BTC over the last 24 hours. Rising alt participation reads "
                "as broader breadth, not a price prediction for either side."),
            "page_title": "Altcoin Rotation / BTC Dominance",
            "page_hero_html": _value_visual(f'{dominance["btc_dominance_pct"]:.1f}%', rotation["label"], rotation_color, "hero"),
            "page_sections": [
                ("What It Measures", "<p>Two related reads: Bitcoin's share of total crypto market capitalization "
                 "(\"BTC dominance\"), and whether our tracked altcoins are currently outperforming or "
                 "underperforming BTC on a 24-hour basis.</p>"),
                ("How It's Calculated", "<p>BTC dominance comes directly from CoinGecko's global market data "
                 f"(no calculation on our end). The rotation label compares BTC's own 24-hour price change "
                 f"against the average 24-hour change of the other tracked coins: a gap of "
                 f"&ge;{DOMINANCE_ROTATION_THRESHOLD:.0f} percentage points either way reads Alts Outperforming "
                 f"or BTC Outperforming; anything smaller reads In Line.</p>"),
                ("How We Read \"Positive\"", "<p>In Signal Confluence, Alts Outperforming counts as the "
                 "\"positive\" reading here &mdash; the same broadening-participation convention Top Sectors "
                 "and Capital Flow use &mdash; not a call that altcoins are the better trade. An In Line "
                 "reading is left out of Signal Confluence entirely rather than forced green or red, and BTC "
                 "dominance rising or falling says nothing about where the total market is headed.</p>"),
                ("Why It Matters", "<p>Distinguishes a market where gains are concentrated in Bitcoin from one "
                 "where participation has broadened into altcoins &mdash; two very different market states "
                 "that a single \"market is up\" headline can't tell apart.</p>"),
                ("Data Source &amp; Update Frequency", "<p>CoinGecko public global-market API. "
                 "Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: (f"{row['dominance']['btc_dominance_pct']:.1f}% BTC dom."
                                               if row.get("dominance") else "&ndash;"),
        },
        {
            "id": "leverage_heat",
            "page": "leverage-heat.html",
            "card_label": "&#128293; Leverage Heat",
            "card_main_html": _value_visual(f'{leverage["funding_rate_pct"]:+.3f}%', lev_signal["label"], lev_color, "card"),
            "card_caption": f'${leverage["open_interest_usd"]/1e9:.2f}B BTC perp open interest',
            "confluence_name": "Leverage Heat",
            "confluence_positive": lev_signal["positive"],
            "confluence_display": f'{leverage["funding_rate_pct"]:+.3f}% ({lev_signal["label"]})',
            "explainer_icon": "&#128293;",
            "explainer_text": (
                "BTC perpetual futures funding rate - the periodic payment between long and short leverage "
                "positions. Elevated readings in either direction mean one side is more crowded with leverage, "
                "which raises liquidation-cascade risk, not a directional price call."),
            "page_title": "Leverage Heat",
            "page_hero_html": _value_visual(f'{leverage["funding_rate_pct"]:+.3f}%', lev_signal["label"], lev_color, "hero"),
            "page_sections": [
                ("What It Measures", "<p>The BTC perpetual futures funding rate - the periodic payment "
                 "exchanged directly between long and short position holders on perpetual futures contracts. "
                 "A positive rate means longs are paying shorts (the long side is more crowded with leverage); "
                 "a negative rate means the reverse.</p>"),
                ("How It's Calculated", f"<p>Pulled directly from OKX's BTC-USDT perpetual swap (no calculation "
                 f"on our end). A rate within &plusmn;{LEVERAGE_ELEVATED_THRESHOLD:.2f}% reads Balanced; "
                 f"&plusmn;{LEVERAGE_ELEVATED_THRESHOLD:.2f}&ndash;{LEVERAGE_EXTREME_THRESHOLD:.2f}% reads "
                 f"Elevated Long/Short Leverage; beyond &plusmn;{LEVERAGE_EXTREME_THRESHOLD:.2f}% reads Extreme "
                 f"Long/Short Leverage, based on OKX's own typical historical funding range.</p>"),
                ("How We Read \"Positive\"", "<p>Unlike most indicators here, \"positive\" doesn't mean "
                 "bullish - it means balanced, uncrowded positioning. Elevated leverage in <strong>either</strong> "
                 "direction counts as the non-positive reading in Signal Confluence, since crowded leverage on "
                 "either side raises the risk of a fast, forced liquidation cascade, not just for one side.</p>"),
                ("Why It Matters", "<p>Crowded leverage - long or short - is fuel for sharp, fast moves as "
                 "over-leveraged positions get forcibly liquidated. Balanced funding means positioning is "
                 "healthier and less prone to a cascade in either direction.</p>"),
                ("Data Source &amp; Update Frequency", "<p>OKX public market-data API (BTC-USDT-SWAP), no key "
                 "required. Refreshed automatically every 15 minutes. (Binance's equivalent endpoint is "
                 "geo-blocked for US-region requests, so this uses OKX instead.)</p>"),
            ],
            "history_formatter": lambda row: (f'{row["leverage"]["funding_rate_pct"]:+.3f}%'
                                               if row.get("leverage") else "&ndash;"),
        },
        {
            "id": "stablecoin_liquidity",
            "page": "stablecoin-liquidity.html",
            "card_label": "&#128181; Stablecoin Liquidity",
            "card_main_html": _value_visual(f'${stablecoins["total_usd"]/1e9:.1f}B', stable_signal["signal"], stable_signal["color"], "card"),
            "card_caption": f'{stablecoins["change_7d_pct"]:+.1f}% over 7 days',
            "confluence_name": "Stablecoin Liquidity",
            "confluence_positive": stable_signal["expanding"],
            "confluence_display": f"${stablecoins['total_usd']/1e9:.1f}B ({stablecoins['change_7d_pct']:+.1f}%)",
            "explainer_icon": "&#128181;",
            "explainer_text": (
                "Tracks total stablecoin supply and its 7-day change &mdash; a proxy for how much capital is "
                "parked in the crypto ecosystem, ready to deploy. Expanding supply means fresh capital is "
                "entering; contracting means it's leaving the space entirely."),
            "page_title": "Stablecoin Liquidity",
            "page_hero_html": _value_visual(f'${stablecoins["total_usd"]/1e9:.1f}B', stable_signal["signal"], stable_signal["color"], "hero"),
            "page_sections": [
                ("What It Measures", "<p>The total circulating supply of major USD-pegged stablecoins (USDT, "
                 "USDC, DAI, and others) across all chains &mdash; a proxy for how much \"dry powder\" is "
                 "sitting inside the crypto ecosystem, ready to move.</p>"),
                ("How It's Calculated", "<p>Total stablecoin market cap today vs. 7 days ago. A positive "
                 "7-day change reads Expanding, negative reads Contracting.</p>"),
                ("Why It Matters", "<p>Price charts don't show whether new capital is entering or leaving the "
                 "ecosystem. Expanding stablecoin supply means more capital is parked and available to buy; "
                 "contracting supply means capital is leaving the space entirely, not just rotating between "
                 "coins.</p>"),
                ("Data Source &amp; Update Frequency", "<p>DefiLlama's free stablecoins API "
                 "(stablecoins.llama.fi). Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: (f"${row['stablecoins']['total_usd']/1e9:.1f}B "
                                               f"({row['stablecoins']['change_7d_pct']:+.1f}%)"
                                               if row.get("stablecoins") else "&ndash;"),
        },
        {
            "id": "defi_pulse",
            "page": "defi-pulse.html",
            "card_label": "&#9889; DeFi Pulse",
            "card_main_html": _value_visual(f'${defi_tvl["total_usd"]/1e9:.1f}B', defi_signal["signal"], defi_signal["color"], "card"),
            "card_caption": f'{defi_tvl["change_7d_pct"]:+.1f}% over 7 days',
            "confluence_name": "DeFi Pulse",
            "confluence_positive": defi_signal["growing"],
            "confluence_display": f"${defi_tvl['total_usd']/1e9:.1f}B ({defi_tvl['change_7d_pct']:+.1f}%)",
            "explainer_icon": "&#9889;",
            "explainer_text": (
                "Total value locked (TVL) across DeFi protocols, all chains combined, and its 7-day change. "
                "A different read than Stablecoin Liquidity - this is capital actually deployed into DeFi, not "
                "just dry powder sitting on the sidelines."),
            "page_title": "DeFi Pulse",
            "page_hero_html": _value_visual(f'${defi_tvl["total_usd"]/1e9:.1f}B', defi_signal["signal"], defi_signal["color"], "hero"),
            "page_sections": [
                ("What It Measures", "<p>Total Value Locked (TVL) across DeFi protocols &mdash; lending "
                 "markets, DEXs, staking, and more &mdash; combined across every chain DefiLlama tracks.</p>"),
                ("How It's Calculated", "<p>Total TVL today vs. 7 days ago. A positive 7-day change reads "
                 "Growing, negative reads Shrinking.</p>"),
                ("How This Differs From Stablecoin Liquidity", "<p>Stablecoin Liquidity tracks dry powder "
                 "sitting in USD-pegged tokens, ready to deploy but not yet used. TVL tracks capital already "
                 "deployed into DeFi protocols &mdash; and moves with the price of what's locked (a broad "
                 "rally can lift TVL with zero new deposits), not purely a fresh-capital signal.</p>"),
                ("Why It Matters", "<p>A rising TVL means more capital and activity is flowing into DeFi "
                 "protocols specifically, beyond just holding or trading spot assets.</p>"),
                ("Data Source &amp; Update Frequency", "<p>DefiLlama's free TVL API (api.llama.fi). "
                 "Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: (f"${row['defi_tvl']['total_usd']/1e9:.1f}B "
                                               f"({row['defi_tvl']['change_7d_pct']:+.1f}%)"
                                               if row.get("defi_tvl") else "&ndash;"),
        },
        {
            "id": "network_health",
            "page": "network-health.html",
            "card_label": "&#9889;&#65039; Miner Health",
            "card_main_html": _value_visual(f'{network_health["hashrate_eh"]:.0f} EH/s', net_signal["label"], net_signal["color"], "card"),
            "card_caption": f'{network_health["fastest_fee_satvb"]} sat/vB &middot; {network_health["pending_tx_count"]:,} pending',
            "confluence_name": "Miner Health",
            "confluence_positive": net_signal["positive"],
            "confluence_display": f'{network_health["hashrate_eh"]:.0f} EH/s ({net_signal["label"]})',
            "explainer_icon": "&#9889;&#65039;",
            "explainer_text": (
                "Bitcoin network hash rate and its trend into the next difficulty adjustment, plus current "
                "mempool congestion. Rising hash rate means more mining power is actively securing the "
                "network - a security/health read, not a price signal."),
            "page_title": "Miner Health / Network Activity",
            "page_hero_html": _value_visual(f'{network_health["hashrate_eh"]:.0f} EH/s', net_signal["label"], net_signal["color"], "hero"),
            "page_sections": [
                ("What It Measures", "<p>The Bitcoin network's total hash rate (mining power securing the "
                 "network, in exahashes/second), its trend into the next difficulty adjustment, and current "
                 "mempool congestion (pending transactions and required fees).</p>"),
                ("How It's Calculated", f"<p>Hash rate and the difficulty-change estimate come directly from "
                 f"mempool.space, computed from actual observed block times since the last retarget - not a "
                 f"projection of our own. A next-retarget change of &plusmn;{NETWORK_HEALTH_THRESHOLD:.0f}% or "
                 f"more reads Hash Rate Rising/Falling; anything smaller reads Stable.</p>"),
                ("Why It Matters", "<p>Hash rate is Bitcoin's actual security budget - a rising hash rate means "
                 "more real-world computing power is committed to securing the network. Mempool congestion and "
                 "fees are a direct read on how much genuine transaction demand the network is seeing right "
                 "now.</p>"),
                ("Data Source &amp; Update Frequency", "<p>mempool.space's free public API, no key required. "
                 "Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: (f'{row["network_health"]["hashrate_eh"]:.0f} EH/s'
                                               if row.get("network_health") else "&ndash;"),
        },
        {
            "id": "liquidations",
            "page": "liquidations.html",
            "card_label": "&#128165; Liquidations",
            "card_main_html": _value_visual(
                f'${(liquidations["long_liq_usd"]+liquidations["short_liq_usd"])/1e6:.2f}M',
                liq_signal["label"], liq_signal["color"], "card", stacked=True),
            "card_caption": f'${liquidations["long_liq_usd"]/1e6:.1f}M long &middot; ${liquidations["short_liq_usd"]/1e6:.1f}M short',
            "confluence_name": "Liquidations",
            "confluence_positive": liq_signal["positive"],
            "confluence_display": f'${(liquidations["long_liq_usd"]+liquidations["short_liq_usd"])/1e6:.2f}M ({liq_signal["label"]})',
            "explainer_icon": "&#128165;",
            "explainer_text": (
                "The size and direction of BTC perpetual futures liquidations - forced closeouts of "
                "over-leveraged positions - over the most recent ~100 events on OKX. Heavy liquidations in "
                "either direction mean forced, cascading action, not a directional price call."),
            "page_title": "Liquidations",
            "page_hero_html": _value_visual(
                f'${(liquidations["long_liq_usd"]+liquidations["short_liq_usd"])/1e6:.2f}M',
                liq_signal["label"], liq_signal["color"], "hero", stacked=True),
            "page_sections": [
                ("What It Measures", "<p>The dollar size and direction of BTC perpetual futures liquidations "
                 "&mdash; forced closeouts of over-leveraged long or short positions &mdash; over the most "
                 "recent batch of events.</p>"),
                ("How It's Calculated", f"<p>Pulled from OKX's public liquidation-orders feed for the "
                 f"BTC-USDT perpetual swap: the most recent 100 filled liquidation events, split into total "
                 f"long-side vs. short-side notional value. A share of "
                 f"&ge;{int(LIQUIDATION_DOMINANCE_THRESHOLD*100)}% on one side reads that side Dominant; "
                 f"otherwise Balanced, or Quiet if there were no liquidations at all in the window. Because "
                 f"this is a fixed <em>count</em> of events rather than a fixed time window, the window itself "
                 f"stretches during quiet markets and shrinks during volatile ones - the last 100 events "
                 f"span roughly {liquidations['window_minutes']:.0f} minutes right now.</p>"),
                ("An Honest Note On Coverage", "<p>This covers OKX's own order flow only, not an aggregate "
                 "across every exchange &mdash; there is no free, no-key data source for that (the well-known "
                 "aggregators require a paid plan). Treat this as a real, representative sample of BTC "
                 "perpetual liquidation activity, not a total market figure.</p>"),
                ("Why It Matters", "<p>Long-dominant liquidations mean a sharp drop forced leveraged longs out; "
                 "short-dominant means a sharp rise forced leveraged shorts out (a short squeeze). Either way, "
                 "it's forced selling or buying, not organic.</p>"),
                ("Data Source &amp; Update Frequency", "<p>OKX public liquidation-orders API, no key required. "
                 "Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: (
                f'${(row["liquidations"]["long_liq_usd"]+row["liquidations"]["short_liq_usd"])/1e6:.2f}M'
                if row.get("liquidations") else "&ndash;"),
        },
        {
            "id": "whale_activity",
            "page": "whale-activity.html",
            "card_label": "&#128040; Whale Activity",
            "card_main_html": _value_visual(str(whale_signal["whale_count"]), whale_signal["label"], whale_signal["color"], "card"),
            "card_caption": f'${whale_signal["whale_total_usd"]/1e6:.1f}M across whale-sized transfers',
            "confluence_name": "Whale Activity",
            "confluence_positive": whale_signal["positive"],
            "confluence_display": f'{whale_signal["whale_count"]} transfers ({whale_signal["label"]})',
            "explainer_icon": "&#128040;",
            "explainer_text": (
                "The count of $1M+ BTC transactions in a sample of recent network activity. Purely a size "
                "read - we can't tell whether a large transfer is accumulation, distribution, or just an "
                "exchange moving its own coins, so this deliberately isn't scored positive or negative."),
            "page_title": "Whale Activity",
            "page_hero_html": _value_visual(str(whale_signal["whale_count"]), whale_signal["label"], whale_signal["color"], "hero"),
            "page_sections": [
                ("What It Measures", "<p>How many individual Bitcoin transactions moving $1,000,000 or more "
                 "showed up in a recent sample of network activity.</p>"),
                ("How It's Calculated", f"<p>Sampled from the most recent {whale_activity['sample_size']:,} "
                 f"unconfirmed (mempool) transactions via blockchain.info's public API. Each transaction's "
                 f"total output value (in BTC, converted to USD at the current price) is checked against the "
                 f"${WHALE_THRESHOLD_USD/1e6:.0f}M threshold. 0 qualifying transfers reads Quiet, 1&ndash;4 "
                 f"reads Active, 5+ reads Elevated.</p>"),
                ("An Honest Note On Coverage", "<p>Total output value is a standard but approximate proxy for "
                 "\"amount moved\" - it can overcount slightly since change outputs returning coins to the "
                 "sender are included too, and it can't distinguish a whale accumulating from an exchange "
                 "shuffling coins between its own wallets. Treat this as a size signal, not an intent "
                 "signal.</p>"),
                ("Why It Matters", "<p>Large transactions are worth knowing about even without knowing their "
                 "intent - a cluster of them often precedes or accompanies periods of higher volatility.</p>"),
                ("Data Source &amp; Update Frequency", "<p>blockchain.info's free public API, no key required. "
                 "Refreshed automatically every 15 minutes.</p>"),
            ],
            "history_formatter": lambda row: (
                f'{_whale_signal(row["whale_activity"], row["prices"])["whale_count"]} transfers'
                if row.get("whale_activity") and row.get("prices") else "&ndash;"),
        },
        {
            "id": "macro_risk",
            "page": "macro-risk.html",
            "card_label": "&#127758; Macro Risk",
            "card_main_html": _badge_visual(macro_signal["level"].upper(), f'pulse-risk-{macro_signal["level"]}', "card"),
            "card_caption": f'VIX {macro["vix"]:.1f} &middot; DXY {macro["dxy"]:.1f}',
            "confluence_name": "Macro Risk",
            "confluence_positive": macro_signal["positive"],
            "confluence_display": f'{macro_signal["level"].upper()} (VIX {macro["vix"]:.1f})',
            "explainer_icon": "&#127758;",
            "explainer_text": (
                "A Low/Moderate/Elevated read on traditional-market conditions - equity volatility (VIX) and "
                "US dollar strength (DXY) - the only indicator here that looks outside crypto. A temperature "
                "check on macro turbulence, not a crypto-specific signal."),
            "page_title": "Macro Risk",
            "page_hero_html": _badge_visual(macro_signal["level"].upper(), f'pulse-risk-{macro_signal["level"]}', "hero"),
            "page_sections": [
                ("What It Measures", "<p>How turbulent <em>traditional</em> financial markets look right now "
                 "&mdash; equity volatility and US dollar strength &mdash; not a crypto-specific read. The "
                 "only indicator on this site that looks outside crypto entirely.</p>"),
                ("How It's Calculated", "<p>A Crypto Playback score built from two real inputs: the CBOE "
                 "Volatility Index (VIX) and the US Dollar Index's (DXY) daily move. VIX &ge;30 (equities' "
                 "classic \"high fear\" threshold) adds 2 points, &ge;20 (above its long-run average) adds 1. "
                 "A single-day DXY move of &ge;0.5% in either direction adds 1 point. 0 points reads Low, "
                 "1&ndash;2 reads Moderate, 3 reads Elevated.</p>"),
                ("Why It Matters", "<p>Crypto doesn't trade in a vacuum - a risk-off shock in traditional "
                 "markets (volatility spikes, a sharply strengthening dollar) often spills into crypto risk "
                 "appetite too, even when nothing crypto-specific has changed.</p>"),
                ("Data Source &amp; Update Frequency", "<p>Yahoo Finance's public market data (VIX, DX-Y.NYB). "
                 "Both only update during US trading hours, so readings hold steady overnight and on weekends "
                 "&mdash; not stale data, just no new trading session yet. Refreshed automatically every 15 "
                 "minutes.</p>"),
            ],
            "history_formatter": lambda row: (f'{row["macro"]["vix"]:.1f} VIX'
                                               if row.get("macro") else "&ndash;"),
        },
    ]

    # All 13 indicators above share the one 15-minute live refresh
    # timestamp - set once here instead of repeating it in every dict.
    # ETF Flow/Market Breadth/Narrative Momentum below set their own
    # (date-only, no fabricated time) since they refresh on a different
    # schedule entirely.
    live_updated_display = _format_live_updated(dashboard.get("updated_at"), "recently")
    for entry in registry:
        entry["last_updated_display"] = live_updated_display

    if etf:
        flow_m = float(etf["latest_flow_usd"]) / 1e6
        etf_color = INDICATOR_GREEN if flow_m >= 0 else INDICATOR_RED
        etf_word = _etf_pressure_label(etf["pressure_score"], flow_m)
        etf_card_main = _value_visual(f"{flow_m:+.1f}M", etf_word, etf_color, "card")
        etf_hero_main = _value_visual(f"{flow_m:+.1f}M", etf_word, etf_color, "hero")
        etf_caption = f'{etf["streak_count"]}D {etf["streak_direction"].title()} Streak &middot; {etf["latest_date"]}'
        etf_history_rows = [{"date_display": d, "flow": f} for d, f in etf["history"][:12]]
        etf_history_formatter = lambda row: f"${float(row['flow'])/1e6:+.1f}M"
        validation_line = (
            f"<p>Cross-checked against XOOMAR (an independent, holdings-file-derived source covering IBIT, "
            f"BITB, and ARKB) for the same three funds: current status "
            f"<strong>{etf['validation_status'] or 'UNAVAILABLE'}</strong>"
            + (f", difference ${float(etf['validation_difference_usd'])/1e6:.1f}M." if etf.get('validation_difference_usd') else ".")
            + "</p>"
            + (f"<p>{etf['validation_notes']}</p>"
               if etf.get("validation_notes") and "Driven mainly by" in etf["validation_notes"] else "")
        )
        freshness_line = (f"<p>Data freshness: <strong>{etf['freshness']}</strong> ({etf['days_old']} day(s) "
                           f"since the latest confirmed trading day, {etf['latest_date']}).</p>")
        etf_confluence_positive = etf["latest_flow_usd"] >= 0
        etf_confluence_display = f"${flow_m:+.1f}M ({etf['streak_count']}d {etf['streak_direction']})"
    else:
        etf_card_main = etf_hero_main = _badge_visual("AWAITING DAILY ETF DATA", "", "card")
        etf_caption = "Spot Bitcoin ETF net flow, US trading days"
        etf_history_rows, etf_history_formatter = [], lambda row: "&ndash;"
        validation_line, freshness_line = "<p>No reading yet.</p>", ""
        etf_confluence_positive, etf_confluence_display = None, None
    etf_last_updated = _format_date_only(etf['latest_date']) if etf else "awaiting first daily update"

    etf_entry = {
        "id": "etf_flow",
        "page": "etf-flow.html",
        "card_label": "&#127974; ETF Flow",
        "card_main_html": etf_card_main,
        "card_caption": etf_caption,
        "last_updated_display": etf_last_updated,
        "confluence_name": "ETF Flow",
        "confluence_positive": etf_confluence_positive,
        "confluence_display": etf_confluence_display,
        "explainer_icon": "&#127974;",
        "explainer_text": (
            "Net daily flow across US spot Bitcoin ETFs, plus a rolling streak and flow-pressure score. "
            "Positive means the funds took in more money than left them that day, not a price call. "
            "Cross-checked against a second, independent data source before it's shown."),
        "page_title": "Bitcoin ETF Flow",
        "page_hero_html": etf_hero_main,
        "page_sections": [
            ("What It Measures", "<p>The net daily flow of money into or out of US spot Bitcoin ETFs (shares "
             "created/redeemed, valued in USD) &mdash; not a price prediction, a measurement of fund-level "
             "buying and selling pressure on a single US trading day.</p>"),
            ("How It's Calculated", "<p>Primary data: SoSoValue's aggregate net flow across all US spot BTC "
             "ETFs. From the stored daily history we compute the latest confirmed flow, 3D/7D/30D/90D "
             "cumulative totals and averages (30D/90D only shown once that much real history has actually "
             "accumulated - never a shorter window mislabeled as a longer one), the current consecutive "
             "inflow/outflow streak, a Flow Momentum read (7-day average vs. 30-day average, scaled by the "
             "size of the 30-day average: &ge;50% relative difference reads Accelerating/Decelerating, "
             "&ge;15% reads Strengthening/Weakening, otherwise Neutral), and a 0&ndash;100 Flow Pressure "
             "score (40% the percentile rank of today's flow, 60% the percentile rank of the trailing 7-day "
             "cumulative, both against all stored history - weighted toward the 7-day figure so one "
             "unusually large single day can't dominate the score).</p>"),
            ("Independent Validation", validation_line +
             "<p>XOOMAR doesn't cover every US spot BTC ETF, so this is only ever a same-subset check "
             "(SoSoValue's IBIT+BITB+ARKB total vs. XOOMAR's), never treated as an error against SoSoValue's "
             "full-universe total. Data via <a href=\"https://xoomar.com\">xoomar.com</a>.</p>"),
            ("Why It Matters", "<p>Distinguishes real, fund-level capital movement from ordinary "
             "secondary-market price action. We deliberately don't say things like \"institutions are "
             "buying\" or \"this predicts price\" &mdash; only what the flow itself was.</p>"),
            ("Data Source, Freshness &amp; Update Frequency", freshness_line +
             "<p>Primary: SoSoValue Open API. Validation: XOOMAR. ETF flow is a once-per-US-trading-day "
             "figure, so this refreshes a few times a day on its own schedule &mdash; not the 15-minute "
             "cycle the other live indicators use, since polling a daily number that often would be "
             "pointless.</p>"),
        ],
        "history_formatter": etf_history_formatter,
        "_own_history_rows": etf_history_rows,  # only this entry has its own history source, not the shared one
        "refresh_note": ("Refreshed a few times a day &mdash; ETF flow is a once-per-US-trading-day figure, "
                          "not something backfilled or estimated between real updates."),
    }
    registry.append(etf_entry)

    if breadth and breadth["have_50"]:
        breadth_color = INDICATOR_GREEN if breadth["pct_above_50"] >= 55 else (
            INDICATOR_RED if breadth["pct_above_50"] < 45 else "#F2C94C")
        breadth_card_main = _value_visual(f'{breadth["pct_above_50"]}%', breadth["label"], breadth_color, "card")
        breadth_hero_main = _value_visual(f'{breadth["pct_above_50"]}%', breadth["label"], breadth_color, "hero")
        two_hundred_d_line = (
            f'<p>The same read against each coin\'s 200-day SMA: <strong>{breadth["pct_above_200"]}%</strong> '
            f'({breadth["eligible_200"]} of {breadth["universe_size"]} coins eligible).</p>'
            if breadth["have_200"] else
            f'<p>The 200-day version of this reading is still building - {breadth["available_days"]} of the '
            f'200 days of price history it needs have been stored so far.</p>'
        )
        breadth_caption = f'{breadth["eligible_50"]} of {breadth["universe_size"]} coins eligible &middot; {breadth["latest_date"]}'
        breadth_history_rows = [{"date_display": h["date"], "pct": h["pct_above_50"]} for h in breadth["history"]]
        breadth_history_formatter = lambda row: f'{row["pct"]}%'
        breadth_confluence_positive = breadth["pct_above_50"] >= 55
        breadth_confluence_display = f'{breadth["pct_above_50"]}% {breadth["label"]}'
    else:
        awaiting_days = breadth["available_days"] if breadth else 0
        breadth_card_main = breadth_hero_main = _badge_visual(
            f"BUILDING ({awaiting_days}/50 DAYS)" if awaiting_days else "AWAITING DATA", "", "card")
        breadth_caption = "Share of tracked coins above their moving average"
        two_hundred_d_line = "<p>No reading yet.</p>"
        breadth_history_rows, breadth_history_formatter = [], lambda row: "&ndash;"
        breadth_confluence_positive, breadth_confluence_display = None, None
    breadth_last_updated = (_format_date_only(breadth['latest_date']) if breadth
                             else "awaiting first daily update")

    breadth_entry = {
        "id": "market_breadth",
        "page": "market-breadth.html",
        "card_label": "&#128200; Market Breadth",
        "last_updated_display": breadth_last_updated,
        "card_main_html": breadth_card_main,
        "card_caption": breadth_caption,
        "confluence_name": "Market Breadth",
        "confluence_positive": breadth_confluence_positive,
        "confluence_display": breadth_confluence_display,
        "explainer_icon": "&#128200;",
        "explainer_text": (
            "The share of a fixed 40-coin universe currently trading above its own 50-day moving average. "
            "A broad measure of how widespread the current trend actually is, not just whether a few large "
            "coins are moving."),
        "page_title": "Market Breadth",
        "page_hero_html": breadth_hero_main,
        "page_sections": [
            ("What It Measures", "<p>The percentage of a fixed universe of 40 major coins (by market cap, "
             "stablecoins and wrapped/staked tokens excluded) currently trading above their own 50-day simple "
             "moving average - the same style of \"breadth\" reading traders use for stocks (e.g. the share of "
             "S&amp;P 500 members above their 200-day average), applied to crypto.</p>"),
            ("How It's Calculated", "<p>Each coin's own 50-day SMA is computed from its stored daily price "
             "history, then we count what share of the universe is currently priced above that line. The "
             "40-coin universe is locked in on this indicator's first day and isn't reshuffled day to day, so "
             "the reading tracks the same set of coins over time instead of silently changing what it "
             "measures.</p>" + two_hundred_d_line),
            ("Why It Matters", "<p>Distinguishes a broad, widespread trend from one being carried by just a "
             "handful of large coins - two markets can show the same headline price action with very different "
             "breadth underneath it.</p>"),
            ("Data Source &amp; Update Frequency", "<p>CoinGecko public markets API, one price snapshot per "
             "coin per day. Refreshed a few times a day on its own schedule - not the 15-minute cycle the "
             "other live indicators use, since a moving-average reading doesn't change faster than daily.</p>"),
        ],
        "history_formatter": breadth_history_formatter,
        "_own_history_rows": breadth_history_rows,
        "refresh_note": ("Refreshed a few times a day &mdash; a moving-average breadth reading changes at "
                          "most once a day, not something backfilled or estimated between real updates."),
    }
    registry.append(breadth_entry)

    if narrative and narrative["have_7d"]:
        top3 = narrative["ranked"][:3]
        narrative_visual_rows = [{"label": r["label"], "change_24h": r["avg_change_pct"]} for r in top3]
        narrative_card_main = _sector_list_visual(narrative_visual_rows, "card")
        narrative_hero_main = _sector_list_visual(narrative_visual_rows, "hero")
        narrative_caption = f'7-day average &middot; {narrative["latest_date"]}'
        narrative_history_rows = [{"date_display": h["date"], "label": h["leader_label"], "value": h["leader_avg"]}
                                   for h in narrative["history"]]
        narrative_history_formatter = lambda row: f'{row["label"]} {row["value"]:+.1f}%'
        leader = top3[0] if top3 else None
        narrative_confluence_positive = bool(top3) and sum(1 for r in top3 if r["avg_change_pct"] >= 0) > len(top3) / 2
        narrative_confluence_display = f'{leader["label"]} {leader["avg_change_pct"]:+.1f}%' if leader else "&ndash;"
    else:
        awaiting_days = narrative["available_days"] if narrative else 0
        narrative_card_main = narrative_hero_main = _badge_visual(
            f"BUILDING ({awaiting_days}/7 DAYS)" if awaiting_days else "AWAITING DATA", "", "card")
        narrative_caption = "Sectors ranked by sustained weekly performance"
        narrative_history_rows, narrative_history_formatter = [], lambda row: "&ndash;"
        narrative_confluence_positive, narrative_confluence_display = None, None
    narrative_last_updated = (_format_date_only(narrative['latest_date']) if narrative
                               else "awaiting first daily update")

    narrative_entry = {
        "id": "narrative_momentum",
        "page": "narrative-momentum.html",
        "last_updated_display": narrative_last_updated,
        "card_label": "&#128161; Narrative Momentum",
        "card_main_html": narrative_card_main,
        "card_caption": narrative_caption,
        "confluence_name": "Narrative Momentum",
        "confluence_positive": narrative_confluence_positive,
        "confluence_display": narrative_confluence_display,
        "explainer_icon": "&#128161;",
        "explainer_text": (
            "Ranks sectors by their trailing 7-day average daily performance, not just today's snapshot - a "
            "different cut than Top Sectors, surfacing sustained strength over a single good day."),
        "page_title": "Narrative Momentum",
        "page_hero_html": narrative_hero_main,
        "page_sections": [
            ("What It Measures", "<p>Which crypto narrative/sector categories have shown the strongest "
             "<em>sustained</em> performance over the trailing 7 days - not just today's 24-hour move.</p>"),
            ("How It's Calculated", "<p>Each day, we record every tracked sector's 24-hour change (the same "
             "data Top Sectors uses). This indicator then ranks sectors by their average daily change across "
             "the last 7 stored days, once a real 7 days of history has accumulated - a 2 or 3-day average is "
             "never silently labeled as a 7-day read.</p>"),
            ("How This Differs From Top Sectors", "<p>Top Sectors answers \"what's leading right now.\" This "
             "answers \"what's been consistently strong all week.\" A sector can spike for a single day "
             "without appearing here, or grind steadily upward all week without topping today's "
             "leaderboard.</p>"),
            ("Why It Matters", "<p>Distinguishes a narrative with real, sustained rotation behind it from one "
             "single volatile day of price action.</p>"),
            ("Data Source &amp; Update Frequency", "<p>Computed by The Crypto Playback from CoinGecko sector "
             "data already fetched every 15 minutes - one new day of history is recorded once per day. "
             "Refreshed automatically every 15 minutes.</p>"),
        ],
        "history_formatter": narrative_history_formatter,
        "_own_history_rows": narrative_history_rows,
        "refresh_note": ("Refreshed automatically every 15 minutes, but a 7-day average only moves once a day "
                          "at most, when that day's sector snapshot is recorded."),
    }
    registry.append(narrative_entry)

    # Returned alongside the registry (not just the registry alone) so
    # callers that also need the raw signals/mover/etc. for other sections
    # (Market Snapshot's text, What Changed's comparisons) get them from
    # this one call instead of recomputing them a second time.
    return {
        "indicators": registry,
        "signals": signals,
        "resolved_mover": resolved_mover,
        "stable_signal": stable_signal,
        "etf": etf,
    }


# Client-side, in-browser live price updates for the Top 6 Market ticker
# only - every other indicator on the site is still a server-rendered
# static page rebuilt by the 15-minute (or 4x/day) GitHub Actions workflows,
# which is the right cadence for numbers that take real computation. Price
# itself changes constantly though, and polling CoinGecko's free, public,
# unauthenticated /simple/price endpoint directly from each visitor's own
# browser - no API key involved, so nothing of ours is exposed - gets prices
# visibly live without needing a 1-minute GitHub Actions schedule (which
# GitHub doesn't reliably honor below ~5 minutes anyway) or multiplying load
# on every other indicator's own data source just to speed up six prices.
# Fails silently (console.warn only) on a network hiccup or rate limit -
# the server-rendered values stay on screen either way, so a visitor never
# sees blank or broken numbers, just a slightly stale ones until the next
# successful poll.
LIVE_TICKER_SCRIPT = """<script>
(function () {
  var coins = Array.prototype.slice.call(document.querySelectorAll('.pulse-coin[data-coingecko-id]'))
    .filter(function (el) { return el.getAttribute('data-coingecko-id'); });
  if (!coins.length) return;
  var ids = coins.map(function (el) { return el.getAttribute('data-coingecko-id'); }).join(',');
  var asof = document.getElementById('pulse-asof');

  function poll() {
    fetch('https://api.coingecko.com/api/v3/simple/price?ids=' + encodeURIComponent(ids) +
          '&vs_currencies=usd&include_24hr_change=true')
      .then(function (r) { if (!r.ok) throw new Error('CoinGecko ' + r.status); return r.json(); })
      .then(function (data) {
        coins.forEach(function (el) {
          var id = el.getAttribute('data-coingecko-id');
          var quote = data[id];
          if (!quote || typeof quote.usd !== 'number') return;
          var priceEl = el.querySelector('.pulse-coin-price');
          var changeEl = el.querySelector('.pulse-coin-change');
          if (priceEl) priceEl.textContent = '$' + quote.usd.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
          if (changeEl && typeof quote.usd_24h_change === 'number') {
            var change = quote.usd_24h_change;
            changeEl.textContent = (change >= 0 ? '+' : '') + change.toFixed(1) + '%';
            changeEl.style.color = change >= 0 ? '#8FBF5C' : '#E8837A';
          }
        });
        if (asof) {
          var now = new Date();
          asof.textContent = 'Live price updates via CoinGecko \\u00b7 last updated ' +
            now.toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit', second: '2-digit'});
        }
      })
      .catch(function (err) { console.warn('Live ticker update skipped:', err); });
  }

  poll();
  setInterval(poll, 60000);
})();
</script>"""


def render_market_pulse(prices, date_abbrev):
    """Homepage-only Top 6 Market ticker. Used to also render Fear & Greed /
    Biggest Mover / Risk Radar / Capital Flow / Top Sectors as their own
    cards right below the ticker, but those are now shown once, in the
    Alerts & Indicators section further down the page - kept here rather
    than duplicated so there's a single source of truth for each card.

    Each .pulse-coin carries data-coingecko-id so the client-side live-price
    script (see LIVE_TICKER_SCRIPT) knows which coin each card is without
    guessing from the symbol - coins fetched before this field existed just
    won't live-update until the next 15-minute refresh backfills it."""
    coin_cards = "".join(
        f"""<div class="pulse-coin" data-coingecko-id="{c.get('id', '')}">
        <span class="pulse-coin-sym">{c['symbol']}</span>
        <span class="pulse-coin-price">${c['price']:,.2f}</span>
        <span class="pulse-coin-change" style="color:{'#8FBF5C' if c['change_24h'] >= 0 else '#E8837A'};">{c['change_24h']:+.1f}%</span>
      </div>"""
        for c in prices
    )

    return f"""<section class="pulse-ticker-panel">
    <div class="pulse-wrap">
      <div class="pulse-ticker-head">
        <div class="pulse-eyebrow-row">
          <svg class="pulse-trend-icon" viewBox="0 0 24 24" fill="none" stroke="#8FBF5C" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="2,17 8,11 12,14 22,4"/><polyline points="15,4 22,4 22,11"/></svg>
          <span class="pulse-eyebrow">Top {len(prices)} Market</span>
          <svg class="pulse-trend-icon" viewBox="0 0 24 24" fill="none" stroke="#E8837A" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="2,7 8,13 12,10 22,20"/><polyline points="15,20 22,20 22,13"/></svg>
        </div>
        <span class="pulse-asof" id="pulse-asof">Price data via CoinGecko &middot; {date_abbrev}</span>
      </div>
      <div class="pulse-ticker-grid">{coin_cards}</div>
    </div>
  </section>
  {LIVE_TICKER_SCRIPT}"""


def _latest_missed_story(entries):
    """The odd-story-of-the-day from the newest issue that has one (older issues predate the feature)."""
    for e in entries:
        try:
            m = json.load(open(os.path.join(POSTS_DATA_DIR, f"{e['slug']}.json"))).get("missed_story")
        except (OSError, ValueError):
            continue
        if isinstance(m, dict) and m.get("headline") and m.get("body") and m.get("source_url"):
            return m
    return None


def _teaser_image(slug):
    """Best-effort: a real image from this issue's stories, used as the
    homepage teaser card's side image. Checks every story in the issue
    (not just the lead one) so a minimum image count on the homepage is
    reliably met - returns None (never a fabricated/stock photo) only if
    the post predates saved story data or none of its stories has one."""
    try:
        with open(os.path.join(POSTS_DATA_DIR, f"{slug}.json")) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    for s in data.get("stories") or []:
        if s.get("image_url"):
            return s["image_url"]
    return None


def compute_market_overview(indicators, signals, fng, sectors):
    """The Market Snapshot paragraph, Signal Confluence rows/score/
    interpretation, and the bullish/bearish/neutral lean - computed once so
    the homepage (render_index) and the newsletter email (email_render) can
    never drift apart on wording or numbers."""
    confluence_items = [
        (ind["confluence_name"], ind["confluence_positive"], ind["confluence_display"])
        for ind in indicators if ind["confluence_positive"] is not None
    ]
    positive_count = sum(1 for _, pos, _ in confluence_items if pos)
    total_count = len(confluence_items)
    negatives = [name for name, pos, _ in confluence_items if not pos]
    positives = [name for name, pos, _ in confluence_items if pos]
    if positive_count == total_count:
        interpretation = "Every signal we track is currently pointing the same direction: up."
    elif positive_count == 0:
        interpretation = "Every signal we track is currently pointing the same direction: down."
    elif positive_count >= total_count - 1:
        interpretation = f"Signals are broadly positive, with {negatives[0]} the lone holdout."
    elif positive_count <= 1:
        interpretation = f"Signals lean cautious, with {positives[0] if positives else 'nothing'} the lone bright spot."
    else:
        interpretation = "Signals are mixed, split between bullish and cautious readings."

    fng_word = fng["classification"].lower()
    breadth_phrase = ("broad" if signals["breadth_pct"] >= 0.6
                       else ("narrow" if signals["breadth_pct"] <= 0.4 else "mixed"))
    top_sector_name = sectors[0]["label"] if sectors else None
    snapshot_text = (
        f"The market is currently showing a {fng_word}-leaning profile, with "
        f"{signals['risk_level']} volatility risk and {signals['capital_flow_signal'].lower()} capital flow. "
    )
    if top_sector_name:
        snapshot_text += (
            f"{top_sector_name} is leading sector rotation, and participation across tracked assets "
            f"looks {breadth_phrase}."
        )
    else:
        snapshot_text += f"Participation across tracked assets looks {breadth_phrase}."


    if fng["value"] >= 55:
        market_lean = "bullish"
    elif fng["value"] <= 45:
        market_lean = "bearish"
    else:
        market_lean = "neutral"
    return {
        "confluence_items": confluence_items,
        "positive_count": positive_count,
        "total_count": total_count,
        "interpretation": interpretation,
        "snapshot_text": snapshot_text,
        "market_lean": market_lean,
    }


def load_market_overview():
    """Same overview, built straight from the latest live data on disk
    (data/live_indicators.json) - what the newsletter email calls. Returns
    the overview dict plus the 'Updated ...' line and the raw fng value."""
    entries = load_index()
    dashboard = _load_dashboard_data(entries)
    if dashboard is None:
        return None
    ctx = _build_indicator_registry(dashboard, dashboard["gauge_path"])
    overview = compute_market_overview(ctx["indicators"], ctx["signals"], dashboard["fng"], dashboard["sectors"])
    overview["updated"] = _format_live_updated(dashboard.get("updated_at"), entries[0].get("date_display", "") if entries else "")
    overview["fng_value"] = dashboard["fng"]["value"]
    return overview


def render_index(entries):
    hero = home_v2.hero(16)

    if not entries:
        return page("", "The Crypto Playback", hero + "<p>First post coming soon.</p>", datetime.now().year, theme="v2")

    # Homepage's live indicator sections (ticker, Market Snapshot, Signal
    # Confluence, What Changed, Alerts & Indicators) are sourced from
    # data/live_indicators.json, refreshed on its own 15-minute schedule by
    # refresh_indicators.py - completely independent of when a newsletter
    # issue publishes. See _load_dashboard_data for the fallback used
    # before that file exists.
    dashboard = _load_dashboard_data(entries)
    if dashboard is None:
        return page("", "The Crypto Playback", hero + "<p>First post coming soon.</p>", datetime.now().year, theme="v2")
    prices = dashboard["prices"]
    fng = dashboard["fng"]
    mover = dashboard["mover"]
    sectors = dashboard["sectors"]
    stablecoins = dashboard["stablecoins"]
    dominance = dashboard["dominance"]
    leverage = dashboard["leverage"]
    defi_tvl = dashboard["defi_tvl"]
    network_health = dashboard["network_health"]
    liquidations = dashboard["liquidations"]
    macro = dashboard["macro"]
    gauge_src = dashboard["gauge_path"]
    date_abbrev = _format_live_updated(dashboard.get("updated_at"), entries[0].get("date_display", ""))

    # One call builds every indicator's data + markup (see
    # _build_indicator_registry) - render_index() only needs to turn that
    # single list into the three homepage sections below, plus pull out
    # signals/resolved_mover/stable_signal/etf for the Market Snapshot text
    # and What Changed comparisons further down.
    ctx = _build_indicator_registry(dashboard, gauge_src)
    indicators = ctx["indicators"]
    signals = ctx["signals"]
    resolved_mover = ctx["resolved_mover"]
    stable_signal = ctx["stable_signal"]
    etf = ctx["etf"]
    market_strip = home_v2.price_strip(prices, date_abbrev)

    # ============ Playback Snapshot: Signal Confluence + What Changed? ============
    # Both built only from real per-issue data already computed above - no
    # external "AI live" call at page-load, no invented deltas. The market
    # snapshot paragraph and interpretation lines are templated prose driven
    # by the actual numbers, same pattern as mover_label/mover_caption above.
    overview = compute_market_overview(indicators, signals, fng, sectors)
    confluence_items = overview["confluence_items"]
    positive_count = overview["positive_count"]
    total_count = overview["total_count"]
    interpretation = overview["interpretation"]
    snapshot_text = overview["snapshot_text"]
    market_lean = overview["market_lean"]

    market_snapshot_section = home_v2.snapshot(fng, snapshot_text, total_count, date_abbrev)

    # "What Changed?" compares the latest live reading to the snapshot from
    # about 24 hours ago in data/indicator_history.json (written by
    # refresh_indicators.py on every scheduled run) - real deltas only,
    # completely independent of the newsletter's publish cadence now. An
    # indicator that didn't move meaningfully is left out rather than
    # padded with a non-change to hit some item count.
    history = load_indicator_history()
    prev_snapshot = _find_comparison_snapshot(history, hours_ago=24)

    change_items = []
    if prev_snapshot:
        prev_fng = prev_snapshot["fng"]
        prev_sectors = prev_snapshot.get("sectors") or []
        prev_signals = _compute_derived_signals(prev_snapshot["prices"], prev_fng, prev_sectors)
        prev_mover_display = _live_mover_display(prev_snapshot["mover"])

        fng_delta = fng["value"] - prev_fng["value"]
        if fng_delta != 0:
            dot = "&#128994;" if fng_delta > 0 else "&#128308;"
            change_items.append((dot, "Fear &amp; Greed shifted",
                                  f"{prev_fng['value']} &rarr; {fng['value']} ({fng_delta:+d})"))

        if signals["risk_level"] != prev_signals["risk_level"]:
            risk_rank = {"low": 0, "moderate": 1, "elevated": 2}
            dot = "&#128994;" if risk_rank[signals["risk_level"]] < risk_rank[prev_signals["risk_level"]] else "&#128308;"
            change_items.append((dot, "Risk Radar shifted",
                                  f"{prev_signals['risk_level'].upper()} &rarr; {signals['risk_level'].upper()}"))

        flow_delta = signals["capital_flow_score"] - prev_signals["capital_flow_score"]
        if abs(flow_delta) >= 5:
            dot = "&#128994;" if flow_delta > 0 else "&#128308;"
            change_items.append((dot, "Capital Flow moved",
                                  f"{prev_signals['capital_flow_score']} &rarr; {signals['capital_flow_score']} ({flow_delta:+d})"))

        if sectors and prev_sectors and sectors[0]["label"] != prev_sectors[0]["label"]:
            change_items.append(("&#128993;", "Sector leadership rotated",
                                  f"{prev_sectors[0]['label']} &rarr; {sectors[0]['label']}"))

        if resolved_mover["symbol"] != prev_mover_display["symbol"]:
            change_items.append(("&#128993;", "Biggest mover changed",
                                  f"{prev_mover_display['symbol']} &rarr; {resolved_mover['symbol']}"))

        prev_stablecoins = prev_snapshot.get("stablecoins")
        if prev_stablecoins:
            stable_delta_b = (stablecoins["total_usd"] - prev_stablecoins["total_usd"]) / 1e9
            if abs(stable_delta_b) >= 0.5:
                dot = "&#128994;" if stable_delta_b > 0 else "&#128308;"
                change_items.append((dot, "Stablecoin supply moved",
                                      f"${prev_stablecoins['total_usd']/1e9:.1f}B &rarr; "
                                      f"${stablecoins['total_usd']/1e9:.1f}B ({stable_delta_b:+.1f}B)"))

        prev_dominance = prev_snapshot.get("dominance")
        if prev_dominance:
            dom_delta = dominance["btc_dominance_pct"] - prev_dominance["btc_dominance_pct"]
            if abs(dom_delta) >= 0.5:
                dot = "&#128994;" if dom_delta < 0 else "&#128308;"  # falling dominance = alts gaining share
                change_items.append((dot, "BTC Dominance shifted",
                                      f"{prev_dominance['btc_dominance_pct']:.1f}% &rarr; "
                                      f"{dominance['btc_dominance_pct']:.1f}% ({dom_delta:+.1f}pp)"))

        prev_leverage = prev_snapshot.get("leverage")
        if prev_leverage:
            lev_now, lev_prev = _leverage_signal(leverage), _leverage_signal(prev_leverage)
            if lev_now["label"] != lev_prev["label"]:
                dot = "&#128994;" if lev_now["positive"] and not lev_prev["positive"] else (
                    "&#128308;" if not lev_now["positive"] and lev_prev["positive"] else "&#128993;")
                change_items.append((dot, "Leverage Heat shifted",
                                      f"{lev_prev['label']} &rarr; {lev_now['label']}"))

        prev_defi_tvl = prev_snapshot.get("defi_tvl")
        if prev_defi_tvl:
            tvl_delta_b = (defi_tvl["total_usd"] - prev_defi_tvl["total_usd"]) / 1e9
            if abs(tvl_delta_b) >= 1.0:
                dot = "&#128994;" if tvl_delta_b > 0 else "&#128308;"
                change_items.append((dot, "DeFi TVL moved",
                                      f"${prev_defi_tvl['total_usd']/1e9:.1f}B &rarr; "
                                      f"${defi_tvl['total_usd']/1e9:.1f}B ({tvl_delta_b:+.1f}B)"))

        prev_network_health = prev_snapshot.get("network_health")
        if prev_network_health:
            hash_delta = network_health["hashrate_eh"] - prev_network_health["hashrate_eh"]
            if abs(hash_delta) >= 20:
                dot = "&#128994;" if hash_delta > 0 else "&#128308;"
                change_items.append((dot, "Hash rate moved",
                                      f"{prev_network_health['hashrate_eh']:.0f} &rarr; "
                                      f"{network_health['hashrate_eh']:.0f} EH/s ({hash_delta:+.0f})"))

        prev_liquidations = prev_snapshot.get("liquidations")
        if prev_liquidations:
            liq_now, liq_prev = _liquidation_signal(liquidations), _liquidation_signal(prev_liquidations)
            if liq_now["label"] != liq_prev["label"] and not (liq_now["positive"] and liq_prev["positive"]):
                dot = "&#128994;" if liq_now["positive"] else "&#128308;"
                change_items.append((dot, "Liquidations shifted",
                                      f"{liq_prev['label']} &rarr; {liq_now['label']}"))

        prev_macro = prev_snapshot.get("macro")
        if prev_macro:
            macro_now, macro_prev = _macro_risk_signal(macro), _macro_risk_signal(prev_macro)
            if macro_now["level"] != macro_prev["level"]:
                risk_rank = {"low": 0, "moderate": 1, "elevated": 2}
                dot = "&#128994;" if risk_rank[macro_now["level"]] < risk_rank[macro_prev["level"]] else "&#128308;"
                change_items.append((dot, "Macro Risk shifted",
                                      f"{macro_prev['level'].upper()} &rarr; {macro_now['level'].upper()}"))

    # ETF Flow diffs against its own most recent prior trading day (from
    # data/etf_flows.json) rather than the ~24h-ago snapshot above - it has
    # its own daily-trading-day cadence, not the 15-minute one.
    if etf and len(etf["history"]) >= 2:
        _, latest_etf_flow = etf["history"][0]
        prev_etf_date, prev_etf_flow = etf["history"][1]
        if (latest_etf_flow >= 0) != (prev_etf_flow >= 0):
            dot = "&#128994;" if latest_etf_flow >= 0 else "&#128308;"
            change_items.append((dot, "ETF flow flipped direction",
                                  f"${float(prev_etf_flow)/1e6:+.1f}M &rarr; ${float(latest_etf_flow)/1e6:+.1f}M"))

    if not change_items and prev_snapshot:
        # PREVIEW COPY, requested by the user to see the section's real
        # layout with content in it (there isn't 24h of real drift yet).
        # Same real indicators this section actually tracks, illustrative
        # numbers only - swap back to the genuine "No major shifts" empty
        # state (still handled below) once real drift exists, or sooner
        # on request.
        change_items = [
            ("&#128994;", "Fear &amp; Greed climbed", "62 &rarr; 70 (+8)"),
            ("&#128994;", "Capital Flow strengthened", "74 &rarr; 88 (+14)"),
            ("&#128308;", "Risk Radar ticked up", "LOW &rarr; MODERATE"),
            ("&#128993;", "Sector leadership rotated", "AI &rarr; RWA"),
            ("&#128994;", "Biggest mover flipped", "ETH +3.1% &rarr; SOL +18.6%"),
        ]

    confluence_section = home_v2.confluence_and_changed(
        confluence_items, positive_count, total_count, interpretation, change_items, date_abbrev)

    alerts_indicators_section = home_v2.alerts(indicators, date_abbrev)
    news_section = home_v2.news(entries, _teaser_image, _latest_missed_story(entries))
    subscribe_section = home_v2.subscribe()
    explainer_section = home_v2.decode(indicators)

    body = (hero + market_strip + market_snapshot_section + confluence_section + alerts_indicators_section
            + news_section + subscribe_section + explainer_section)
    return page(
        "", "Daily Bitcoin & Crypto Market Research | The Crypto Playback", body,
        datetime.now().year, theme="v2",
        description=("Free daily Bitcoin & crypto market research. 16 live indicators (Fear & Greed, ETF flows, stablecoin liquidity, risk) plus a morning newsletter."),
        path="", jsonld=home_v2.jsonld(indicators),
        extra_head='<link rel="preload" as="image" href="assets/v2/crypto-playback-mascot-bitcoin-uncle-sam.webp" type="image/webp" fetchpriority="high">',
        indicator_links=home_v2.indicator_footer_links(indicators),
    )


def _recent_readings(history, limit=12):
    """The most recent `limit` live snapshots (oldest first for display),
    each with its derived signals recomputed the same way as the current
    reading. Sourced from data/indicator_history.json, written on every
    refresh_indicators.py run - independent of the newsletter, so this
    grows on its own 15-minute schedule rather than once per issue."""
    rows = []
    for snap in history[-limit:]:
        prices = snap.get("prices") or []
        fng = snap.get("fng")
        if not prices or not fng:
            continue
        sectors = snap.get("sectors") or []
        sig = _compute_derived_signals(prices, fng, sectors)
        dt = datetime.fromisoformat(snap["updated_at"])
        rows.append({
            "date_display": f"{format_date_abbrev(dt)} {dt.strftime('%-I:%M %p')} UTC",
            "fng": fng,
            "mover": _live_mover_display(snap["mover"]),
            "sectors": sectors,
            "risk_level": sig["risk_level"],
            "capital_flow_score": sig["capital_flow_score"],
            "capital_flow_signal": sig["capital_flow_signal"],
            "stablecoins": snap.get("stablecoins"),
        })
    return rows


def _indicator_page_shell(eyebrow, title, hero_html, sections, history_rows, history_formatter,
                           last_updated_display,
                           refresh_note="Refreshed automatically every 15 minutes &mdash; nothing here is backfilled or estimated."):
    sections_html = "".join(
        f"""<div class="indicator-section">
        <h2>{heading}</h2>
        {body}
      </div>"""
        for heading, body in sections
    )
    if history_rows:
        history_html = "".join(
            f"""<div class="indicator-history-row">
            <span class="indicator-history-date">{row['date_display']}</span>
            <span class="indicator-history-value">{history_formatter(row)}</span>
          </div>"""
            for row in history_rows
        )
    else:
        history_html = '<p class="changed-empty">No history yet &mdash; check back after the next refresh.</p>'
    body_html = f"""<section class="indicator-hero">
    <div class="indicator-hero-inner">
      <img class="indicator-mascot" src="assets/mascot-color-section.png?v={SECTION_MASCOT_VERSION}" alt="The Crypto Playback mascot &mdash; Bitcoin and crypto market newsletter, {title} indicator">
      <div class="indicator-hero-content">
        <span class="snapshot-eyebrow">{eyebrow}</span>
        <div class="snapshot-meta"><span>Last updated {last_updated_display}</span></div>
        <h1 class="indicator-title">{title}</h1>
        <div class="indicator-hero-value">{hero_html}</div>
      </div>
    </div>
  </section>
  <div class="indicator-body">
    {sections_html}
    <div class="indicator-section">
      <h2>Recent Readings</h2>
      <div class="indicator-history">{history_html}</div>
      <p class="indicator-history-note">{refresh_note}</p>
    </div>
  </div>"""
    return page("", f"{title} — The Crypto Playback", body_html, datetime.now().year)


def render_indicator_pages(entries):
    """{filename: html} for every real indicator's dedicated page - one
    _indicator_page_shell() call per entry in the shared registry (see
    _build_indicator_registry), using that indicator's own recent-history
    source (the general 15-minute live history for most; ETF Flow and
    Market Breadth each carry their own daily history instead, see the
    registry entries' "_own_history_rows"). `entries` is only needed for _load_dashboard_data's
    fallback path (before the refresh workflow has ever run). Adding an 8th
    indicator later needs no change here at all - it already has a page the
    moment it's added to the registry."""
    dashboard = _load_dashboard_data(entries)
    if dashboard is None:
        return {}
    gauge_src = dashboard["gauge_path"]
    ctx = _build_indicator_registry(dashboard, gauge_src)
    shared_history = _recent_readings(load_indicator_history())

    pages = {}
    for ind in ctx["indicators"]:
        history_rows = ind.get("_own_history_rows", shared_history)
        note = ind.get("refresh_note", "Refreshed automatically every 15 minutes: nothing here is backfilled or estimated.")
        pages[ind["page"]] = indicator_v2.render(ind, history_rows, note, ctx["indicators"])
    return pages



def render_archive(entries):
    items = ""
    for e in entries:
        items += f"""<a class="v2-arch-item" href="posts/{e['slug']}.html" data-tag="{e['tag']}">
      <span class="v2-arch-meta"><span class="v2-arch-tag v2-arch-{e['tag'].lower()}">{e['tag']}</span><span class="v2-arch-date">{e['date_display']}</span></span>
      <span class="v2-arch-title">{e['title']}</span>
      <span class="v2-arch-go" aria-hidden="true">&rarr;</span>
    </a>"""
    body = f"""<section class="v2-ind-hero v2-arch-hero" aria-labelledby="arch-h">
  <div class="v2-wrap">
    <nav class="v2-crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a><span aria-hidden="true">›</span><span aria-current="page">Archive</span></nav>
    <div class="v2-kicker v2-kicker-brass v2-ind-kicker">Every issue, free to read</div>
    <h1 class="v2-ind-title" id="arch-h">The Playback Archive</h1>
    <p class="v2-arch-sub">On this page you will find every daily and weekly newsletter we&rsquo;ve ever released.</p>
  </div>
</section>
<section class="v2-section v2-ind-body">
  <div class="v2-wrap">
    <div class="v2-arch-filters" role="group" aria-label="Filter issues">
      <button class="active" data-filter="all">All</button><button data-filter="Daily">Daily</button><button data-filter="Weekly">Weekly</button>
    </div>
    <div class="v2-arch-list" id="archive-items">{items}</div>
    <p class="v2-ind-sub"><a class="v2-btn v2-btn-navy" href="index.html#subscribe">Get the daily playback free</a></p>
  </div>
</section>
<script>
  document.querySelectorAll('.v2-arch-filters button').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.v2-arch-filters button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const f = btn.dataset.filter;
      document.querySelectorAll('.v2-arch-item').forEach(item => {{
        item.style.display = (f === 'all' || item.dataset.tag === f) ? '' : 'none';
      }});
    }});
  }});
</script>"""
    import json as _json
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://cryptoplayback.com/"},
        {"@type": "ListItem", "position": 2, "name": "Archive", "item": "https://cryptoplayback.com/archive.html"}]}
    return page("", "Archive: Daily & Weekly Crypto Briefings | The Crypto Playback", body, datetime.now().year, theme="v2",
                description="Every daily and weekly Bitcoin and crypto market briefing from The Crypto Playback, newest first.",
                path="archive.html", jsonld=_json.dumps(crumbs, separators=(",", ":")),
                indicator_links=_footer_indicator_links())


def _footer_indicator_links():
    dash = _load_dashboard_data(load_index())
    if dash is None:
        return ""
    return home_v2.indicator_footer_links(_build_indicator_registry(dash, dash["gauge_path"])["indicators"])


def write_seo(entries, indicator_files):
    """sitemap.xml, robots.txt, feed.xml, llms.txt, 404.html (see seo.py)."""
    dashboard = _load_dashboard_data(entries)
    if dashboard is None:
        return
    ctx = _build_indicator_registry(dashboard, dashboard["gauge_path"])
    updated = None
    try:
        updated = datetime.fromisoformat(dashboard["updated_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError, TypeError):
        pass
    seo.write_seo_files(entries, ctx["indicators"], indicator_files, updated)


PENDING_DIR = os.path.join(DATA_DIR, "pending")


def save_pending_post(post):
    """Stores a generated issue WITHOUT publishing it: no site page, no index
    entry, no homepage or archive change. publish_approved.py promotes it
    (via add_post_and_rebuild) once its Buttondown email has been published."""
    os.makedirs(PENDING_DIR, exist_ok=True)
    path = os.path.join(PENDING_DIR, f"{post['slug']}.json")
    with open(path, "w") as f:
        json.dump(post, f, indent=2)
    return path


def add_post_and_rebuild(post):
    """post: dict as passed to render_post_html, plus 'excerpt' and 'slug'.
    Writes the post's HTML page, updates the index, and rebuilds index.html + archive.html."""
    with open(os.path.join(POSTS_DATA_DIR, f"{post['slug']}.json"), "w") as f:
        json.dump(post, f, indent=2)

    post_html = render_post_html(post, "../")
    with open(os.path.join(POSTS_HTML_DIR, f"{post['slug']}.html"), "w") as f:
        f.write(post_html)

    # Drop any existing entry for this slug first - re-publishing a slug must
    # replace its archive entry, never add a second one pointing at the same page.
    entries = [e for e in load_index() if e["slug"] != post["slug"]]
    entries.insert(0, {
        "slug": post["slug"],
        "title": post["title"],
        "date_display": post["date_display"],
        "tag": post["tag"],
        "excerpt": post["excerpt"],
    })
    save_index(entries)

    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(render_index(entries))
    with open(os.path.join(ROOT, "archive.html"), "w") as f:
        f.write(render_archive(entries))
    pages = render_indicator_pages(entries)
    for filename, html in pages.items():
        with open(os.path.join(ROOT, filename), "w") as f:
            f.write(html)
    rebuild_post_pages()
    write_seo(entries, pages.keys())


if __name__ == "__main__":
    entries = load_index()
    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(render_index(entries))
    with open(os.path.join(ROOT, "archive.html"), "w") as f:
        f.write(render_archive(entries))
    indicator_pages = render_indicator_pages(entries)
    for filename, html in indicator_pages.items():
        with open(os.path.join(ROOT, filename), "w") as f:
            f.write(html)
    n_posts = rebuild_post_pages()
    write_seo(entries, indicator_pages.keys())
    try:
        import build_static_pages      # About + Resources: regenerated every build so their stylesheet version never goes stale
        build_static_pages.build()
    except Exception as exc:     # noqa: BLE001 - never break the main build
        print(f"Static pages skipped: {exc}")
    try:
        import pro_page
        pro_page.write_institutional_page()
    except Exception as exc:     # noqa: BLE001 - the Pro page must never break the main build
        print(f"Institutional page skipped: {exc}")
    print(f"Rebuilt index.html and archive.html from {len(entries)} existing post(s), "
          f"plus {len(indicator_pages)} indicator page(s) and {n_posts} issue page(s).")
