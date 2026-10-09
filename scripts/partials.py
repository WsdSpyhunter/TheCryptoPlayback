"""Shared HTML fragments used across every generated/static page."""

import hashlib
from pathlib import Path


def asset_version(filename):
    # Cloudflare caches everything under assets/ for hours (max-age=14400),
    # so a plain href/src never picks up a fresh deploy on the live site
    # until that edge cache expires on its own - true for images just as
    # much as CSS. Hashing the file's contents into a ?v= query string
    # gives every real edit its own URL, which busts that cache immediately
    # instead of waiting out the TTL.
    path = Path(__file__).resolve().parent.parent / "assets" / filename
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()[:10]
    except OSError:
        return "0"


CSS_VERSION = asset_version("styles.css")
LOGO_VERSION = asset_version("logo-wordmark.png")
FOOTER_MASCOT_VERSION = asset_version("footer-mascot-web.png")

HEAD = """<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;700&family=Playfair+Display:ital,wght@0,700;1,400&family=Source+Sans+3:wght@400;600&family=Black+Ops+One&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/styles.css?v=""" + CSS_VERSION + """">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>%E2%82%BF</text></svg>">
"""

HEADER = """<header class="site-header">
  <div class="wrap">
    <a class="logo-link" href="{root}index.html">
      <img class="logo" src="{root}assets/logo-wordmark.png?v=""" + LOGO_VERSION + """" alt="The Crypto Playback">
    </a>
    <nav class="site-nav">
      <a href="{root}about.html">About</a>
      <a href="{root}index.html#subscribe">Subscribe</a>
      <a href="{root}archive.html">Archives</a>
      <a href="{root}resources.html">Resources</a>
    </nav>
  </div>
</header>
"""

DISCLAIMER = """<div class="disclaimer">
  <div class="wrap">
    <span class="disclaimer-label">Disclaimer</span>
    <strong>THE CRYPTO PLAYBACK IS NOT FINANCIAL ADVICE.</strong>
    The material in this newsletter has no regard to any specific investment objectives, financial situation,
    or particular needs of any reader. It is published solely for informational purposes and is not to be
    construed as a solicitation nor does it constitute advice, investment or otherwise. References made to
    third parties are based on information obtained from sources believed to be reliable but not guaranteed
    as being accurate. Readers should not regard it as a substitute for the exercise of their own judgment.
    Our comments are an expression of opinion. While we believe our statements to be true, they always depend
    on the reliability of our own credible sources. We recommend that you consult with a licensed, qualified
    investment advisor before making any investment decisions.
  </div>
</div>
"""

FOOTER = """<footer class="site-footer">
  <div class="wrap">
    <div class="footer-copy">&copy; {year} The Crypto Playback &middot; <a href="{root}about.html">Contact</a></div>
    <div class="footer-brand">
      <img class="footer-mascot" src="{root}assets/footer-mascot-web.png?v=""" + FOOTER_MASCOT_VERSION + """" alt="The Crypto Playback mascot &mdash; Bitcoin and crypto market newsletter">
      <img class="footer-logo" src="{root}assets/logo-wordmark.png?v=""" + LOGO_VERSION + """" alt="The Crypto Playback">
    </div>
  </div>
</footer>
"""


