# The Crypto Playback: Version 2 baseline (homepage locked)

**Locked 2026-10-07** on branch `version-2-dev`, tag `version-2-homepage-baseline`.
The approved Version 2 homepage (navy / brass / ivory). Build the rest of Version 2 from this;
do not restyle the homepage without the owner's request. Version 1 is untouched at tag `version-1-final`.

## What is locked
- Homepage markup: `scripts/home_v2.py`, `scripts/v2_ui.py`; shared shell (header, footer, SEO head) in `scripts/partials.py` (`theme="v2"`).
- Styles: `assets/v2.css` (tokens at the top: navy `#0B1F3A`, brass `#B8934A`/`#D4B063`, ivory `#F7F4EC`; IBM Plex Sans/Mono, Libre Franklin, Barlow Condensed).
- Brand artwork: `assets/v2/` (made by `scripts/prep_v2_assets.py` from the owner's source PNGs).
- SEO files: `scripts/seo.py` (sitemap.xml, robots.txt, feed.xml, llms.txt, 404.html), JSON-LD on the homepage.
- Approved details: hero (large wordmark, tagline directly under it, buttons and stats row below), Top 6 tickers (symbols larger than prices), Market Snapshot with extra website-only Fear & Greed sentence, Signal Confluence with dark-navy boxed titles and centered data, What Changed with boxed labels, Alerts & Indicators with centered cards (title + icon on one line, status tag above the link), Top News, Subscribe (mascot nudged up-left), Decode The Dashboard, footer.

## Still to do (not part of this baseline)
Indicator pages, archive, issue pages, About, Resources in the v2 shell; the v2 newsletter email; merge to `main` only on the owner's go-ahead.

## Get back to this baseline
```bash
git fetch --tags
git checkout version-2-homepage-baseline -- .
```
