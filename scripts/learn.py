"""Plain-English explainer pages ("Learn"): evergreen answers to questions people search, each linking to the live indicator.

Content is original and describes how a measure works, never what price will do. Add a page by appending to PAGES;
build_site.py writes learn/<slug>.html on every build and seo.py lists them in the sitemap.
"""
import json
import os
from datetime import datetime
from html import escape

from partials import page, SITE_URL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = "learn"
PUBLISHED = "2026-11-24"

PAGES = [
    {
        "slug": "bitcoin-funding-rate",
        "title": "What Is the Bitcoin Funding Rate? A Plain-English Guide",
        "seo_title": "What Is the Bitcoin Funding Rate? Plain-English Guide",
        "desc": "What the Bitcoin funding rate is, why longs and shorts pay each other, what positive and negative rates mean, and how to read them. Includes a live reading.",
        "kicker": "Learn · Derivatives",
        "intro": "The Bitcoin funding rate is a small payment that traders on one side of a perpetual futures contract make to the other side. It is one of the quickest ways to see whether the market is crowded on the long side or the short side.",
        "indicator": ("leverage-heat.html", "See today's live funding rate on the Leverage Heat page"),
        "sections": [
            ("What is a perpetual future?",
             "<p>A perpetual future is a Bitcoin contract with no expiry date. Traders use it to bet on the price going up (going long) or down (going short), usually with borrowed money, which is called leverage. Because the contract never expires, there has to be something that keeps its price close to the real Bitcoin price. That something is the funding rate.</p>"),
            ("How the funding rate works",
             "<p>At regular intervals, often every eight hours, the exchange works out the gap between the perpetual contract's price and the spot price of Bitcoin. If the contract trades above spot, traders holding longs pay traders holding shorts. If it trades below spot, shorts pay longs. The exchange itself does not keep the payment; it passes between traders.</p>"
             "<p>The payment pulls the contract price back toward spot. Paying to hold a position makes crowded trades more expensive, which nudges traders to close them.</p>"),
            ("What a positive or negative rate means",
             "<ul><li><strong>Positive rate:</strong> longs pay shorts. More traders are leaning long, and they are willing to pay for that position.</li>"
             "<li><strong>Negative rate:</strong> shorts pay longs. More traders are leaning short.</li>"
             "<li><strong>Near zero:</strong> positioning is roughly balanced.</li></ul>"
             "<p>Many exchanges use a small positive baseline, so a rate a little above zero is common and not unusual by itself.</p>"),
            ("Why a high funding rate matters",
             "<p>When the rate is far from normal in either direction, one side of the market is crowded with leverage. Leveraged traders get force-closed (liquidated) if price moves against them, and a wave of liquidations can push price further and faster. That is why a very high or very low rate is often read as a warning about fragile positioning.</p>"
             "<p>It does not tell you which way price will go. Crowded trades can stay crowded for a long time, and the rate can stay high while price keeps moving the same way.</p>"),
            ("How we show it",
             "<p>The Crypto Playback reads the funding rate for Bitcoin's perpetual swap on OKX and refreshes it every 15 minutes. We label it Balanced, Elevated or Extreme, in either the long or short direction, and track its recent history. In Signal Confluence, crowded leverage on either side counts as a caution, because it raises the risk of a forced move in both directions.</p>"),
        ],
        "faq": [
            ("Is a positive funding rate bullish?", "Not necessarily. A positive rate means longs are paying shorts, which shows traders are leaning long. It describes positioning, not where price goes next, and very high positive rates can signal a crowded trade that is vulnerable to a sharp reversal."),
            ("How often is the funding rate paid?", "On most major exchanges it is settled every eight hours, though some use shorter intervals. The rate shown is for one interval, not per day."),
            ("What is a normal funding rate?", "A small positive number close to zero is typical on many exchanges. What counts as unusual depends on the exchange, so it helps to compare today's rate with its own recent history."),
            ("Who receives the funding payment?", "The traders on the other side of the contract. The exchange does not keep it."),
        ],
        "related": ["liquidations.html", "stablecoin-liquidity.html", "fear-greed-index.html"],
    },
]

