"""Search-engine and discovery files, regenerated on every site build:
sitemap.xml, sitemap.html (for visitors), robots.txt, feed.xml (RSS), llms.txt and the 404 page.

Called from build_site (full rebuild, publish) and refresh_indicators (every
15 minutes), so a new issue is in the sitemap and feed as soon as it is posted.
"""
import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape

import issue_label
from partials import SITE_URL, page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_LASTMOD = datetime(2026, 10, 7, tzinfo=timezone.utc)  # bump when about/resources copy changes
STATIC_PAGES = [  # (path, changefreq, priority)
    ("", "hourly", "1.0"),
    ("playback-lab.html", "hourly", "0.9"),
    ("archive.html", "daily", "0.8"),
    ("resources.html", "monthly", "0.7"),
    ("about.html", "monthly", "0.5"),
    ("terms.html", "yearly", "0.3"),
    ("sitemap.html", "daily", "0.3"),
]


def _slug_date(slug):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", slug)
    if not m:
        return None
    return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 12, 0, tzinfo=timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def sitemap_xml(entries, indicator_files, updated=None):
    now = updated or datetime.now(timezone.utc)
    urls = []
    latest_post = next((_slug_date(e["slug"]) for e in entries if _slug_date(e["slug"])), now)
    for path, freq, prio in STATIC_PAGES:
        lm = now if path in ("", "playback-lab.html") else (latest_post if path in ("archive.html", "sitemap.html") else STATIC_LASTMOD)
        urls.append((f"{SITE_URL}/{path}", _iso(lm), freq, prio))
    for fn in sorted(indicator_files):
        urls.append((f"{SITE_URL}/{fn}", _iso(now), "hourly", "0.9"))
    seen = set()
    for e in entries:
        if e["slug"] in seen:
            continue
        seen.add(e["slug"])
        d = _slug_date(e["slug"]) or now
        urls.append((f"{SITE_URL}/posts/{e['slug']}.html", _iso(d), "never", "0.8"))
    body = "".join(
        f"<url><loc>{escape(u)}</loc><lastmod>{lm}</lastmod><changefreq>{cf}</changefreq><priority>{pr}</priority></url>\n"
        for u, lm, cf, pr in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")


def robots_txt():
    return f"""User-agent: *
Allow: /
Disallow: /go/
Disallow: /docs/

Sitemap: {SITE_URL}/sitemap.xml
"""


def feed_xml(entries, limit=20):
    now = datetime.now(timezone.utc)
    items, seen = "", set()
    for e in entries:
        if e["slug"] in seen:
            continue
        seen.add(e["slug"])
        d = _slug_date(e["slug"]) or now
        url = f"{SITE_URL}/posts/{e['slug']}.html"
        items += (f"<item><title>{escape(e['title'])}</title><link>{url}</link>"
                  f"<guid isPermaLink=\"true\">{url}</guid><pubDate>{format_datetime(d)}</pubDate>"
                  f"<category>{escape(e.get('tag', ''))}</category>"
                  f"<description>{escape(e.get('excerpt', ''))}</description></item>\n")
        if len(seen) >= limit:
            break
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n'
            "<title>The Crypto Playback</title>\n"
            f"<link>{SITE_URL}/</link>\n"
            "<description>Daily research and news on Bitcoin and digital assets, with 24 live market indicators.</description>\n"
            "<language>en-us</language>\n"
            f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>\n"
            f'<atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>\n'
            + items + "</channel>\n</rss>\n")


def llms_txt(indicators):
    lines = "\n".join(f"- [{re.sub('<[^>]+>', '', i['page_title']).replace('&amp;', '&')}]({SITE_URL}/{i['page']})"
                      for i in indicators)
    return f"""# The Crypto Playback

> Free Bitcoin and crypto market research, four issues a week. A live dashboard of 16 market indicators (sentiment, risk, ETF flows,
> stablecoin liquidity, leverage, on-chain activity and more) refreshed every 15 minutes, plus 8 Playback Lab indicators
> (Bitcoin trend, institutional positioning, miner stress, net liquidity and more) refreshed every 2 hours, and a concise newsletter
> published Monday, Wednesday, Friday and Saturday. Not financial advice.

## Main pages
- [Home and live dashboard]({SITE_URL}/)
- [The Crypto Playback Lab: market-structure indicators (institutional positioning, on-chain crowded unwind risk, stablecoin flows)]({SITE_URL}/playback-lab.html)
- [Newsletter archive]({SITE_URL}/archive.html)
- [Resources and glossary]({SITE_URL}/resources.html)
- [About]({SITE_URL}/about.html)
- [RSS feed]({SITE_URL}/feed.xml)

## Live indicators (each page explains what it measures, how it is calculated and its data source)
{lines}
"""


