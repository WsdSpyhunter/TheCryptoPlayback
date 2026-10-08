"""Search-engine and discovery files, regenerated on every site build:
sitemap.xml, robots.txt, feed.xml (RSS), llms.txt and the 404 page.

Called from build_site (full rebuild, publish) and refresh_indicators (every
15 minutes), so a new issue is in the sitemap and feed as soon as it is posted.
"""
import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape

from partials import SITE_URL, page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_LASTMOD = datetime(2026, 10, 7, tzinfo=timezone.utc)  # bump when about/resources copy changes
STATIC_PAGES = [  # (path, changefreq, priority)
    ("", "hourly", "1.0"),
    ("institutional.html", "hourly", "0.9"),
    ("archive.html", "daily", "0.8"),
    ("resources.html", "monthly", "0.7"),
    ("about.html", "monthly", "0.5"),
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
        lm = now if path in ("", "institutional.html") else (latest_post if path == "archive.html" else STATIC_LASTMOD)
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
            "<description>Daily research and news on Bitcoin and digital assets, with 16 live market indicators.</description>\n"
            "<language>en-us</language>\n"
            f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>\n"
            f'<atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>\n'
            + items + "</channel>\n</rss>\n")


def llms_txt(indicators):
    lines = "\n".join(f"- [{re.sub('<[^>]+>', '', i['page_title']).replace('&amp;', '&')}]({SITE_URL}/{i['page']})"
                      for i in indicators)
    return f"""# The Crypto Playback

> Free daily Bitcoin and crypto market research. A live dashboard of 16 market indicators (sentiment, risk, ETF flows,
> stablecoin liquidity, leverage, on-chain activity and more), refreshed every 15 minutes, plus a concise newsletter
> published Monday through Saturday. Not financial advice.

## Main pages
- [Home and live dashboard]({SITE_URL}/)
- [Institutional indicators (pressure index, crowded unwind risk, protocol revenue/TVL quality, stablecoin flows)]({SITE_URL}/institutional.html)
- [Newsletter archive]({SITE_URL}/archive.html)
- [Resources and glossary]({SITE_URL}/resources.html)
- [About]({SITE_URL}/about.html)
- [RSS feed]({SITE_URL}/feed.xml)

## Live indicators (each page explains what it measures, how it is calculated and its data source)
{lines}
"""


def not_found_html(indicators, year):
    links = "".join(f'<li><a href="/{i["page"]}">{i["page_title"]}</a></li>' for i in indicators)
    body = f"""<section class="v2-section v2-section-white"><div class="v2-wrap">
  <h1 class="v2-lead" style="font-family:var(--f-head);font-size:34px;font-weight:700">That page isn't on the board</h1>
  <p class="v2-lead">The page you were looking for has moved or doesn't exist. Try the live dashboard, the archive,
  or one of the indicators below.</p>
  <p><a class="v2-btn v2-btn-navy" href="/">Back to the live dashboard</a></p>
  <ul>{links}</ul></div></section>"""
    return page("/", "Page not found | The Crypto Playback", body, year, theme="v2", path="404.html", noindex=True)


def write_seo_files(entries, indicators, indicator_files, updated=None):
    def w(name, text):
        with open(os.path.join(ROOT, name), "w") as f:
            f.write(text)
    w("sitemap.xml", sitemap_xml(entries, indicator_files, updated))
    w("robots.txt", robots_txt())
    w("feed.xml", feed_xml(entries))
    w("llms.txt", llms_txt(indicators))
    w("404.html", not_found_html(indicators, datetime.now().year))