NAMES = {"liquidations.html": "Liquidations", "stablecoin-liquidity.html": "Stablecoin Liquidity", "fear-greed-index.html": "Fear &amp; Greed Index",
         "leverage-heat.html": "Leverage Heat", "market-breadth.html": "Market Breadth", "macro-risk.html": "Macro Risk"}


def paths():
    return [f"{DIR}/{p['slug']}.html" for p in PAGES]


def render(p):
    root = "../"
    cards = "".join(f'<article class="v2-ind-card"><h2>{h}</h2>{b}</article>' for h, b in p["sections"])
    faq = "".join(f'<article class="v2-ind-card"><h3>{escape(q)}</h3><p>{escape(a)}</p></article>' for q, a in p["faq"])
    href, label = p["indicator"]
    live = f'<a class="v2-ind-lab" href="{root}{href}"><span>Live data</span><strong>{label}</strong><em>&rarr;</em></a>'
    chips = "".join(f'<a href="{root}{h}">{NAMES.get(h, h)}</a>' for h in p["related"])
    body = f"""<section class="v2-ind-hero" aria-labelledby="learn-h">
  <div class="v2-wrap">
    <nav class="v2-crumbs" aria-label="Breadcrumb"><a href="{root}index.html">Home</a><span aria-hidden="true">›</span><a href="{root}resources.html">Learn</a><span aria-hidden="true">›</span><span aria-current="page">{escape(p['seo_title'].split('?')[0])}</span></nav>
    <div class="v2-kicker v2-kicker-brass v2-ind-kicker">{p['kicker']}</div>
    <h1 class="v2-ind-title" id="learn-h">{escape(p['title'])}</h1>
    <p class="v2-arch-sub">{p['intro']}</p>
  </div>
</section>
<section class="v2-section v2-ind-body">
  <div class="v2-wrap">
    {live}
    <div class="v2-ind-grid v2-learn-grid">{cards}</div>
    <section class="v2-ind-faq" aria-labelledby="faq-h"><h2 id="faq-h">Common questions</h2><div class="v2-ind-grid">{faq}</div></section>
    <section class="v2-ind-related" aria-labelledby="rel-h"><h2 id="rel-h">Related live indicators</h2><div class="v2-ind-chips">{chips}</div></section>
    <p class="v2-about-note">This is education, not financial advice.</p>
    <p class="v2-ind-sub"><a class="v2-btn v2-btn-navy" href="{root}index.html#subscribe">Get the Playback free</a></p>
  </div>
</section>"""
    url = f"{SITE_URL}/{DIR}/{p['slug']}.html"
    ld = [{"@context": "https://schema.org", "@type": ["Article", "TechArticle"], "headline": p["title"], "description": p["desc"],
           "datePublished": PUBLISHED, "dateModified": PUBLISHED, "mainEntityOfPage": url,
           "author": {"@type": "Organization", "name": "The Crypto Playback"},
           "publisher": {"@type": "Organization", "name": "The Crypto Playback", "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/assets/v2/apple-touch-icon.png"}}},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
              {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in p["faq"]]},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
              {"@type": "ListItem", "position": 2, "name": p["seo_title"].split("?")[0], "item": url}]}]
    ldj = '</script><script type="application/ld+json">'.join(json.dumps(x, separators=(",", ":")) for x in ld)
    return page(root, f"{p['seo_title']} | The Crypto Playback", body, datetime.now().year, theme="v2",
                description=p["desc"], path=f"{DIR}/{p['slug']}.html", og_type="article", jsonld=ldj)


def build():
    os.makedirs(os.path.join(ROOT, DIR), exist_ok=True)
    for p in PAGES:
        with open(os.path.join(ROOT, DIR, f"{p['slug']}.html"), "w") as f:
            f.write(render(p))
    return len(PAGES)