LAB_SECTIONS = [("trend", "Bitcoin Trend & Volatility"), ("pressure", "Institutional Positioning"), ("basis", "Basis-Trade Crowding"),
                ("reg", "Regulatory & ETF Pipeline"), ("miners", "Miner Stress"), ("liquidity", "Net Liquidity & Macro"),
                ("unwind", "Crowded Unwind Risk"), ("stables", "Stablecoin Flows"), ("sources", "Methodology & Data Sources")]


def _plain(t):
    return re.sub(r"<[^>]+>", "", t or "").replace("&amp;", "&")


def not_found_html(indicators, year):
    chips = "".join(f'<a href="/{i["page"]}">{_plain(i["page_title"])}</a>' for i in indicators)
    body = f"""<section class="v2-ind-hero" aria-labelledby="nf-h">
  <div class="v2-wrap">
    <div class="v2-kicker v2-kicker-brass v2-ind-kicker">Error 404</div>
    <h1 class="v2-ind-title" id="nf-h">That page isn&rsquo;t on the board</h1>
    <p class="v2-arch-sub">The page you were looking for has moved or doesn&rsquo;t exist. Here is where to go next.</p>
  </div>
</section>
<section class="v2-section v2-ind-body">
  <div class="v2-wrap" style="text-align:center">
    <p class="v2-ind-sub" style="display:flex;flex-wrap:wrap;gap:12px;justify-content:center">
      <a class="v2-btn v2-btn-navy" href="/">Live dashboard</a>
      <a class="v2-btn v2-btn-navy" href="/playback-lab.html">Playback Lab</a>
      <a class="v2-btn v2-btn-navy" href="/archive.html">Newsletter archive</a>
      <a class="v2-btn v2-btn-navy" href="/sitemap.html">Site map</a>
    </p>
    <section class="v2-ind-related" aria-labelledby="nf-ind-h"><h2 id="nf-ind-h" style="text-align:center">Live indicators</h2><div class="v2-ind-chips" style="justify-content:center">{chips}</div></section>
  </div>
</section>"""
    return page("/", "Page not found | The Crypto Playback", body, year, theme="v2", path="404.html", noindex=True)


def sitemap_html(entries, indicators, year):
    """A human-readable site map (the XML sitemap is for search engines)."""
    def block(title, links):
        return (f'<section class="v2-ind-related"><h2>{title}</h2><ul class="v2-sitemap-list">'
                + "".join(f'<li><a href="{h}">{escape(t)}</a></li>' for h, t in links) + "</ul></section>")
    main = [("index.html", "Home: live dashboard"), ("playback-lab.html", "The Playback Lab"), ("archive.html", "Newsletter archive"),
            ("resources.html", "Resources"), ("about.html", "About"), ("terms.html", "Terms of Use"), ("index.html#subscribe", "Subscribe free"),
            ("feed.xml", "RSS feed")]
    lab = [(f"playback-lab.html#{a}", t) for a, t in LAB_SECTIONS]
    ind = [(i["page"], _plain(i["page_title"])) for i in indicators]
    seen, posts = set(), []
    for e in entries:
        if e["slug"] in seen:
            continue
        seen.add(e["slug"])
        posts.append((f"posts/{e['slug']}.html", f"{(issue_label.edition(e['tag']) + ' · ') if issue_label.edition(e['tag']) else ''}{issue_label.weekday_date(e['slug'])}: {_plain(e['title'])}"))
    body = f"""<section class="v2-ind-hero" aria-labelledby="sm-h">
  <div class="v2-wrap">
    <nav class="v2-crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a><span aria-hidden="true">›</span><span aria-current="page">Site map</span></nav>
    <div class="v2-kicker v2-kicker-brass v2-ind-kicker">Every page, one place</div>
    <h1 class="v2-ind-title" id="sm-h">Site Map</h1>
    <p class="v2-arch-sub">Everything on The Crypto Playback: the main pages, the Playback Lab, every live indicator and every newsletter issue.</p>
  </div>
</section>
<section class="v2-section v2-ind-body"><div class="v2-wrap v2-sitemap">
  {block("Main pages", main)}{block("Playback Lab", lab)}{block("Live indicators", ind)}{block("Newsletter issues", posts)}
</div></section>"""
    return page("", "Site Map | The Crypto Playback", body, year, theme="v2",
                description="Every page on The Crypto Playback: the live dashboard, Playback Lab, all live indicators and every newsletter issue.",
                path="sitemap.html")


def write_seo_files(entries, indicators, indicator_files, updated=None):
    def w(name, text):
        with open(os.path.join(ROOT, name), "w") as f:
            f.write(text)
    w("sitemap.xml", sitemap_xml(entries, indicator_files, updated))
    w("robots.txt", robots_txt())
    w("feed.xml", feed_xml(entries))
    w("llms.txt", llms_txt(indicators))
    w("404.html", not_found_html(indicators, datetime.now().year))
    w("sitemap.html", sitemap_html(entries, indicators, datetime.now().year))
