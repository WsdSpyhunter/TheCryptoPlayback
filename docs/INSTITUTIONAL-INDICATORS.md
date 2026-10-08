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
| Stablecoins, DEX volume | DefiLlama `stablecoins.llama.fi`, `/overview/dexs` | no key |

**Not used:** Binance and Bybit (both refuse US IP addresses, which includes GitHub Actions), Farside (blocks scraping).
**Licensing before any paywall:** DefiLlama's API is free; exchange market-data endpoints are public but each venue's terms apply. Re-read the terms of DefiLlama, OKX,
Gate.io and Hyperliquid before charging for a product built on them, and add attribution where requested.

## Methodology

### 1. Basic Institutional Pressure Index
Four components, each a trailing z-score against its own past (no look-ahead, clipped to ±3), blended with configurable weights
(`DEFAULT_WEIGHTS` in `pressure.py`): **ETF net flow 30%** (half 1-day, half 5-day sum; a day counts from the next 00:00 UTC), **Coinbase Premium 20%**
(Coinbase BTC-USD ÷ (OKX BTC-USDT × Kraken USDT/USD) − 1, in bps; half 6-hour mean, half 24-hour mean), **Funding 25%** (OI-weighted funding across OKX, Gate,
Hyperliquid), **OI × price 25%** (24-hour change in aggregate BTC OI (Gate + OKX) signed by the 24-hour price direction). Output: z-score, 0–100 percentile
(normal CDF of z), regime (z ≥ +1 Strong Buy Pressure, z ≤ −1 Strong Sell Pressure, else Neutral), component breakdown and ~30 days of history.

### 2. Crowded Unwind Risk Map
Ten assets (BTC, ETH, SOL, XRP, DOGE, BNB, ADA, AVAX, LINK, SUI). Score 0–100 from five percentiles of the asset's own trailing 30 days of Gate.io hourly stats:
OI crowding 30%, Funding 30% (60% extremity + 40% persistence), Long/short skew 20% (deviation from own median), Liquidation heat 10% (24h liquidations ÷ OI),
Adverse move 10% (24h move against the crowded side). Bands: Low <35, Moderate 35–55, High 55–75, Extreme ≥75. Cross-venue OI/funding table is context only.
**Not modelled (no free data):** liquidation-price clusters, order-book depth.

### 3. Protocol Revenue / TVL Quality Score
Universe: TVL ≥ $100M, 30-day fees ≥ $250k, top 60 by fees. Percentile ranks: Fee yield 35%, Stability 25% (low CV of 90-day daily fees), Growth 20%, Scale 20%.
Also fee concentration (top-5/top-10 share, HHI). Score history accumulates daily in `data/pro/quality_history.json`.

### 4. Basic Stablecoin Velocity & Flows
USD-pegged stablecoins only. Supply, 1/7/30-day change and net issuance (mint-minus-burn proxy), major coins with peg deviation (coins >3% from $1 are shown as
non-par), chain deployment (7/30-day net change), velocity proxy = 7-day average daily DEX volume ÷ supply, flow signal and velocity signal as 365-day z-scores.
**Not modelled (no free data):** exchange balances / netflows, perp-DEX volume.

## Data-quality caveats
* Fees, TVL and stablecoin supply are third-party reported and can be revised. Percentiles depend on the universe at the time.
* ETF history in the site dataset is short (starts late September 2026), so ETF z-scores use fewer observations than other components.
* Liquidation volumes are those seen on Gate.io only. Funding conventions differ by venue and are normalised as documented in `derivs.py`.
* These are descriptive gauges, not forecasts or advice.

## Extending
Add a venue: write a `snapshot_<venue>()` in `derivs.py` and register it in `VENUES`. Add an asset: append to `ASSETS` (it needs a `<SYM>_USDT` contract on Gate).
Change weights: edit the constants at the top of each module. New indicator: add `scripts/pro/<name>.py` with `compute()` returning a dict with `updated_at`, register it in
`refresh_pro.JOBS`, and add a section function in `scripts/pro_page.py`.
