"""Version 2 homepage sections (markup only).

Every function takes already-computed data from build_site.render_index()
and returns an HTML string. Nothing here fetches or derives market data, so
the live-indicator pipeline is untouched by the redesign.
"""
import json
import re
from datetime import datetime
from html import escape

from partials import SITE_URL
import v2_ui as ui

try:  # Central time for the hero date line (the site's reader timezone)
    from zoneinfo import ZoneInfo
    CENTRAL = ZoneInfo("America/Chicago")
except Exception:  # pragma: no cover
    CENTRAL = None


def _strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "")


def hero(n_indicators):
    now = datetime.now(CENTRAL) if CENTRAL else datetime.now()
    date_line = now.strftime("%A, %B ") + str(now.day) + now.strftime(", %Y")
    return f"""<section class="v2-hero" aria-labelledby="home-title">
  <div class="v2-hero-bg" aria-hidden="true">{ui.candlesticks_svg()}</div>
  <div class="v2-hero-inner">
    <img class="v2-hero-mascot" src="assets/v2/crypto-playback-mascot-bitcoin-uncle-sam.webp" width="594" height="760" alt="The Crypto Playback mascot: Uncle Sam with Bitcoin glasses pointing at you" fetchpriority="high">
    <div class="v2-hero-copy">
      <h1 id="home-title" class="v2-hero-title"><img src="assets/v2/the-crypto-playback-logo.webp" width="1600" height="172" alt="The Crypto Playback"><span class="v2-sr">: daily Bitcoin and crypto market research</span></h1>
      <p class="v2-hero-tagline">Daily research and news on Bitcoin and digital assets</p>
      <p class="v2-hero-date">{date_line}</p>
      <div class="v2-hero-actions">
        <a class="v2-btn v2-btn-brass" href="#subscribe">Subscribe free</a>
        <a class="v2-btn v2-btn-ghost" href="#alerts">See the live indicators</a>
      </div>
      <ul class="v2-hero-facts">
        <li><strong>{n_indicators}</strong> live indicators</li>
        <li><strong>15 min</strong> data refresh</li>
        <li><strong>Mon&ndash;Sat</strong> free briefing</li>
      </ul>
    </div>
  </div>
</section>"""


def price_strip(prices, date_abbrev):
    cells = ""
    for c in prices:
        ch = c["change_24h"]
        cls = "up" if ch > 0.05 else ("down" if ch < -0.05 else "flat")
        arrow = "&#9650;" if cls == "up" else ("&#9660;" if cls == "down" else "&#9644;")
        cells += (f'<div class="v2-coin" data-coingecko-id="{c.get("id", "")}">'
                  f'<span class="v2-coin-sym">{c["symbol"]}</span>'
                  f'<span class="v2-coin-price">${c["price"]:,.2f}</span>'
                  f'<span class="v2-coin-change {cls}">{arrow} {abs(ch):.1f}%</span></div>')
    return f"""<section class="v2-strip" aria-label="Top {len(prices)} cryptocurrency prices">
  <div class="v2-wrap">
    <div class="v2-coins">{cells}</div>
    <p class="v2-strip-note" id="pulse-asof">Top {len(prices)} by market cap &middot; Prices via CoinGecko &middot; {date_abbrev}</p>
  </div>
</section>
{ui.LIVE_TICKER_SCRIPT}"""


def snapshot(fng, snapshot_text, total_count, date_abbrev):
    cls = fng["classification"]
    tone = "pos" if fng["value"] >= 55 else ("neg" if fng["value"] <= 45 else "neu")
    return f"""<section class="v2-section" id="snapshot" aria-labelledby="snapshot-h">
  <div class="v2-wrap">
    {ui.title_box("snapshot", '<span id="snapshot-h">Market Snapshot</span>', f"Updated {date_abbrev} &middot; {total_count} indicators")}
    <div class="v2-snapshot">
      <div class="v2-snapshot-gauge">
        {ui.gauge_svg(fng["value"], cls)}
        <div class="v2-snapshot-score">{fng["value"]}</div>
        <div class="v2-snapshot-label {tone}">{escape(cls)}</div>
        <div class="v2-snapshot-sub">Fear &amp; Greed Index</div>
      </div>
      <p class="v2-snapshot-text">{snapshot_text}</p>
    </div>
  </div>
</section>"""


def _confluence_cards(items):
    n = len(items)
    cards = ""
    for i, (name, pos, val) in enumerate(items):
        value, detail = ui.split_value(val)
        span = " v2-conf-wide" if (n % 4 == 1 and i == n - 1) else ""
        neg = " neg" if pos is False else ""
        cards += (f'<div class="v2-conf{neg}{span}"><div class="v2-conf-name">{name}</div>'
                  f'<div class="v2-conf-value">{value}</div>'
                  f'<div class="v2-conf-detail">{detail}</div>{ui.pill(pos)}</div>')
    return cards


