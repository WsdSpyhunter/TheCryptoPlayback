# Institutional Indicators Suite (Phase 1, free-data edition)

Four institutional-style indicators computed **only from free public data** (no paid APIs, no API keys),
shown on `institutional.html` in the Version 2 site style.

| # | Indicator | File | Output |
|---|-----------|------|--------|
| 1 | Basic Institutional Pressure Index | `scripts/pro/pressure.py` | `data/pro/pressure.json` |
| 2 | Crowded Unwind Risk Map | `scripts/pro/unwind.py` | `data/pro/unwind.json` |
| 3 | Protocol Revenue / TVL Quality Score | `scripts/pro/quality.py` | `data/pro/quality.json`, `quality_history.json` |
| 4 | Basic Stablecoin Velocity & Flows | `scripts/pro/stables.py` | `data/pro/stables.json` |

## How it differs from the original brief (and why)
The brief suggested a FastAPI server, SQLite and a React front end. This site is static (GitHub Pages) and updates through scheduled GitHub Actions, which is
**free to run and needs no server**. So the same architecture is expressed as: *modular collectors → feature/scoring code → JSON files → static page*.
Raw → features → scores stay separate modules; the page is generated HTML with inline-SVG charts (no JavaScript library). Nothing is hard-wired to the page, so an
API, a database, or a paywall can be added later by reading the same JSON files. History is **recomputed from free historical endpoints on every run**
(stateless, robust), except the Quality score history which is accumulated daily.

## Run it locally
```bash
pip install -r requirements.txt
cd scripts
python -m pro.refresh_pro            # all four (about 20 seconds); or name some: pressure unwind quality stables
python pro_page.py                   # writes ../institutional.html from data/pro/*.json
python -m http.server 8124 --directory ..   # open http://localhost:8124/institutional.html
```
Each indicator also runs alone: `python -m pro.pressure`, `python -m pro.unwind`, `python -m pro.quality`, `python -m pro.stables`.

## Scheduling
`.github/workflows/refresh-pro.yml` runs every 2 hours (and on demand), refreshes the data, rebuilds the page and commits. Each indicator is isolated: if one
source fails it keeps its last good file, marked `stale` (the page says so), and the job still succeeds as long as one indicator refreshed. No secrets are required.
Note: GitHub only runs scheduled workflows from the default branch, so this starts after the Version 2 branch is merged to `main`.

## Free data sources (verified 2026-10-07 from a US network)
| Need | Source | Notes |
|------|--------|-------|
| Funding, open interest | OKX, Gate.io, Hyperliquid, Bitget, Deribit (BTC/ETH), Kraken Futures public APIs | funding normalised to a per-8h rate; OI in USD |
| Long/short ratios, liquidations, hourly history | Gate.io `contract_stats`; OKX `rubik` endpoints | Gate gives 180+ days of hourly OI, ratios, funding, liquidations per contract |
| Coinbase Premium | Coinbase Exchange, OKX, Kraken public prices | computed here; see below |
| ETF flows | the site's own `data/etf_flows.json` (SoSoValue, validated against XOOMAR) | Farside blocks automation (Cloudflare 403) |
| Protocol TVL / fees / revenue | DefiLlama `/protocols`, `/overview/fees`, `/summary/fees/{slug}` | no key |
| Stablecoin supply | Token contracts on public nodes (blastapi, drpc, mevblocker, mainnet.base.org, api.avax.network), TronGrid, Solana public RPC; Tether transparency feed | no key; archive-capable keyless nodes verified 2026-10-08 |

**Not used:** Binance and Bybit (both refuse US IP addresses, which includes GitHub Actions), Farside (blocks scraping).
**Licensing before any paywall:** DefiLlama's API is free; exchange market-data endpoints are public but each venue's terms apply. Re-read the terms of DefiLlama, OKX,
Gate.io and Hyperliquid before charging for a product built on them, and add attribution where requested.

## Methodology

