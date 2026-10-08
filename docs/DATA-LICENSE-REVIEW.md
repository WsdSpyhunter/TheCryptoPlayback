# Data licence review: Institutional indicators (2026-10-07)

**Not legal advice.** This is a plain-language read of each source's published terms, done with web research on 2026-10-07. Terms change; some pages could
not be read in full. Before charging for anything, have a lawyer confirm the points marked "confirm".

## Bottom line
Technical access is not permission. Almost every source below licenses its free data for **personal / internal use**, and several restrict republishing it
or using it in a commercial product without **written consent**. That means:
* **Free public page:** low-to-moderate risk if we show our own derived scores, credit sources and avoid republishing raw per-venue figures. It is not zero risk, and the
  live homepage already uses OKX (funding, open interest, liquidations) and DefiLlama (TVL, stablecoins) the same way.
* **Paid product:** NOT cleared. Needs written permission or paid licences (or replacement sources) before launch.

## Source by source
| Source | What the terms say (own words) | Free public page | Paid product |
|---|---|---|---|
| **DefiLlama** (TVL, fees, stablecoins, DEX volume) | Limited licence for personal, non-commercial use. No reselling or republishing data; scraping for commercial purposes needs prior written consent; the terms list large liquidated damages for data-use breaches. Paid API plan is $300/month (1,000 req/min); custom data licences only on the Enterprise plan. | Moderate: derived scores, credited | Needs consent or a paid/enterprise licence |
| **OKX** (funding, OI, long/short ratios) | API agreement's "market data" explicitly includes funding and open interest and covers public, unauthenticated endpoints. Data is for your own trading/account use; no publishing or displaying to third parties, no use in a commercial product or competing analytics platform without written consent. "Derived data" is not defined. | Moderate to high for raw figures; derived scores are a grey area | Needs written consent / data licence |
| **Gate.io** (hourly stats, history) | User Agreement bars unauthorised API use, evading limits, scraping and using the services commercially without written agreement. The part I could read does not address redistributing market data (part of the text was not read). | Moderate (confirm) | Needs written consent |
| **Coinbase** (price for the premium) | Public market data is under Coinbase's Market Data terms: limited licence for your own or your entity's personal/research use, not for building an app for end users; redistribution is handled through authorised partners. Could not read the live text. | Low (one price, used only inside a ratio) (confirm) | Needs a licence or a licensed redistributor |
| **Deribit** (BTC/ETH perp snapshot) | Terms (2021 update, from Deribit's summary) limit market and derived data to personal use; aggregating, publishing or reselling needs explicit approval. | Moderate (confirm); tiny weight in our data | Needs approval |
| **Kraken** (USDT/USD, futures snapshot) | API terms not retrieved. Kraken lists marketdata@kraken.com for licensing questions. | Unknown (confirm) | Ask Kraken |
| **Hyperliquid** (funding, OI) | Terms page could not be read; developer docs say nothing about licensing. It is an on-chain exchange, so the data is public by design, but the interface terms still apply (confirm). | Unknown, probably lowest | Confirm |
| **Bitget** | Data terms not found. | Unknown | Confirm |
| **SoSoValue / XOOMAR** (ETF flows) | Terms not found. We already use an API key from SoSoValue, so its terms govern; check them. | Unknown | Check API terms |

## What we can do about it
1. **Before launch, reduce exposure on the free page** (small changes I can make): remove the per-venue "Cross-venue" tables (they republish venue-level OI and funding), show only our own
   aggregated scores, keep clear source credits, and say we are independent and not affiliated with any exchange.
2. **Ask for permission** in writing (I can draft the emails): OKX, Gate.io, Deribit, Coinbase, Kraken (marketdata@kraken.com), DefiLlama (sales@defillama.com), SoSoValue. Keep the replies.
3. **Plan the paid version around licensed data:** DefiLlama's $300/month API tier or Enterprise licence; written consent or a vendor that is an authorised redistributor
   for exchange data (for example Amberdata, which says it is an authorised Coinbase redistributor); or substitute on-chain/public-ledger data and public-domain macro data where possible.
   The suite is built so a source can be swapped without redesigning the indicators.
4. **Get a short legal review** (a few hundred dollars of lawyer time) before charging. The cost of a mistake is high (DefiLlama's terms mention damages of up to $100,000 per violation).

## Reading list
DefiLlama [terms](https://defillama.com/terms) and [plans](https://docs.llama.fi/pro-api) · OKX [API agreement](https://www.okx.com/en-us/help/okx-api-agreement) · Gate [user agreement](https://www.gate.com/legal/user-agreement) ·
Coinbase [market data terms](https://www.coinbase.com/legal/market_data) · Deribit [terms update](https://insights.deribit.com/exchange-updates/deribit-updates-terms-of-service-as-of-29-january-2021/) · Kraken [API docs](https://docs.kraken.com/api/docs/guides/global-intro)