def confluence_and_changed(items, positive_count, total_count, interpretation, change_items, date_abbrev):
    rows = ""
    for dot, headline, detail in change_items:
        tone = "up" if "128994" in dot else ("down" if "128308" in dot else "flat")
        rows += (f'<div class="v2-change"><div class="v2-change-name">{headline}</div>'
                 f'<div class="v2-change-detail {tone}">{detail}</div></div>')
    if not rows:
        rows = '<p class="v2-change-empty">Check back after the next update to see what has changed.</p>'
    return f"""<section class="v2-dark" id="confluence" aria-labelledby="confluence-h">
  <div class="v2-wrap">
    {ui.title_box("confluence", '<span id="confluence-h">Signal Confluence</span>', f"Updated {date_abbrev}", dark=True)}
    <div class="v2-conf-head">
      <div class="v2-conf-score">{positive_count}<span>/{total_count}</span></div>
      <p class="v2-conf-interp"><strong>signals positive.</strong> {interpretation}</p>
    </div>
    <div class="v2-conf-grid">{_confluence_cards(items)}</div>
    <p class="v2-fineprint">Each signal is a Crypto Playback reading of live market data. The Capital Flow score is a composite of
    price and sector breadth weighted against sentiment; it is not institutional transaction data.
    <a href="resources.html#signals">How we read the signals</a></p>
    <div class="v2-changed">
      {ui.title_box("changed", "What Changed", "vs. about 24 hours ago", dark=True)}
      <div class="v2-change-list">{rows}</div>
      <p class="v2-fineprint">Each indicator is compared with its own reading from about 24 hours earlier. Bitcoin ETF flow
      compares with the prior trading day because it only updates once a day.</p>
    </div>
  </div>
</section>"""


def _card_title(ind):
    return ui.strip_emoji(ind["card_label"])


def alerts(indicators, date_abbrev):
    cards = ""
    for ind in indicators:
        title = _card_title(ind)
        pos = ind.get("confluence_positive")
        cards += f"""<a class="v2-card" href="{ind['page']}">
      <span class="v2-card-head">{ui.icon(ind['id'], 20)}<span class="v2-card-title">{title}</span>{ui.pill(pos)}</span>
      <span class="v2-card-main">{ind['card_main_html']}</span>
      <span class="v2-card-caption">{ind['card_caption']}</span>
      <span class="v2-card-updated">Updated {ind['last_updated_display']}</span>
      <span class="v2-card-cta">View full breakdown &rarr;</span>
    </a>"""
    return f"""<section class="v2-alerts" id="alerts" aria-labelledby="alerts-h">
  <div class="v2-alerts-intro">
    <div class="v2-wrap">
      {ui.title_box("alerts", '<span id="alerts-h">Alerts &amp; Indicators</span>', f"Updated {date_abbrev}")}
      <p class="v2-lead">Sixteen live readings of crypto market mood, risk, flows and structure. Each card links to its full
      methodology, data source and recent history.</p>
    </div>
  </div>
  <div class="v2-alerts-grid-wrap"><div class="v2-wrap"><div class="v2-cards">{cards}</div></div></div>
</section>"""


def news(entries, teaser_image):
    seen, cards, count = set(), "", 0
    latest = None
    for e in entries:
        if e["slug"] in seen:
            continue
        seen.add(e["slug"])
        if latest is None:
            latest = e          # featured in the lede box above the list
            continue
        img_url = teaser_image(e["slug"]) if count % 2 == 0 else None
        img = (f'<img class="v2-story-img" src="{img_url}" alt="" loading="lazy" width="320" height="200">'
               if img_url else "")
        tile_icon = "calendar" if e.get("tag", "").lower() == "weekly" else "news"
        cards += f"""<article class="v2-story{' has-img' if img else ''}">
      <div class="v2-story-tile" aria-hidden="true">{ui.icon(tile_icon, 34)}</div>
      <div class="v2-story-body">
        <div class="v2-kicker">{e['tag']} playback &middot; {e['date_display']}</div>
        <h3 class="v2-story-title"><a href="posts/{e['slug']}.html">{e['title']}</a></h3>
        <p>{e['excerpt']}</p>
        <a class="v2-story-link" href="posts/{e['slug']}.html">Read the full playback &rarr;</a>
      </div>
      {img}
    </article>"""
        count += 1
        if count == 6:
            break
    lede = ""
    if latest:
        lede = f"""<div class="v2-lede">
      <div class="v2-lede-kicker">Latest playback &middot; {latest['date_display']}</div>
      <p class="v2-lede-title"><a href="posts/{latest['slug']}.html">{latest['title']}</a></p>
      <p class="v2-lede-text">{latest['excerpt']}</p>
    </div>"""
    return f"""<section class="v2-section v2-section-white" id="news" aria-labelledby="news-h">
  <div class="v2-wrap">
    {ui.title_box("news", '<span id="news-h">The Top News Stories</span>', "Refreshed and updated daily")}
    {lede}
    <div class="v2-stories">{cards}</div>
    <p class="v2-more"><a class="v2-btn v2-btn-navy" href="archive.html">Browse the full archive</a></p>
  </div>
</section>"""


