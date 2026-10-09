"""Version 2 issue (post) pages (markup only).

build_site.render_post_html() calls render() with the saved post dict plus the market numbers
recovered by build_site._market_data_from_post(), and the archive entries for prev/next links.
"""
import json
import re
from datetime import datetime
from html import escape

from partials import page, SITE_URL
from home_v2 import missed_card


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
    strip = (f'<section class="v2-post-strip" aria-label="Market at the open"><div class="v2-wrap"><div class="v2-post-chips">{chips}{mood}</div>'
             f'<p>Prices as of 6 AM CT on the issue date. <a href="{root}index.html#alerts">See live indicators</a></p></div></section>') if chips else ""

    stories = ""
    for s in post["stories"]:
        img = (f'<img class="v2-post-img" src="{s["image_url"]}" alt="{escape(_plain(s["headline"]), quote=True)}" loading="lazy">'
               if s.get("image_url") else "")
        stories += (f'<article class="v2-post-story">{img}<h2>{s["headline"]}</h2>{s["body"]}'
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

    kicker = f'{tag} issue' + (f' · Issue #{issue}' if issue else "")
    body = f"""<section class="v2-ind-hero v2-post-hero" aria-labelledby="post-h">
  <div class="v2-wrap">
    <nav class="v2-crumbs" aria-label="Breadcrumb"><a href="{root}index.html">Home</a><span aria-hidden="true">›</span><a href="{root}archive.html">Archive</a><span aria-hidden="true">›</span><span aria-current="page">{post['date_display']}</span></nav>
    <div class="v2-kicker v2-kicker-brass v2-ind-kicker">{kicker} · {post['date_display']}</div>
    <h1 class="v2-ind-title v2-post-title" id="post-h">{post['title']}</h1>
  </div>
</section>
{strip}
<section class="v2-section v2-ind-body v2-post-body">
  <div class="v2-wrap v2-post-wrap">
    <div class="v2-post-lede"><span>Top story</span><p>{lede}</p></div>
    {missed_card(post["missed_story"], root, "v2-news-missed") if isinstance(post.get("missed_story"), dict) and post["missed_story"].get("headline") else ""}
    {stories}
    <p class="v2-ind-sub"><a class="v2-btn v2-btn-navy" href="{root}index.html#subscribe">Get the daily playback free</a></p>
    {nav}
  </div>
</section>"""
    plain_title = _plain(post["title"])
    first_img = next((s["image_url"] for s in post["stories"] if s.get("image_url")), None)
    ld = [{"@context": "https://schema.org", "@type": "NewsArticle", "headline": plain_title, "datePublished": date_iso, "dateModified": date_iso,
           "description": _plain(post.get("excerpt", lede)),
           "image": [first_img if (first_img and first_img.startswith("http")) else f"{SITE_URL}/assets/v2/the-crypto-playback-share-card.png"],
           "author": {"@type": "Organization", "name": "The Crypto Playback"},
           "publisher": {"@type": "Organization", "name": "The Crypto Playback", "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/assets/v2/apple-touch-icon.png"}},
           "mainEntityOfPage": f"{SITE_URL}/posts/{slug}.html"},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
              {"@type": "ListItem", "position": 2, "name": "Archive", "item": f"{SITE_URL}/archive.html"},
              {"@type": "ListItem", "position": 3, "name": plain_title, "item": f"{SITE_URL}/posts/{slug}.html"}]}]
    return page(root, f"{plain_title} | The Crypto Playback", body, datetime.now().year, theme="v2", indicator_links=footer_links,
                description=_plain(post.get("excerpt", lede))[:158], path=f"posts/{slug}.html", og_type="article",
                jsonld=json.dumps(ld, separators=(",", ":")))
