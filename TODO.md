# To-do (paused 2026-10-07)

## Version 2 rollout (paused while the "Institutional / Pro Indicator" side project is done)
Build from the locked baseline (tag `version-2-homepage-baseline`, branch `version-2-dev`):
1. The 16 indicator pages in the v2 shell (own title/description, breadcrumbs, structured data).
2. Archive and issue pages (per-issue share card with headline, Article structured data).
3. About and Resources in the v2 shell.
4. Rebuild the newsletter email from the LOCKED redesign in docs/newsletter-v3-design/ (README + index.html are the source of truth; table-based, test sends to the owner's phone). See docs/NEWSLETTER-V3-DESIGN-LOCK.md.
5. Merge to `main` only on the owner's go-ahead (re-run build_site.py after the merge).

## Owner actions
- Verify the site in Google Search Console and Bing Webmaster Tools and submit https://cryptoplayback.com/sitemap.xml.

## Open optional items
- Shrink / re-host very large story images; choose a better thumbnail for the Oct 5 Weekly teaser.
- Fifth oval color on Resources (v1 only); "Biggest Mover of the Week" from top 10.

## Pinned questions to ask the owner again (once the four Playback Lab indicators are built and working well)
- Add small "See the full picture in the Playback Lab" links to the five homepage cards that have deeper Lab counterparts (ETF Flow, Leverage Heat, Liquidations, Stablecoin Liquidity, DeFi Pulse)? (Touches the locked homepage; owner said they probably want to, but later.)
- Whether to add Whale Activity and/or Macro Risk (net liquidity) as extra Lab sections.

## Playback Lab roadmap (agreed 2026-10-08)
1. Finish the first four indicators on cleaner sources ("Open Edition"): Stablecoin Flows on-chain (supply, mint/burn straight from the chains + issuer feeds); Pressure Index -> Institutional Positioning Index (ETF flows, CFTC positioning, Hyperliquid funding/OI); Unwind Risk Map on Hyperliquid + dYdX; Revenue/TVL Quality stays on DefiLlama while permission is requested. Remove per-exchange "Cross-venue" tables; log readings daily for a public track record.
2. NEW indicator 1: ETF/Futures Basis-Trade Crowding (CFTC COT leveraged-fund shorts vs ETF holdings vs CME OI).
3. NEW indicator 2: Regulatory & ETF-Pipeline Tracker (Federal Register + SEC feeds).
4. NEW indicator 3: Miner Stress (hashprice, hash ribbons, Puell multiple, difficulty forecast; mempool.space).
5. NEW indicator 4: Net Liquidity & Macro Sensitivity (FRED + Treasury; BTC beta/correlation).
Later: the pinned homepage-links question, paused Version 2 rollout, permission emails, lawyer review, waitlist test.

## Market-read accuracy ideas (agreed 2026-10-11)
Done: (1) Bitcoin Trend & Volatility indicator in the Lab (scripts/pro/trend.py; counts in the Playback Read); (5) daily Signal Confluence log (data/signal_log.json, scripts/signal_log.py; first reading each US Central day at/after 7 AM CT, with the BTC price). The Playback Read history (data/pro/read_history.json) now also stores the BTC price ("px").
Later (owner: "pin it, remind me at good stopping points"):
- (2) Tighten weak inputs: liquidations come from ~100 recent OKX events (thin sample); Whale Activity is a small-sample count (unscored); Leverage Heat uses a single funding rate -> blend several permissionless venues (Hyperliquid, dYdX, etc.).
- (3) Split the market read into a Bitcoin read and a crypto-market read (BTC-specific: ETF flows, miners, funding, trend; broad: sectors, DeFi, narrative momentum, breadth). When they disagree, that is information.
- (4) Group/weight the signals (trend, flows, leverage, macro, sentiment) and show the groups instead of a flat count like 8/13.
- Exchange reserves proxy indicator (#8) - first check which exchanges publish usable proof-of-reserves addresses and whether history can be backfilled.
- After ~3 months of the signal log: publish an honest track-record page (how readings related to what BTC did next). Use data/signal_log.json + data/pro/read_history.json.
- Possibly show the track record on the Lab / homepage once there is enough history.
Biggest Mover stays at the top-10 pool (owner decision 2026-10-11); do not change to top 50.