### 1. Institutional Positioning Index (Open Edition; replaces the first "Pressure Index")
Module `scripts/pro/positioning.py`. Four components, each a trailing z-score (past data only, clipped ±3), blended with configurable weights: **CME futures positioning 30%**
(asset managers' net position as % of open interest from the CFTC Traders in Financial Futures report, weekly since 2018, z over the trailing 104 weeks; a report counts from the Saturday after the
Tuesday it describes), **Spot ETF flows 30%** (half 1-day, half 5-day sum; the site's ETF dataset), **On-chain perp funding 20%** (Hyperliquid BTC funding per 8h, z over 30 days), **Perp OI x price 20%**
(24h change in Hyperliquid BTC open interest signed by 24h price direction; builds from our own hourly snapshots in `data/pro/hl_btc_snapshots.json` because Hyperliquid has no OI history). Output: z-score,
0-100 percentile, regime (z >= +1 Bullish Positioning, z <= -1 Bearish Positioning, else Neutral), components, ~30 days of history, and a CME block (asset managers / leveraged funds / dealers: long, short, net, % of OI,
weekly change, two-year chart). Leveraged funds are usually net short because many run the ETF-vs-futures basis trade, so their short is shown but not scored as bearish. The earlier version (`scripts/pro/pressure.py`)
used Coinbase Premium and centralised-exchange funding/OI; those were removed (no clean free source). `pressure.py` is kept because the ETF helper is reused.

### 2. Crowded Unwind Risk Map (Open Edition: on-chain perpetuals)
Module `scripts/pro/unwind_chain.py`. Ten assets (BTC, ETH, SOL, XRP, DOGE, BNB, ADA, AVAX, LINK, SUI) on Hyperliquid, the largest on-chain perp exchange. Score 0-100 from four percentiles of the coin's own trailing 30 days:
**Premium 45%** (|perp price vs oracle price|, from Hyperliquid's hourly funding-history premium), **Funding excess 25%** (funding above or below Hyperliquid's fixed 0.01%-per-8h interest floor: raw funding sits on that
floor whenever the market is balanced and would falsely look elevated; 60% extremity + 40% persistence), **Open interest 15%** (current OI vs its own range, built from our own hourly snapshots in
`data/pro/hl_snapshots.json` because Hyperliquid has no OI history; shows "building" for about two days and the other components are re-weighted meanwhile), **Adverse move 15%** (24h move against the crowded side).
Bands: Low <35, Moderate 35-55, High 55-75, Extreme >=75. Direction = vote of premium sign (beyond 1 bp) and funding-excess sign; Low scores read "Balanced". dYdX was evaluated and dropped (100-500x smaller than Hyperliquid, so
noise). **Not modelled (no free data):** long/short account ratios, liquidation-price clusters, order-book depth, centralised-exchange crowding. The earlier Gate.io-based version (`scripts/pro/unwind.py`) is kept but unused.

### 3. Protocol Revenue / TVL Quality Score
Universe: TVL ≥ $100M, 30-day fees ≥ $250k, top 60 by fees. Percentile ranks: Fee yield 35%, Stability 25% (low CV of 90-day daily fees), Growth 20%, Scale 20%.
Also fee concentration (top-5/top-10 share, HHI). Score history accumulates daily in `data/pro/quality_history.json`.

### 4. Basic Stablecoin Velocity & Flows (Open Edition: on-chain)
Module `scripts/pro/stables_chain.py`. No aggregator: supply is read from each token's contract (`totalSupply()`) on free public nodes (Ethereum, Base, Arbitrum, Polygon,
Optimism, Avalanche, BSC), Tron through TronGrid, Solana through the public RPC; Tether's own transparency feed supplies its reserve figures. Nine USD coins are tracked.
USDT is counted only on Ethereum and Tron (about 97% of Tether's liabilities); bridged or Binance-Peg copies are excluded to avoid double counting, and USDT circulating supply
= total supply minus the Tether treasury wallet's balance (reconciles to Tether's published liabilities). History: EVM chains from archive-node reads at each midnight UTC; Tron from the
treasury wallet's on-chain transfers; Solana accumulates from the first run (`data/pro/stable_chain_history.json`, 60 days). Net issuance = change in supply (supply only changes
by mint or burn). Flow velocity = average daily net issuance, last 7 days versus the 7 days before. Flow signal = z-score of the 7-day change versus the last two months.
**Not modelled (no free source):** exchange balances / netflows, on-chain transfer volume, smaller chains, non-USD stablecoins. (The earlier DefiLlama-based version, `scripts/pro/stables.py`, is kept in the repo but no longer used.)

## Data-quality caveats
* Fees, TVL and stablecoin supply are third-party reported and can be revised. Percentiles depend on the universe at the time.
* ETF history in the site dataset is short (starts late September 2026), so ETF z-scores use fewer observations than other components.
* Liquidation volumes are those seen on Gate.io only. Funding conventions differ by venue and are normalised as documented in `derivs.py`.
* These are descriptive gauges, not forecasts or advice.

## Extending
Add a venue: write a `snapshot_<venue>()` in `derivs.py` and register it in `VENUES`. Add an asset: append to `ASSETS` (it needs a `<SYM>_USDT` contract on Gate).
Change weights: edit the constants at the top of each module. New indicator: add `scripts/pro/<name>.py` with `compute()` returning a dict with `updated_at`, register it in
`refresh_pro.JOBS`, and add a section function in `scripts/pro_page.py`.
