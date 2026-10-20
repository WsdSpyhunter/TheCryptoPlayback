"""Version 2 issue (post) pages (markup only).

build_site.render_post_html() calls render() with the saved post dict plus the market numbers
recovered by build_site._market_data_from_post(), and the archive entries for prev/next links.
"""
import json
import re
from datetime import datetime
from html import escape

import issue_label
from partials import page, SITE_URL
from home_v2 import missed_card
from email_v3 import categorize

# Story category -> our own pages that give context (label, page, one-line description), used for the "Related research" box.
RELATED = {
    "Flows": [("Bitcoin ETF Flow", "etf-flow.html", "Daily net flows into US spot Bitcoin ETFs"),
              ("Institutional Positioning Index", "playback-lab.html#pressure", "CME futures, ETF flows and on-chain funding in one read"),
              ("Basis-Trade Crowding", "playback-lab.html#basis", "How crowded the ETF-versus-futures trade is")],
    "Security": [("Risk Radar", "risk-radar.html", "A simple read on market volatility and sentiment risk"),
                 ("Liquidations", "liquidations.html", "Forced closeouts in Bitcoin futures markets")],
    "Stablecoins": [("Stablecoin Liquidity", "stablecoin-liquidity.html", "Total stablecoin supply and its 7-day change"),
                    ("Stablecoin Flows", "playback-lab.html#stables", "Supply, minting and burning read straight from the blockchains")],
    "Corporate Treasuries": [("Whale Activity", "whale-activity.html", "Large Bitcoin transfers on the network"),
                             ("Institutional Positioning Index", "playback-lab.html#pressure", "Where big, regulated players are positioned")],
    "Policy": [("Regulatory & ETF-Pipeline Tracker", "playback-lab.html#reg", "Federal Register and SEC filings in one place"),
               ("Macro Risk", "macro-risk.html", "Equity volatility and the dollar as a macro temperature check")],
    "Market Infrastructure": [("Regulatory & ETF-Pipeline Tracker", "playback-lab.html#reg", "Federal Register and SEC filings in one place"),
                              ("DeFi Pulse", "defi-pulse.html", "Total value locked across DeFi protocols")],
    "Network": [("Miner Health", "network-health.html", "Bitcoin hash rate and network health"),
                ("Miner Stress", "playback-lab.html#miners", "Hashprice, hash ribbons and miner margins")],
    "News": [("Fear & Greed Index", "fear-greed-index.html", "A 0-100 read on overall market mood"),
             ("Risk Radar", "risk-radar.html", "A simple read on market volatility and sentiment risk")],
}
ALWAYS = [("The Playback Read", "playback-lab.html#read", "A simple tally of the Lab's readings: supportive, neutral or caution"),
          ("Net Liquidity & Macro Sensitivity", "playback-lab.html#liquidity", "Fed liquidity, real yields and the dollar, and how Bitcoin has reacted")]


def related_research(post, root):
    """Links from this issue to the live indicators and Lab sections that match its stories (deduplicated, at most 6)."""
    items = list(post["stories"]) + ([post["missed_story"]] if isinstance(post.get("missed_story"), dict) and post["missed_story"].get("headline") else [])
    counts = {}
    for it in items:
        cat = categorize(_plain(it["headline"]), _plain(it.get("body", "")))[0]
        counts[cat] = counts.get(cat, 0) + 1
    picks, seen = [ALWAYS[0]], {ALWAYS[0][1]}
    for cat, _ in sorted(counts.items(), key=lambda kv: -kv[1]):
        for entry in RELATED.get(cat, []):
            if entry[1] not in seen and len(picks) < 5:
                picks.append(entry); seen.add(entry[1])
    if ALWAYS[1][1] not in seen:
        picks.append(ALWAYS[1])
    cards = "".join(f'<a class="v2-rel-card" href="{root}{href}"><strong>{label}</strong><span>{desc}</span></a>' for label, href, desc in picks[:6])
    return (f'<section class="v2-post-related" aria-labelledby="rel-h"><h2 id="rel-h">Related research</h2>'
            f'<p>Live indicators and Playback Lab research connected to this issue&rsquo;s stories.</p><div class="v2-rel-grid">{cards}</div></section>')


