"""Search-facing copy for indicator pages: a sharper <title>/description and a short plain-English FAQ.

Written for people searching the plain phrase (e.g. "bitcoin funding rate"). It explains the measure; it never
predicts. Indicators without an entry keep the generic title and first-section description.
"""

SEO = {
    "leverage_heat": {
        "title": "Bitcoin Funding Rate Today: Live Leverage Heat",
        "desc": "Live Bitcoin perpetual futures funding rate and what it says about crowded leverage. Updated every 15 minutes, with plain-English reading help.",
        "faq": [
            ("What is the Bitcoin funding rate?", "It is the small periodic payment between traders who are long and traders who are short on Bitcoin perpetual futures. When the rate is positive, longs pay shorts; when it is negative, shorts pay longs."),
            ("What does a high funding rate mean?", "A high positive or negative rate means one side of the market is crowded with leverage. That raises the chance of fast, forced liquidations, but it does not say which way price will go."),
            ("Where does this data come from?", "It is read directly from OKX's public BTC-USDT perpetual swap data and refreshed every 15 minutes. Nothing is estimated or backfilled."),
        ],
    },
    "liquidations": {
        "title": "Bitcoin Liquidations Today: Live Long vs Short Data",
        "desc": "Live Bitcoin futures liquidations: how many dollars of longs and shorts were force-closed recently. Updated every 15 minutes, free.",
        "faq": [
            ("What is a crypto liquidation?", "A liquidation happens when an exchange force-closes a leveraged trade because the trader's collateral can no longer cover the losses."),
            ("Why do long and short liquidations matter?", "Large long liquidations mean over-leveraged buyers were forced out as price fell; large short liquidations mean over-leveraged sellers were forced out as price rose. Big totals show how stretched positioning was."),
            ("Is this a buy or sell signal?", "No. It is a description of recent forced selling and buying, not a forecast."),
        ],
    },
    "market_breadth": {
        "title": "Crypto Market Breadth Today: How Many Coins Are Rising",
        "desc": "Live crypto market breadth: the share of 40 major coins trading above their moving average. A quick read on whether a rally is broad or narrow.",
        "faq": [
            ("What is crypto market breadth?", "It measures how many coins are taking part in a move. If most of the 40 coins we track are rising, breadth is strong; if only a few are, breadth is weak."),
            ("Why does breadth matter?", "A rally led by only Bitcoin and a handful of coins is often more fragile than one where most coins are participating. Breadth shows which one you are looking at."),
            ("Which coins are included?", "A fixed universe of 40 major coins by market cap, with stablecoins and wrapped or staked tokens excluded."),
        ],
    },
    "stablecoin_liquidity": {
        "title": "Stablecoin Supply Today: Total USDT, USDC & More",
        "desc": "Live total stablecoin supply (USDT, USDC, DAI and others) and its 7-day change. A simple gauge of how much dollar liquidity is parked in crypto.",
        "faq": [
            ("What is stablecoin liquidity?", "It is the total supply of dollar-pegged stablecoins such as USDT and USDC. These coins are the cash that traders use to buy other crypto, so the total shows how much dry powder sits inside the market."),
            ("Is a growing stablecoin supply bullish?", "Not automatically. Growth means more cash has entered crypto, which can support buying, but it does not guarantee that the cash will be spent or that prices will rise."),
            ("How often is it updated?", "Every 15 minutes, from public market data."),
        ],
    },
    "macro_risk": {
        "title": "Macro Risk Today: Stock Volatility & Dollar Strength",
        "desc": "Live read on traditional-market stress that often spills into crypto: stock-market volatility (VIX) and US dollar strength, updated automatically.",
        "faq": [
            ("What is macro risk in crypto?", "It is the pressure that comes from outside crypto: swings in stocks and in the US dollar. Crypto often trades as a risk asset, so rough conditions elsewhere can weigh on it."),
            ("What does this indicator track?", "Equity volatility (the VIX) and US dollar strength. A calm reading means traditional markets look steady; an elevated one means they look stressed."),
            ("Does it predict Bitcoin's price?", "No. It describes the backdrop, not the outcome."),
        ],
    },
    "defi_pulse": {
        "title": "DeFi TVL Today: Total Value Locked Across Chains",
        "desc": "Live total value locked (TVL) across DeFi protocols on every chain DefiLlama tracks, with recent change. Updated automatically.",
        "faq": [
            ("What is DeFi TVL?", "Total value locked is the dollar value of crypto deposited in decentralized finance apps such as lending markets, exchanges and staking."),
            ("Why does TVL change?", "It rises when people deposit more or when prices of the locked tokens rise, and falls when people withdraw or prices drop. So it mixes real activity with price moves."),
            ("Where does the data come from?", "DefiLlama's public data, combined across all chains it tracks."),
        ],
    },
}
