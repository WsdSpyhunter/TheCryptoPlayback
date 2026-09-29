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
from datetime import datetime, timezone
from PIL import Image, ImageDraw
from partials import page, asset_version

HEADER_WEB_VERSION = asset_version("header-web.png")
SECTION_MASCOT_VERSION = asset_version("mascot-color-section.png")
CAMO_VERSION = asset_version("camo-brand.png")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
POSTS_DATA_DIR = os.path.join(DATA_DIR, "posts")
POSTS_HTML_DIR = os.path.join(ROOT, "posts")
GAUGES_DIR = os.path.join(ROOT, "assets", "gauges")
INDEX_FILE = os.path.join(DATA_DIR, "posts_index.json")

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
    <span class="ticker-subscribe-text">SUBSCRIBE HERE</span>
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
    """post: dict with title, date, tag, ticker_html, sentiment_html, issue_pill_html,
    top_story_html, stories (list of {headline, body, source_title, source_url, image_url})"""
    stories_html = ""
    for s in post["stories"]:
        img_html = ""
        if s.get("image_url"):
            img_html = f'<img class="story-image" src="{s["image_url"]}" alt="" loading="lazy">'
        stories_html += f"""<div class="story">
      <h3>{s['headline']}</h3>
      {img_html}
      {s['body']}
      <a class="source-link" href="{s['source_url']}" target="_blank" rel="noopener">Read more at {s['source_title']} &rarr;</a>
    </div>"""

    masthead_html = render_masthead().replace("{root}", root_prefix)
    sentiment_html = post.get('sentiment_html', '').replace("{gauge_src}", f"{root_prefix}{post.get('gauge_path', '')}")

    body = f"""<article class="post">
    {masthead_html}
    {post.get('ticker_html', '')}
    {sentiment_html}
    <div class="release-row">
      <span class="release-date">{post['date_display']}</span>
      <span class="release-issue">Issue #{post.get('issue_number', 1)}</span>
    </div>
    <div class="title-block">
      {post.get('issue_pill_html', '')}
      <h1>{post['title']}</h1>
    </div>
    {post.get('top_story_html', '')}
    {stories_html}
  </article>"""
    return page(root_prefix, f"{post['title']} — The Crypto Playback", body, datetime.now().year)


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


def _resolve_mover(mover, week_mover, tag):
    """Which mover to show + its real change, shared by the dashboard cards,
    the Signal Confluence dots and the indicator pages so they can never
    show different numbers for the same thing."""
    if tag == "Weekly" and week_mover:
        return {
            "symbol": week_mover["symbol"],
            "change": week_mover["change_7d"],
            "label": "BIGGEST MOVER OF THE WEEK",
            "caption": "Rolling data from the previous 7 days",
            "period": "the previous 7 days",
        }
    return {
        "symbol": mover["symbol"],
        "change": mover["change_24h"],
        "label": "BIGGEST MOVER TODAY",
        "caption": "",
        "period": "the last 24 hours",
    }


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