def subscribe():
    return """<section class="v2-subscribe" id="subscribe" aria-labelledby="subscribe-h">
  <div class="v2-subscribe-inner">
    <img class="v2-subscribe-mascot" src="assets/v2/crypto-playback-mascot-bitcoin-uncle-sam.webp" width="594" height="760" alt="The Crypto Playback mascot inviting you to subscribe" loading="lazy">
    <div class="v2-subscribe-copy">
      <div class="v2-kicker v2-kicker-brass">Join The Playback</div>
      <h2 id="subscribe-h">Subscribe for free and don't miss another top story</h2>
      <p>One concise briefing every morning: live market signals, what changed overnight, and the stories that matter
      for Bitcoin and digital assets. Subscribe now and automatically unlock <strong>VIP OG status</strong>.</p>
      <form class="v2-form" action="https://buttondown.com/api/emails/embed-subscribe/cryptoplayback" method="post" target="popupwindow" onsubmit="window.open('https://buttondown.com/cryptoplayback', 'popupwindow')">
        <label class="v2-sr" for="sub-name">First name</label>
        <input id="sub-name" type="text" name="metadata__first_name" placeholder="First name" autocomplete="given-name" required>
        <label class="v2-sr" for="sub-email">Email address</label>
        <input id="sub-email" type="email" name="email" placeholder="Email address" autocomplete="email" required>
        <button type="submit" class="v2-btn v2-btn-brass">Subscribe</button>
      </form>
      <p class="v2-fine-light">Free (for now). Unsubscribe anytime. No spam. We don't share your info.</p>
    </div>
  </div>
</section>"""


def decode(indicators):
    cards = ""
    for ind in indicators:
        title = ind["page_title"]
        cards += f"""<article class="v2-decode">
      <div class="v2-decode-tile" aria-hidden="true">{ui.icon(ind['id'], 30)}</div>
      <div>
        <h3><a href="{ind['page']}">{title}</a></h3>
        <p>{ind['explainer_text']}</p>
      </div>
    </article>"""
    return f"""<section class="v2-section" id="decode" aria-labelledby="decode-h">
  <div class="v2-wrap">
    {ui.title_box("book", '<span id="decode-h">Decode The Dashboard</span>', "What every signal measures")}
    <p class="v2-lead">What each alert above actually measures, and how it is calculated. Tap any signal name for the full
    methodology, data sources and history.</p>
    <div class="v2-decode-grid">{cards}</div>
  </div>
</section>"""


def jsonld(indicators):
    """Organization + WebSite for search engines, plus an FAQPage built from
    the visible 'Decode The Dashboard' explanations (same text a visitor
    reads on the page, so the markup is truthful)."""
    faq = []
    for ind in indicators:
        q = f"What is the {_strip_tags(ind['page_title']).replace('&amp;', '&')}?"
        a = _strip_tags(ind["explainer_text"]).replace("&amp;", "&").replace("&ndash;", "-").replace("&mdash;", "-")
        faq.append({"@type": "Question", "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": a}})
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Organization", "@id": f"{SITE_URL}/#org", "name": "The Crypto Playback", "url": SITE_URL + "/",
             "logo": f"{SITE_URL}/assets/v2/the-crypto-playback-badge.webp", "email": "info@cryptoplayback.com"},
            {"@type": "WebSite", "@id": f"{SITE_URL}/#site", "url": SITE_URL + "/", "name": "The Crypto Playback",
             "description": "Free daily Bitcoin and crypto market research with 16 live indicators.",
             "publisher": {"@id": f"{SITE_URL}/#org"}, "inLanguage": "en-US"},
            {"@type": "FAQPage", "mainEntity": faq},
        ],
    }
    return json.dumps(data, ensure_ascii=False)


def indicator_footer_links(indicators):
    return "".join(f'<li><a href="{{root}}{ind["page"]}">{ind["page_title"]}</a></li>' for ind in indicators)