def page(root, title, body_html, year, theme="v1", **meta):
    """Wrap body_html in the full document shell. theme="v2" uses the new
    navy/brass/ivory shell (see page_v2); v1 pages keep the old one until
    they are migrated."""
    if theme == "v2":
        return page_v2(root, title, body_html, year, **meta)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<title>{title}</title>
{HEAD.format(root=root)}
</head>
<body>
{HEADER.format(root=root)}
{body_html}
{DISCLAIMER}
{FOOTER.format(root=root, year=year)}
</body>
</html>
"""


# ============================ Version 2 shell ============================
SITE_URL = "https://cryptoplayback.com"
V2_CSS_VERSION = asset_version("v2.css")
V2_FAVICON_VERSION = asset_version("v2/favicon.png")

V2_FONTS = ("https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600&"
            "family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;500;600&"
            "family=Libre+Franklin:wght@600;700&display=swap")

DEFAULT_DESCRIPTION = ("Free daily Bitcoin & crypto market research. 16 live indicators (Fear & Greed, ETF flows, stablecoin liquidity, risk) plus a morning newsletter.")

V2_NAV = [("Indicators", "index.html#alerts"), ("Playback Lab", "playback-lab.html"), ("Archive", "archive.html"),
          ("Resources", "resources.html"), ("About", "about.html")]


def head_v2(root, title, description=None, path="", og_image=None, jsonld=None, og_type="website", noindex=False, extra_head=""):
    """<head> contents for a v2 page: fonts, stylesheet, SEO + social tags."""
    from html import escape
    description = escape(description or DEFAULT_DESCRIPTION, quote=True)
    safe_title = escape(title, quote=True)
    url = f"{SITE_URL}/{path}" if path else f"{SITE_URL}/"
    image = og_image or f"{SITE_URL}/assets/v2/the-crypto-playback-share-card.png"
    robots = '<meta name="robots" content="noindex,follow">' if noindex else \
        '<meta name="robots" content="index,follow,max-image-preview:large">'
    ld = f'<script type="application/ld+json">{jsonld}</script>' if jsonld else ""
    return f"""<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
{robots}
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#0B1F3A">
<meta property="og:site_name" content="The Crypto Playback">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{safe_title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{safe_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{image}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{V2_FONTS}" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/v2.css?v={V2_CSS_VERSION}">
<link rel="icon" type="image/png" href="{root}assets/v2/favicon.png?v={V2_FAVICON_VERSION}">
<link rel="apple-touch-icon" href="{root}assets/v2/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="The Crypto Playback" href="{SITE_URL}/feed.xml">
{extra_head}
{ld}"""


def header_v2(root):
    links = "".join(f'<a href="{root}{href}">{label}</a>' for label, href in V2_NAV)
    return f"""<a class="v2-skip" href="#main">Skip to content</a>
<header class="v2-header">
  <div class="v2-header-inner">
    <a class="v2-brand" href="{root}index.html" aria-label="The Crypto Playback home">
      <img src="{root}assets/v2/the-crypto-playback-badge.webp" width="40" height="40" alt="">
      <img class="v2-brand-word" src="{root}assets/v2/the-crypto-playback-logo-small.webp" width="800" height="86" alt="The Crypto Playback">
    </a>
    <nav class="v2-nav" aria-label="Main">{links}</nav>
    <a class="v2-nav-cta" href="{root}index.html#subscribe">Subscribe free</a>
  </div>
</header>"""


def footer_v2(root, year, indicator_links=""):
    from html import escape  # noqa: F401
    return f"""<footer class="v2-footer">
  <div class="v2-footer-inner">
    <div class="v2-footer-brand">
      <img class="v2-footer-badge" src="{root}assets/v2/the-crypto-playback-badge.webp" width="64" height="64" alt="The Crypto Playback mascot badge" loading="lazy">
      <img class="v2-footer-word" src="{root}assets/v2/the-crypto-playback-logo-small.webp" width="800" height="86" alt="The Crypto Playback" loading="lazy">
    </div>
    <div class="v2-footer-cols">
      <div>
        <h2 class="v2-footer-h">Explore</h2>
        <ul>
          <li><a href="{root}index.html">Home</a></li>
          <li><a href="{root}playback-lab.html">Playback Lab</a></li>
          <li><a href="{root}archive.html">Newsletter archive</a></li>
          <li><a href="{root}resources.html">Resources</a></li>
          <li><a href="{root}about.html">About</a></li>
          <li><a href="{root}index.html#subscribe">Subscribe free</a></li>
        </ul>
      </div>
      <div class="v2-footer-ind">
        <h2 class="v2-footer-h">Live indicators</h2>
        <ul>{indicator_links}</ul>
      </div>
    </div>
    <p class="v2-footer-sources"><strong>Sources and timestamps.</strong> Prices: CoinGecko. Indicators: Crypto Playback composite
    methodology, refreshed automatically every 15 minutes. News: Decrypt, The Block, CoinDesk.</p>
    <hr class="v2-footer-rule">
    <p class="v2-footer-disclaimer"><strong>THE CRYPTO PLAYBACK IS NOT FINANCIAL ADVICE.</strong> The material in this newsletter
    has no regard to any specific investment objectives, financial situation, or particular needs of any reader. It is published
    solely for informational purposes and is not to be construed as a solicitation, nor does it constitute advice, investment or
    otherwise. References to third parties are based on information obtained from sources believed to be reliable but are not
    guaranteed as being accurate. Readers should not regard it as a substitute for the exercise of their own judgment. Our comments
    are an expression of opinion. While we believe our statements to be true, they always depend on the reliability of our own
    credible sources. We recommend that you consult a licensed, qualified investment advisor before making any investment decisions.</p>
    <div class="v2-footer-base">
      <span>&copy; {year} The Crypto Playback&trade;. All rights reserved. &middot; <a href="mailto:info@cryptoplayback.com">info@cryptoplayback.com</a></span>
      <span><a href="{root}terms.html">Terms of Use</a> &middot; <a href="{root}index.html#subscribe">Subscribe</a> &middot; <a href="{SITE_URL}/feed.xml">RSS</a></span>
    </div>
  </div>
</footer>"""


def page_v2(root, title, body_html, year, indicator_links="", **meta):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{head_v2(root, title, **meta)}
</head>
<body class="v2">
{header_v2(root)}
<main id="main">
{body_html}
</main>
{footer_v2(root, year, indicator_links.replace('{root}', root))}
</body>
</html>
"""