def _plain(s):
    t = re.sub(r"<[^>]+>", "", s or "")
    for a, b in (("&amp;", "&"), ("&ndash;", "-"), ("&mdash;", "-"), ("&rsquo;", "'"), ("&#39;", "'"), ("&nbsp;", " ")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def _fmt_price(p):
    return f"${p:,.2f}" if p < 1000 else f"${p:,.0f}"


def render(post, root, market, entries, footer_links=""):
    prices, fng, mover = market
    slug = post["slug"]
    tag = post.get("tag", "Daily")
    issue = post.get("issue_number")
    m = re.search(r'top-story-text">(.*?)</p>', post.get("top_story_html", ""), re.S)
    lede = m.group(1).strip() if m else post.get("excerpt", "")
    if lede and lede.rstrip()[-1] not in ".!?\"'”’)":
        lede = lede.rstrip() + "…"
    date_iso = slug[:10]

    chips = ""
    for p in prices[:6]:
        ch = p["change_24h"]
        cls = "up" if ch >= 0 else "down"
        chips += (f'<span class="v2-post-chip"><b>{escape(p["symbol"])}</b><span>{_fmt_price(p["price"])}</span>'
                  f'<i class="{cls}">{ch:+.1f}%</i></span>')
    mood = ""
    if fng and fng.get("value"):
        mood = f'<span class="v2-post-chip v2-post-mood"><b>Fear &amp; Greed</b><span>{fng["value"]}</span><i>{escape(str(fng["classification"]))}</i></span>'
    strip = (f'<section class="v2-post-strip" aria-label="Market at the open"><div class="v2-wrap"><div class="v2-post-chips">{chips}</div>{f'<div class="v2-post-chips v2-post-moodline">{mood}</div>' if mood else ""}'
             f'<p>Prices as of 6 AM CT on the issue date. <a href="{root}index.html#alerts">See live indicators</a></p></div></section>') if chips else ""

    stories = ""
    for s in post["stories"]:
        img = (f'<img class="v2-post-img" src="{s["image_url"]}" alt="{escape(_plain(s["headline"]), quote=True)}" loading="lazy">'
               if s.get("image_url") else "")
        qt = (f'<blockquote class="v2-post-quote"><p>&ldquo;{escape(s["quote"]["text"], quote=False)}&rdquo;</p>'
              f'<footer>&mdash; {escape(s["quote"]["speaker"], quote=False)}, {escape(s["quote"]["role"], quote=False)}</footer></blockquote>') if s.get("quote") else ""
        stories += (f'<article class="v2-post-story">{img}<h2>{s["headline"]}</h2>{qt}{s["body"]}'
                    f'<a class="v2-post-src" href="{s["source_url"]}" target="_blank" rel="noopener">Read more at {s["source_title"]} &rarr;</a></article>')

    # prev / next issue (entries are newest first)
    idx = next((i for i, e in enumerate(entries) if e["slug"] == slug), None)
    nav = ""
    if idx is not None:
        newer = entries[idx - 1] if idx > 0 else None
        older = entries[idx + 1] if idx + 1 < len(entries) else None
        a = (f'<a class="v2-post-nav-a" href="{older["slug"]}.html"><span>&larr; Previous issue</span><strong>{older["title"]}</strong></a>' if older else "<span></span>")
        b = (f'<a class="v2-post-nav-a v2-post-nav-r" href="{newer["slug"]}.html"><span>Next issue &rarr;</span><strong>{newer["title"]}</strong></a>' if newer else "<span></span>")
        nav = f'<nav class="v2-post-nav" aria-label="More issues">{a}{b}</nav>'

    ed = issue_label.edition(tag)
    kicker = f'Your Crypto Playback for <time datetime="{date_iso}">{issue_label.weekday_date(slug)}</time>' + (f' · {ed}' if ed else "")
    body = f"""<section class="v2-ind-hero v2-post-hero" aria-labelledby="post-h">
  <div class="v2-wrap">
    <nav class="v2-crumbs" aria-label="Breadcrumb"><a href="{root}index.html">Home</a><span aria-hidden="true">›</span><a href="{root}archive.html">Archive</a><span aria-hidden="true">›</span><span aria-current="page">{post['date_display']}</span></nav>
    <div class="v2-kicker v2-kicker-brass v2-ind-kicker">{kicker}</div>
    <h1 class="v2-ind-title v2-post-title" id="post-h">{post['title']}</h1>
  </div>
</section>
{strip}
<section class="v2-section v2-ind-body v2-post-body">
  <div class="v2-wrap v2-post-wrap">
    <div class="v2-post-lede"><span>Top story</span><p>{lede}</p></div>
    {missed_card(post["missed_story"], root, "v2-news-missed") if isinstance(post.get("missed_story"), dict) and post["missed_story"].get("headline") else ""}
    {stories}
    {related_research(post, root)}
    <p class="v2-ind-sub"><a class="v2-btn v2-btn-navy" href="{root}index.html#subscribe">Get the Playback free</a></p>
    {nav}
  </div>
</section>"""
    plain_title = _plain(post["title"])
    first_img = next((s["image_url"] for s in post["stories"] if s.get("image_url")), None)
    ld = [{"@context": "https://schema.org", "@type": "NewsArticle", "headline": plain_title, "datePublished": date_iso, "dateModified": date_iso, "articleSection": "Bitcoin and crypto markets",
           "description": _plain(post.get("excerpt", lede)),
           "image": [first_img if (first_img and first_img.startswith("http")) else f"{SITE_URL}/assets/v2/the-crypto-playback-share-card.png"],
           "author": {"@type": "Organization", "name": "The Crypto Playback"},
           "publisher": {"@type": "Organization", "name": "The Crypto Playback", "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/assets/v2/apple-touch-icon.png"}},
           "mainEntityOfPage": f"{SITE_URL}/posts/{slug}.html"},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
              {"@type": "ListItem", "position": 2, "name": "Archive", "item": f"{SITE_URL}/archive.html"},
              {"@type": "ListItem", "position": 3, "name": plain_title, "item": f"{SITE_URL}/posts/{slug}.html"}]}]
    dt = datetime.strptime(date_iso, "%Y-%m-%d")
    seo_title = f"{plain_title}: Bitcoin & Crypto Briefing, {dt.strftime('%b')} {dt.day}, {dt.year} | The Crypto Playback"
    return page(root, seo_title, body, datetime.now().year, theme="v2", indicator_links=footer_links,
                description=_plain(post.get("excerpt", lede))[:158], path=f"posts/{slug}.html", og_type="article",
                jsonld=json.dumps(ld, separators=(",", ":")))