def render_market_pulse(prices, date_abbrev):
    """Homepage-only Top 6 Market ticker. Used to also render Fear & Greed /
    Biggest Mover / Risk Radar / Capital Flow / Top Sectors as their own
    cards right below the ticker, but those are now shown once, in the
    Alerts & Indicators section further down the page - kept here rather
    than duplicated so there's a single source of truth for each card."""
    coin_cards = "".join(
        f"""<div class="pulse-coin">
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
        <span class="pulse-asof">Price data via CoinGecko &middot; {date_abbrev}</span>
      </div>
      <div class="pulse-ticker-grid">{coin_cards}</div>
    </div>
  </section>"""


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


def render_index(entries):
    # header-web.png: same masthead art as the email (header-a.png), but with
    # the candlestick chart decoration in the corners painted out for the
    # website specifically (user request) - the email's own header-a.png is
    # untouched. The tagline ("YOUR #1 SOURCE FOR BITCOIN & CRYPTO NEWS
    # HIGHLIGHTS") is baked into the image itself, so there's no separate
    # script/tagline markup needed here the way the old hero had.
    hero = f"""<section class="hero">
    <div class="wrap">
      <img class="hero-masthead" src="assets/header-web.png?v={HEADER_WEB_VERSION}" alt="The Crypto Playback — your daily and weekly pulse on Bitcoin and the entire crypto market">
    </div>
  </section>"""

    if not entries:
        return page("", "The Crypto Playback", hero + "<p>First post coming soon.</p>", datetime.now().year)

    # Homepage-only market design (see render_market_pulse) built from the
    # latest issue's real numbers - a static snapshot from the last publish
    # for now (design pass only, per explicit instruction to nail the layout
    # before wiring up any live CoinGecko/Fear&Greed pulls).
    latest_slug = entries[0]["slug"]
    with open(os.path.join(POSTS_DATA_DIR, f"{latest_slug}.json")) as f:
        latest_full = json.load(f)
    prices, fng, mover = _market_data_from_post(latest_full)
    if len(prices) < 6:
        # This snapshot predates the Top-6 change (fetch_prices.py/
        # generate_issue.py already fetch and save 6 real coins for every
        # post from here on) - padding with one placeholder card just so
        # the design can be reviewed as a real 6-wide grid. Not a real
        # price; replaced automatically the next time a post publishes.
        prices = prices + [{"symbol": "DOGE", "price": 0.18, "change_24h": 3.4}]
    gauge_src = latest_full.get("gauge_path", "")
    date_abbrev = latest_full.get("date_abbrev", latest_full.get("date_display", ""))
    # Posts from before the sectors feature don't have this field saved -
    # fall back to a placeholder top-3 so older snapshots still render the
    # card instead of breaking.
    sectors = latest_full.get("sectors") or [
        {"label": "RWA", "change_24h": 12.4},
        {"label": "AI", "change_24h": 8.7},
        {"label": "DeFi", "change_24h": 5.2},
    ]
    # Posts from before the rolling-7-day mover existed don't have this
    # field saved either - a placeholder here just so a Weekly snapshot
    # still previews the card's real 7-day framing.
    week_mover = latest_full.get("week_mover") or {"symbol": "SOL", "change_7d": 18.6}
    tag = latest_full.get("tag", "Daily")
    signals = _compute_derived_signals(prices, fng, sectors)
    resolved_mover = _resolve_mover(mover, week_mover, tag)
    market_strip = render_market_pulse(prices, date_abbrev)

    # ============ Playback Snapshot: Signal Confluence + What Changed? ============
    # Both built only from real per-issue data already computed above - no
    # external "AI live" call at page-load, no invented deltas. The market
    # snapshot paragraph and interpretation lines are templated prose driven
    # by the actual numbers, same pattern as mover_label/mover_caption above.
    sector_positive_count = sum(1 for s in sectors if s["change_24h"] >= 0)
    sector_majority_positive = sectors and sector_positive_count > len(sectors) / 2
    confluence_items = [
        ("Fear &amp; Greed", fng["value"] >= 55, f"{fng['value']} {fng['classification']}"),
        (resolved_mover["label"].title(), resolved_mover["change"] >= 0,
         f"{resolved_mover['symbol']} {resolved_mover['change']:+.1f}%"),
        ("Risk Radar", signals["risk_level"] == "low", signals["risk_level"].upper()),
        ("Capital Flow", signals["capital_flow_signal"] == "Accumulation",
         f"{signals['capital_flow_score']} {signals['capital_flow_signal']}"),
        ("Top Sectors", sector_majority_positive,
         f"{sector_positive_count}/{len(sectors)} positive" if sectors else "&ndash;"),
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
    # Labeled rows, not a bare row of dots - a colored dot alone doesn't tell
    # a visitor which indicator it belongs to or what it's currently reading.
    confluence_rows = "".join(
        f'<div class="confluence-row">'
        f'<span class="confluence-row-dot">{"&#128994;" if pos else "&#128308;"}</span>'
        f'<span class="confluence-row-name">{name}</span>'
        f'<span class="confluence-row-value">{val}</span>'
        f'</div>'
        for name, pos, val in confluence_items
    )

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

    # Sits directly under the Top 6 Market ticker now, in the spot the old
    # Fear & Greed/Mover/Risk/Capital Flow/Sectors cards used to occupy -
    # those are shown once now, in Alerts & Indicators further down.
    market_snapshot_section = f"""<section class="snapshot-banner">
    <div class="snapshot-solo">
      <h2 class="snapshot-title">Market Snapshot</h2>
      <p class="snapshot-text">{snapshot_text}</p>
      <div class="snapshot-meta">
        <span>Updated {latest_full.get('date_display', '')}</span>
        <span class="snapshot-meta-dot">&middot;</span>
        <span>Based on {total_count} market indicators</span>
      </div>
    </div>
  </section>"""

    confluence_section = f"""<section class="confluence-banner">
    <div class="confluence-solo">
      <span class="snapshot-eyebrow">Signal Confluence</span>
      <div class="confluence-score">{positive_count}<span class="confluence-score-total">/{total_count} signals positive</span></div>
      <div class="confluence-list">{confluence_rows}</div>
      <p class="snapshot-text">{interpretation}</p>
    </div>
  </section>"""

    # "What Changed?" compares the latest issue to the most recent *different*
    # prior issue - real deltas only; an indicator that didn't move is left
    # out rather than padded with a non-change to hit some item count.
    prev_full = None
    seen_slugs = {latest_slug}
    for e in entries[1:]:
        if e["slug"] in seen_slugs:
            continue
        seen_slugs.add(e["slug"])
        try:
            with open(os.path.join(POSTS_DATA_DIR, f"{e['slug']}.json")) as f:
                prev_full = json.load(f)
        except (OSError, json.JSONDecodeError):
            prev_full = None
        break

    change_items = []
    if prev_full:
        prev_prices, prev_fng, prev_mover_raw = _market_data_from_post(prev_full)
        prev_sectors = prev_full.get("sectors") or []
        if prev_prices:
            prev_signals = _compute_derived_signals(prev_prices, prev_fng, prev_sectors)
            prev_resolved_mover = _resolve_mover(
                prev_mover_raw, prev_full.get("week_mover"), prev_full.get("tag", "Daily")
            )

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

            if resolved_mover["symbol"] != prev_resolved_mover["symbol"]:
                change_items.append(("&#128993;", "Biggest mover changed",
                                      f"{prev_resolved_mover['symbol']} &rarr; {resolved_mover['symbol']}"))

    if change_items:
        changed_rows = "".join(
            f"""<div class="changed-row">
          <span class="changed-dot">{dot}</span>
          <div class="changed-body">
            <span class="changed-headline">{headline}</span>
            <span class="changed-detail">{detail}</span>
          </div>
        </div>"""
            for dot, headline, detail in change_items
        )
    else:
        fallback = ("Check back after the next update to see what's changed." if not prev_full
                    else "No major shifts since the last update.")
        changed_rows = f'<p class="changed-empty">{fallback}</p>'

    what_changed_section = f"""<section class="changed-banner">
    <div class="changed-inner">
      <span class="snapshot-eyebrow">Since The Last Update</span>
      <h2 class="snapshot-title">What Changed?</h2>
      <div class="changed-list">{changed_rows}</div>
    </div>
  </section>"""

    # ============ Alerts & Indicators - same visual language as the pulse
    # cards above, now each one clickable through to its own dedicated page
    # with the full methodology, real historical readings, and why it
    # matters. ============
    flow_color = {"accumulation": "#8FBF5C", "mixed": "#F2C94C", "distribution": "#E8837A"}.get(
        signals["capital_flow_signal"].lower(), "#8A7F5C"
    )
    alerts_cards = [
        ("fear-greed-index.html", "Fear &amp; Greed Index",
         f'<img class="pulse-gauge" src="{gauge_src}" alt="Fear and Greed gauge">'
         f'<div class="pulse-card-value" style="color:{"#E24C4C" if fng["value"] <= 45 else ("#256B32" if fng["value"] >= 55 else "#8A7F5C")};">'
         f'{fng["value"]}<span class="pulse-card-word">{fng["classification"]}</span></div>',
         "Daily fear and greed sentiment indicator"),
        ("biggest-mover.html", resolved_mover["label"].title(),
         f'<span class="pulse-mover-symbol">{resolved_mover["symbol"]}</span>'
         f'<span class="pulse-mover-change" style="color:{"#256B32" if resolved_mover["change"] >= 0 else "#E24C4C"};">'
         f'{"+" if resolved_mover["change"] >= 0 else ""}{resolved_mover["change"]:.1f}%</span>',
         resolved_mover["caption"] or "Ranked by size of move, not direction"),
        ("risk-radar.html", "&#9888;&#65039; Risk Radar",
         f'<span class="pulse-risk-badge pulse-risk-{signals["risk_level"]}">{signals["risk_level"].upper()}</span>',
         "Overall crypto market risk indicator"),
        ("capital-flow.html", "&#128176; Capital Flow",
         f'<div class="pulse-card-value" style="color:{flow_color};">'
         f'{signals["capital_flow_score"]}<span class="pulse-card-word">{signals["capital_flow_signal"]}</span></div>',
         "Price &amp; sector breadth vs. sentiment"),
        ("top-sectors.html", "&#128202; Top Sectors",
         '<div class="pulse-sector-list">' + "".join(
             f'<div class="pulse-sector-row"><span class="pulse-sector-name">{s["label"]}</span>'
             f'<span class="pulse-sector-change" style="color:{"#8FBF5C" if s["change_24h"] >= 0 else "#E8837A"};">{s["change_24h"]:+.1f}%</span></div>'
             for s in sectors
         ) + '</div>',
         "Best-performing sectors, 24H"),
    ]
    alerts_cards_html = "".join(
        f"""<a class="pulse-card indicator-card" href="{href}">
        <span class="pulse-card-label">{label}</span>
        <div class="pulse-card-main">{main_html}</div>
        <span class="pulse-card-caption">{caption}</span>
        <span class="indicator-card-cta">View full breakdown &rarr;</span>
      </a>"""
        for href, label, main_html, caption in alerts_cards
    )
    alerts_indicators_section = f"""<section class="alerts-banner">
    <div class="pulse-wrap">
      <div class="alerts-head">
        <span class="snapshot-eyebrow">The Crypto Playback</span>
        <h2 class="snapshot-title">Alerts &amp; Indicators</h2>
        <p class="explainer-sub">Tap any card for the full methodology and history</p>
      </div>
      <div class="pulse-columns">{alerts_cards_html}</div>
    </div>
  </section>"""

    # De-duplicated (posts_index.json can carry repeat entries from earlier
    # test runs) top few teasers, newest first, instead of a single excerpt.
    # Minimum 6 on the homepage, with at least 3 of those 6 showing a real
    # side image (alternating cards - confirmed/approved treatment).
    seen = set()
    teasers_html = ""
    count = 0
    for e in entries:
        if e["slug"] in seen:
            continue
        seen.add(e["slug"])
        image_url = _teaser_image(e["slug"]) if count % 2 == 0 else None
        card_class = "teaser-card has-image" if image_url else "teaser-card"
        image_html = (
            f'<img class="teaser-image" src="{image_url}" alt="" loading="lazy">' if image_url else ""
        )
        teasers_html += f"""<a class="{card_class}" href="posts/{e['slug']}.html">
      {image_html}
      <div class="teaser-body">
        <span class="eyebrow-tag">{e['tag']}</span>
        <h2>{e['title']}</h2>
        <div class="date">{e['date_display']}</div>
        <p class="excerpt">{e['excerpt']}</p>
        <span class="read-more">Read the full playback &rarr;</span>
      </div>
    </a>"""
        count += 1
        if count == 6:
            break

    section_banner = f"""<section class="section-banner">
    <div class="section-banner-inner">
      <img class="section-mascot" src="assets/mascot-color-section.png?v={SECTION_MASCOT_VERSION}" alt="">
      <div class="section-title-wrap">
        <h2 class="section-title">Top News Stories</h2>
        <span class="section-title-rule"></span>
        <span class="section-title-sub">Refreshed and updated daily</span>
      </div>
    </div>
  </section>"""
    teaser_section = f'<section class="latest">{teasers_html}</section>'

    # Visual mockup only for now - no form action/backend wired up yet
    # (needs a real Brevo hosted-form endpoint from the user's account).
    # button type="button" (not submit) keeps it inert without needing JS.
    subscribe_section = f"""<section class="subscribe-banner">
    <div class="subscribe-grid">
      <div class="subscribe-decor">
        <img class="subscribe-decor-mascot" src="assets/mascot-color-section.png?v={SECTION_MASCOT_VERSION}" alt="">
      </div>
      <div class="subscribe-inner">
        <span class="subscribe-eyebrow">Join The Playback</span>
        <h2 class="subscribe-title">Subscribe for free and don't miss any more top stories</h2>
        <p class="subscribe-sub">Subscribe now and automatically unlock <strong>VIP OG status</strong>.</p>
        <img class="subscribe-mobile-mascot" src="assets/mascot-color-section.png?v={SECTION_MASCOT_VERSION}" alt="">
        <form class="subscribe-form">
          <input type="text" name="first_name" placeholder="First name" autocomplete="given-name" required>
          <input type="email" name="email" placeholder="Email address" autocomplete="email" required>
          <button type="button" class="subscribe-btn">Subscribe</button>
        </form>
        <span class="subscribe-fineprint">Free (for now). Unsubscribe anytime. No spam. We don't share your info.</span>
      </div>
    </div>
  </section>"""

    # Plain-language explainer for each dashboard card above, so a first-time
    # visitor knows what they're looking at. Icons/images are reused from the
    # dashboard cards themselves (same gauge image, same emoji) rather than
    # inventing new art, so the two sections visibly reference each other.
    mover_period = "the previous 7 days" if latest_full.get("tag", "Daily") == "Weekly" else "the last 24 hours"
    mover_title = "Biggest Mover Of The Week" if latest_full.get("tag", "Daily") == "Weekly" else "Biggest Mover Today"
    explainer_cards = [
        (f'<img class="explainer-icon-img" src="{gauge_src}" alt="">', "Fear &amp; Greed Index",
         "A 0&ndash;100 read on overall market mood, from Extreme Fear to Extreme Greed. "
         "Calculated daily from real volatility, momentum, and social data, not opinion. "
         "Extremes often line up with emotional turning points, not rational ones."),
        ("&#128200;", mover_title,
         f"Whichever of our top 6 tracked coins moved the most, up or down, over {mover_period}. "
         "Ranked purely by the size of the move, not its direction. "
         "A quick read on where the action is happening right now."),
        ("&#9888;&#65039;", "Risk Radar",
         "A simple Low, Moderate, or Elevated snapshot of how turbulent the market is right now, "
         "built from volatility and sentiment extremes. "
         "It's a temperature check on current conditions, not a forecast of what happens next."),
        ("&#128176;", "Capital Flow",
         "A Crypto Playback composite score built from price and sector breadth weighted against "
         "sentiment &mdash; not institutional transaction data. A higher score leans toward "
         "accumulation, a lower score toward distribution."),
        ("&#128202;", "Top Sectors",
         "Ranks major crypto narratives, like AI, RWA, and DeFi, by 24-hour performance. Pulled from a "
         "curated list of major sectors so tiny micro-categories can't skew the results. "
         "Shows where money is rotating inside the market, not just up or down overall."),
    ]
    explainer_html = "".join(
        f"""<div class="explainer-card">
        <div class="explainer-icon">{icon}</div>
        <h3 class="explainer-card-title">{title}</h3>
        <p class="explainer-card-text">{text}</p>
      </div>"""
        for icon, title, text in explainer_cards
    )
    explainer_section = f"""<section class="explainer-banner">
    <div class="explainer-inner">
      <div class="explainer-head">
        <span class="explainer-eyebrow">Know Your Signals</span>
        <h2 class="explainer-title">Decode The Dashboard</h2>
        <p class="explainer-sub">What each alert above actually measures, and how it's calculated</p>
      </div>
      <div class="explainer-grid">{explainer_html}</div>
    </div>
  </section>"""

    body = (hero + market_strip + market_snapshot_section + confluence_section + what_changed_section
            + alerts_indicators_section + section_banner + teaser_section + subscribe_section + explainer_section)
    return page("", "The Crypto Playback", body, datetime.now().year)


def _historical_readings(entries):
    """Real per-issue snapshots (oldest first) across every saved issue -
    used for the 'Recent Readings' list on each indicator page. Only ever
    as deep as real published issues go; nothing here is backfilled or
    estimated, so it starts thin and grows with every new issue."""
    seen = set()
    rows = []
    for e in entries:
        if e["slug"] in seen:
            continue
        seen.add(e["slug"])
        try:
            with open(os.path.join(POSTS_DATA_DIR, f"{e['slug']}.json")) as f:
                full = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        p, f_, m = _market_data_from_post(full)
        if not p:
            continue
        s = full.get("sectors") or []
        sig = _compute_derived_signals(p, f_, s)
        rows.append({
            "date_display": full.get("date_display", ""),
            "tag": full.get("tag", "Daily"),
            "fng": f_,
            "mover": _resolve_mover(m, full.get("week_mover"), full.get("tag", "Daily")),
            "sectors": s,
            "risk_level": sig["risk_level"],
            "capital_flow_score": sig["capital_flow_score"],
            "capital_flow_signal": sig["capital_flow_signal"],
        })
    rows.reverse()
    return rows


def _indicator_page_shell(eyebrow, title, hero_html, sections, history_rows, history_formatter):
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
            <span class="indicator-history-date">{row['date_display']} &middot; {row['tag']}</span>
            <span class="indicator-history-value">{history_formatter(row)}</span>
          </div>"""
            for row in history_rows
        )
    else:
        history_html = '<p class="changed-empty">No history yet &mdash; check back after the next issue.</p>'
    body_html = f"""<section class="indicator-hero">
    <div class="indicator-hero-inner">
      <span class="snapshot-eyebrow">{eyebrow}</span>
      <h1 class="indicator-title">{title}</h1>
      <div class="indicator-hero-value">{hero_html}</div>
    </div>
  </section>
  <div class="indicator-body">
    {sections_html}
    <div class="indicator-section">
      <h2>Recent Readings</h2>
      <div class="indicator-history">{history_html}</div>
      <p class="indicator-history-note">History builds up with every new issue we publish &mdash; it isn't backfilled or estimated.</p>
    </div>
  </div>"""
    return page("", f"{title} — The Crypto Playback", body_html, datetime.now().year)


def render_indicator_pages(entries):
    """{filename: html} for every real indicator's dedicated page. Called
    from both the daily/weekly automation and a manual full rebuild so
    these always reflect the latest published issue. Deliberately built
    for all 5 indicators we have real data for (not just one), so the
    Alerts & Indicators cards on the homepage never link to a dead page."""
    if not entries:
        return {}
    latest_slug = entries[0]["slug"]
    try:
        with open(os.path.join(POSTS_DATA_DIR, f"{latest_slug}.json")) as f:
            latest_full = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    prices, fng, mover = _market_data_from_post(latest_full)
    if not prices:
        return {}
    sectors = latest_full.get("sectors") or []
    week_mover = latest_full.get("week_mover")
    tag = latest_full.get("tag", "Daily")
    gauge_src = latest_full.get("gauge_path", "")
    signals = _compute_derived_signals(prices, fng, sectors)
    resolved_mover = _resolve_mover(mover, week_mover, tag)
    history = _historical_readings(entries)
    flow_color = {"accumulation": "#8FBF5C", "mixed": "#F2C94C", "distribution": "#E8837A"}.get(
        signals["capital_flow_signal"].lower(), "#8A7F5C"
    )

    pages = {}

    fng_color = "#E24C4C" if fng["value"] <= 45 else ("#256B32" if fng["value"] >= 55 else "#8A7F5C")
    pages["fear-greed-index.html"] = _indicator_page_shell(
        "The Crypto Playback", "Fear &amp; Greed Index",
        f'<img class="indicator-gauge" src="{gauge_src}" alt="Fear and Greed gauge">'
        f'<div class="indicator-value" style="color:{fng_color};">{fng["value"]}'
        f'<span class="indicator-value-word">{fng["classification"]}</span></div>',
        [
            ("What It Measures", "<p>Overall crypto market sentiment on a 0&ndash;100 scale, from Extreme Fear "
             "to Extreme Greed.</p>"),
            ("How It's Calculated", "<p>Pulled directly from Alternative.me's Crypto Fear &amp; Greed Index, "
             "which blends volatility, market momentum and volume, social media activity, market dominance, "
             "and search trends into a single score. We don't calculate this ourselves &mdash; we display "
             "their published reading as of each issue.</p>"),
            ("Why It Matters", "<p>Extreme readings often &mdash; not always &mdash; line up with emotional "
             "turning points: extreme fear near local bottoms, extreme greed near local tops. It's a sentiment "
             "gauge, not a price prediction.</p>"),
            ("Data Source &amp; Update Frequency", "<p>Alternative.me Crypto Fear &amp; Greed Index "
             "(api.alternative.me/fng). Refreshed every time we publish a new issue, daily and weekly.</p>"),
        ],
        history, lambda row: f"{row['fng']['value']} {row['fng']['classification']}",
    )

    mover_color = "#256B32" if resolved_mover["change"] >= 0 else "#E24C4C"
    pages["biggest-mover.html"] = _indicator_page_shell(
        "The Crypto Playback", resolved_mover["label"].title(),
        f'<div class="indicator-value"><span class="indicator-mover-symbol">{resolved_mover["symbol"]}</span>'
        f'<span style="color:{mover_color};">{"+" if resolved_mover["change"] >= 0 else ""}{resolved_mover["change"]:.1f}%</span></div>',
        [
            ("What It Measures", "<p>Whichever of our top 6 tracked coins (by market cap, stablecoins excluded) "
             "moved the most &mdash; up or down &mdash; over the relevant window: 24 hours for Daily issues, "
             "7 days for Weekly issues.</p>"),
            ("How It's Calculated", "<p>We rank the 6 tracked coins by the absolute size of their price change "
             "over that window and surface the single biggest mover, in either direction.</p>"),
            ("Why It Matters", "<p>Highlights where the action is actually concentrated, instead of just "
             "reporting that \"the market was up.\"</p>"),
            ("Data Source &amp; Update Frequency", "<p>CoinGecko public markets API. Refreshed every time we "
             "publish a new issue.</p>"),
        ],
        history, lambda row: f"{row['mover']['symbol']} {row['mover']['change']:+.1f}%",
    )

    pages["risk-radar.html"] = _indicator_page_shell(
        "The Crypto Playback", "Risk Radar",
        f'<span class="pulse-risk-badge pulse-risk-{signals["risk_level"]} indicator-risk-badge">{signals["risk_level"].upper()}</span>',
        [
            ("What It Measures", "<p>A simple read on how turbulent current market conditions are &mdash; "
             "Low, Moderate, or Elevated.</p>"),
            ("How It's Calculated", "<p>A Crypto Playback score built from two real inputs: how extreme the "
             "Fear &amp; Greed reading is, and the average size of the 24-hour price move across our 6 tracked "
             "coins. Extreme sentiment (Fear &amp; Greed &ge;80 or &le;20) adds 2 points, borderline extreme "
             "(&ge;70 or &le;30) adds 1. Average 24h volatility &ge;8% adds 2 points, &ge;4% adds 1. "
             "0&ndash;1 points reads Low, 2&ndash;3 reads Moderate, 4+ reads Elevated.</p>"),
            ("Why It Matters", "<p>A temperature check on current conditions, not a forecast of what happens "
             "next.</p>"),
            ("Data Source &amp; Update Frequency", "<p>Computed by The Crypto Playback from Alternative.me "
             "and CoinGecko data &mdash; not pulled from any third-party \"risk\" API. Refreshed every time we "
             "publish a new issue.</p>"),
        ],
        history, lambda row: row["risk_level"].upper(),
    )

    pages["capital-flow.html"] = _indicator_page_shell(
        "The Crypto Playback", "Capital Flow",
        f'<div class="indicator-value" style="color:{flow_color};">{signals["capital_flow_score"]}'
        f'<span class="indicator-value-word">{signals["capital_flow_signal"]}</span></div>',
        [
            ("What It Measures", "<p>Whether price and sector breadth, weighted against sentiment, currently "
             "lean toward accumulation or distribution.</p>"),
            ("How It's Calculated", "<p>60% weight on breadth (the share of our 6 tracked coins and tracked "
             "sectors that are positive over 24 hours) plus 40% weight on the Fear &amp; Greed value, scaled "
             "0&ndash;100. A score of 60+ reads Accumulation, 40&ndash;59 reads Mixed, below 40 reads "
             "Distribution.</p>"),
            ("An Honest Note On The Name", "<p>This is <strong>not</strong> built from ETF flows, exchange "
             "order flow, or on-chain institutional transaction data &mdash; it's a composite of price/sector "
             "breadth and sentiment. We plan to fold in real spot Bitcoin ETF flow data in a future update, "
             "which will make this score more literally about capital flow.</p>"),
            ("Why It Matters", "<p>Distinguishes whether a move is broad-based across many assets, or being "
             "carried by just a couple of large coins.</p>"),
            ("Data Source &amp; Update Frequency", "<p>Computed by The Crypto Playback from CoinGecko and "
             "Alternative.me data. Refreshed every time we publish a new issue.</p>"),
        ],
        history, lambda row: f"{row['capital_flow_score']} {row['capital_flow_signal']}",
    )

    sector_rows_html = "".join(
        f'<div class="pulse-sector-row"><span class="pulse-sector-name">{s["label"]}</span>'
        f'<span class="pulse-sector-change" style="color:{"#8FBF5C" if s["change_24h"] >= 0 else "#E8837A"};">{s["change_24h"]:+.1f}%</span></div>'
        for s in sectors
    )
    pages["top-sectors.html"] = _indicator_page_shell(
        "The Crypto Playback", "Top Sectors",
        f'<div class="pulse-sector-list indicator-sector-list">{sector_rows_html}</div>',
        [
            ("What It Measures", "<p>Which major crypto narrative categories &mdash; AI, RWA, DeFi, L1, L2, "
             "Gaming, Memecoins, DePIN, NFT &mdash; are performing best over the last 24 hours.</p>"),
            ("How It's Calculated", "<p>Ranked by 24-hour market-cap change within a curated watchlist of "
             "recognizable sectors, so a narrow, noisy micro-category can't crowd out the real narratives.</p>"),
            ("Why It Matters", "<p>Shows where money is rotating within the market, not just whether the "
             "market overall is up or down.</p>"),
            ("Data Source &amp; Update Frequency", "<p>CoinGecko categories API. Refreshed every time we "
             "publish a new issue.</p>"),
        ],
        history, lambda row: (f"{row['sectors'][0]['label']} {row['sectors'][0]['change_24h']:+.1f}%"
                               if row.get("sectors") else "&ndash;"),
    )

    return pages


def render_archive(entries):
    items = ""
    for e in entries:
        items += f"""<a class="archive-item" href="posts/{e['slug']}.html" data-tag="{e['tag']}">
      <span class="tag">{e['tag']}</span>
      <h3>{e['title']}</h3>
      <span class="date">{e['date_display']}</span>
    </a>"""

    body = f"""<div class="archive-list">
    <h1>Archive</h1>
    <div class="archive-filters">
      <button class="active" data-filter="all">All</button>
      <button data-filter="Daily">Daily</button>
      <button data-filter="Weekly">Weekly</button>
    </div>
    <div id="archive-items">{items}</div>
  </div>
  <script>
    document.querySelectorAll('.archive-filters button').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.archive-filters button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const f = btn.dataset.filter;
        document.querySelectorAll('.archive-item').forEach(item => {{
          item.style.display = (f === 'all' || item.dataset.tag === f) ? 'block' : 'none';
        }});
      }});
    }});
  </script>"""
    return page("", "Archive — The Crypto Playback", body, datetime.now().year)


def add_post_and_rebuild(post):
    """post: dict as passed to render_post_html, plus 'excerpt' and 'slug'.
    Writes the post's HTML page, updates the index, and rebuilds index.html + archive.html."""
    with open(os.path.join(POSTS_DATA_DIR, f"{post['slug']}.json"), "w") as f:
        json.dump(post, f, indent=2)

    post_html = render_post_html(post, "../")
    with open(os.path.join(POSTS_HTML_DIR, f"{post['slug']}.html"), "w") as f:
        f.write(post_html)

    entries = load_index()
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
    for filename, html in render_indicator_pages(entries).items():
        with open(os.path.join(ROOT, filename), "w") as f:
            f.write(html)


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
    print(f"Rebuilt index.html and archive.html from {len(entries)} existing post(s), "
          f"plus {len(indicator_pages)} indicator page(s).")
