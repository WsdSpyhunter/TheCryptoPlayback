"""Run once (or whenever you want to edit About/Resources copy) to regenerate
the two static pages. Unlike index/archive/posts, these are NOT touched by
the daily/weekly automation — edit this file and rerun it by hand."""
import os
from datetime import datetime
from partials import page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ABOUT_BODY = """<div class="page-content">
  <h1>About The Crypto Playback</h1>
  <p>The Crypto Playback is your trusted source for efficient Bitcoin and crypto news and data.</p>
  <p>The website and newsletter both offer a quick scan of the top headlines plus deep, high-value data. All in one place, on a single page, free for subscribers.</p>
  <p>No more spending your day scrolling Crypto Twitter or hunting across multiple sites for the information you need.</p>
  <p>One stop. One look. A quick Crypto Playback and you&rsquo;re fully informed on the fastest-moving industry on the planet.</p>
  <p>Nothing here is financial advice. See the note at the bottom of every page for the full disclosure.</p>
  <h1 style="margin-top:2em;">Contact</h1>
  <p>Questions, tips, or feedback: <a href="mailto:info@cryptoplayback.com">info@cryptoplayback.com</a></p>
</div>"""

# ---------------------------------------------------------------------------
# Resources page: full-bleed banded sections of shadowed link cards. All
# styling lives in assets/styles.css under the res- prefix. Cards are plain
# data below - add or reorder entries here and rerun this script.
# Audience tags: R = retail, I = institutional, A = all levels.
# ---------------------------------------------------------------------------
TAGS = {
    "R": ("res-tag--retail", "Retail"),
    "I": ("res-tag--inst", "Institutional"),
    "A": ("res-tag--all", "All levels"),
}


def _card(source, title, desc, url, tag):
    cls, label = TAGS[tag]
    # External links open in a new tab; links to our own pages stay put.
    target = ' target="_blank" rel="noopener noreferrer"' if url.startswith("http") else ""
    return (
        f'<a class="res-card" href="{url}"{target}>'
        f'<div class="res-card-top"><span class="res-source">{source}</span>'
        f'<span class="res-tag {cls}">{label}</span></div>'
        f'<h3>{title}</h3><p>{desc}</p><span class="res-go">Visit &rarr;</span></a>'
    )


def _section(sec_id, band, kicker, title, sub, cards, extra=""):
    return (
        f'<section class="res-band res-band--{band}" id="{sec_id}"><div class="res-inner">'
        f'<div class="res-head"><span class="res-kicker">{kicker}</span>'
        f'<h2 class="res-title">{title}</h2><p class="res-sub">{sub}</p></div>'
        f'<div class="res-grid">{"".join(_card(*c) for c in cards)}</div>{extra}</div></section>'
    )


FID = "https://www.fidelity.com/learning-center/trading-investing"
LOPP = "https://www.lopp.net/bitcoin-information"
BTCMAG = "https://bitcoinmagazine.com/guides"
WOLF = "https://thewolfofallstreets.com/tools"

START_HERE = [
    ("Fidelity", "Crypto for Beginners", "A structured primer on how crypto works, what moves prices and which risks to understand before you put money in.", f"{FID}/crypto/crypto-for-beginners", "R"),
    ("Fidelity", "What Is Bitcoin?", "How the largest cryptocurrency works, along with the key risks to weigh.", "https://www.fidelity.com/viewpoints/active-investor/what-is-bitcoin", "R"),
    ("Fidelity", "Blockchain Explained", "A visual walk-through of the technology underneath crypto and why it matters.", f"{FID}/crypto/blockchain-101", "R"),
    ("Lopp.net", "Getting Started", "A plain-language intro to what Bitcoin is, why it is unique and how it works.", f"{LOPP}/getting-started.html", "R"),
    ("Bitcoin Magazine", "How to Use &amp; Store Bitcoin Safely", "Practical steps for sending, receiving and securing your first bitcoin.", f"{BTCMAG}/how-to-use-store-bitcoin-safely", "R"),
    ("Bitcoin Magazine", "Protecting Savings From High Inflation", "A guide to how bitcoin is discussed as a tool for preserving personal savings.", f"{BTCMAG}/how-to-protect-your-savings-from-high-inflation", "R"),
]

TOOLS = [
    ("Wolf of All Streets", "DCA Time Machine", "See what a recurring bitcoin purchase would have looked like across history.", f"{WOLF}/dca", "A"),
    ("Wolf of All Streets", "Stack vs S&amp;P", "Compare identical dollars in bitcoin and the S&amp;P 500, lump sum or dollar-cost averaged.", f"{WOLF}/stack-vs-sp", "A"),
    ("Wolf of All Streets", "Retire on Bitcoin", "Estimate when a bitcoin stack could cover your spending, or how much that lifestyle would take.", f"{WOLF}/retire", "R"),
    ("Into the Cryptoverse", "Risk &amp; Cycle Analytics", "Market video analysis, risk and cycle charts and portfolio tools. The deeper toolset sits behind a paid subscription.", "https://intothecryptoverse.com/", "I"),
    ("Lopp.net", "Network Statistics", "A directory of metrics that track Bitcoin's adoption and network health.", f"{LOPP}/statistics-metrics.html", "I"),
    ("The Crypto Playback", "Our Live Dashboard", "Every market signal we track, scored on one page and refreshed every 15 minutes: sentiment, risk, flows, leverage and more.", "index.html", "A"),
]

INSTITUTIONAL = [
    ("Fidelity", "Advanced Crypto Hub", "Market outlooks, regulation, taxes and product explainers for investors who are past the basics.", f"{FID}/crypto/crypto-advanced", "I"),
    ("Fidelity", "Bitcoin's Four-Year Cycles", "A look at the cyclical patterns in bitcoin and what they could mean for investors.", f"{FID}/four-year-bitcoin-and-crypto-cycles", "I"),
    ("Fidelity", "Spot Bitcoin ETPs", "What a spot bitcoin exchange-traded product is and how it differs from holding coins directly.", f"{FID}/spot-bitcoin-ETP", "A"),
    ("Fidelity", "SEC &amp; CFTC Crypto Guidance", "The latest U.S. regulatory guidance and how markets reacted to it.", f"{FID}/sec-cftc-crypto-guidance", "I"),
    ("Fidelity Digital Assets", "Bitcoin First", "Research on why investors may want to consider bitcoin separately from other digital assets.", "https://www.fidelitydigitalassets.com/research-and-insights/bitcoin-first", "I"),
    ("NYDIG", "Bitcoin's Protection Under the First Amendment", "Institutional research on the legal footing of bitcoin in the United States.", "https://nydig.com/research/bitcoins-protection-under-the-first-amendment", "I"),
    ("Lopp.net", "Investment Theses", "A curated collection of the arguments investors make for and against owning bitcoin.", f"{LOPP}/investment-theses.html", "I"),
    ("Bitcoin Magazine", "Best Bitcoin-Backed Loans", "A guide to lending products that use bitcoin as collateral.", f"{BTCMAG}/best-bitcoin-backed-loans", "I"),
]

PROTECT = [
    ("Lopp.net", "Setting Up a Wallet", "Hardware, software, metal and paper wallets, with the trade-offs of each.", f"{LOPP}/recommended-wallets.html", "R"),
    ("Lopp.net", "Security", "How to protect your keys without making your setup so complex you lock yourself out.", f"{LOPP}/security.html", "A"),
    ("Lopp.net", "Running a Node", "Verify the network yourself: why running your own node gives the strongest security model.", f"{LOPP}/full-node.html", "A"),
    ("Fidelity", "Store Crypto Safely", "Protection strategies against hacks, scams and other cybersecurity threats.", f"{FID}/is-bitcoin-safe", "R"),
    ("Bitcoin Magazine", "Bitcoin Privacy in 2026", "A practical guide to on-chain and off-chain privacy tools.", f"{BTCMAG}/bitcoin-privacy-in-2026-a-practical-guide", "A"),
    ("Fidelity", "Crypto Tax Guide", "How crypto is taxed and ways to keep your records in order.", f"{FID}/crypto/crypto-tax-guide", "A"),
    ("Fidelity", "Crypto &amp; Estate Planning", "How digital assets fit into an estate plan and how they pass to heirs.", "https://www.fidelity.com/learning-center/wealth-management-insights/crypto-and-estate-planning", "A"),
    ("Bitcoin Magazine", "Moving a 401(k) Into a Bitcoin IRA", "The steps involved in rolling an old retirement account into a bitcoin IRA.", f"{BTCMAG}/6-steps-to-move-an-old-401k-into-a-bitcoin-ira", "R"),
]

# (title, author, topic, url)
READING = [
    ("Shelling Out: The Origins of Money", "Nick Szabo", "Money", "https://nakamotoinstitute.org/shelling-out/"),
    ("The Bullish Case for Bitcoin", "Vijay Boyapati", "Investing", "https://medium.com/@vijayboyapati/the-bullish-case-for-bitcoin-6ecc8bdecc1"),
    ("Bitcoin Does Not Waste Energy", "Parker Lewis", "Energy", "https://www.unchained-capital.com/blog/bitcoin-does-not-waste-energy/"),
    ("Bitcoin, Not Blockchain", "Parker Lewis", "Fundamentals", "https://unchained-capital.com/blog/bitcoin-not-blockchain/"),
    ("A Most Peaceful Revolution", "Nic Carter", "Culture", "https://medium.com/@nic__carter/a-most-peaceful-revolution-8b63b64c203e"),
    ("Bitcoin Obsoletes All Other Money", "Parker Lewis", "Money", "https://unchained-capital.com/blog/bitcoin-obsoletes-all-other-money/"),
    ("The Number Zero and Bitcoin", "Robert Breedlove", "Culture", "https://medium.com/@breedlove22/the-number-zero-and-bitcoin-4c193336db5b"),
    ("Dear Family, Dear Friends", "Gigi", "Fundamentals", "https://dergigi.com/2020/04/27/dear-family-dear-friends/"),
    ("The Last Word on Bitcoin&rsquo;s Energy Consumption", "Nic Carter", "Energy", "https://www.coindesk.com/the-last-word-on-bitcoins-energy-consumption"),
    ("Masters and Slaves of Money", "Robert Breedlove", "Money", "https://medium.com/@breedlove22/masters-and-slaves-of-money-255ecc93404f"),
    ("Stone Ridge 2020 Shareholder Letter", "Ross Stevens", "Institutional", "https://www.microstrategy.com/en/bitcoin/documents/stone-ridge-2020-shareholder-letter"),
    ("Bitcoin Is Time", "Gigi", "Culture", "https://dergigi.com/2021/01/14/bitcoin-is-time/"),
    ("Bitcoin First: Why Investors Need to Consider Bitcoin Separately From Other Digital Assets", "Chris Kuiper &amp; Jack Neureuter", "Institutional", "https://www.fidelitydigitalassets.com/research-and-insights/bitcoin-first"),
    ("The Legendary Treasure of Satoshi Nakamoto", "Tomer Strolight", "Culture", "https://tomerstrolight.medium.com/the-legendary-treasure-of-satoshi-nakamoto-c3621c5b2106"),
    ("Toward a Node World Order", "Michael Goldstein", "Culture", "https://bitcointimes.com.au/toward-a-node-world-order/"),
    ("Bitcoin&rsquo;s Protection Under the First Amendment", "Ross Stevens", "Legal", "https://nydig.com/research/bitcoins-protection-under-the-first-amendment"),
]

SIGNALS = [
    ("fear-greed-index.html", "Fear &amp; Greed"), ("biggest-mover.html", "Biggest Mover"),
    ("risk-radar.html", "Risk Radar"), ("capital-flow.html", "Capital Flow"),
    ("top-sectors.html", "Top Sectors"), ("btc-dominance.html", "Altcoin Rotation"),
    ("leverage-heat.html", "Leverage Heat"), ("stablecoin-liquidity.html", "Stablecoin Liquidity"),
    ("defi-pulse.html", "DeFi Pulse"), ("network-health.html", "Miner Health"),
    ("liquidations.html", "Liquidations"), ("whale-activity.html", "Whale Activity"),
    ("macro-risk.html", "Macro Risk"), ("etf-flow.html", "Bitcoin ETF Flow"),
    ("market-breadth.html", "Market Breadth"), ("narrative-momentum.html", "Narrative Momentum"),
]

GLOSSARY = [
    ("Cold storage", "Keeping crypto keys offline, away from internet-connected devices, to cut the risk of online theft."),
    ("Self-custody", "Holding your own private keys instead of leaving coins with an exchange or custodian."),
    ("DCA", "Dollar-cost averaging: buying a fixed dollar amount on a regular schedule, whatever the price."),
    ("Market cap", "Price per coin multiplied by the number of coins in circulation."),
    ("Hash rate", "The total computing power securing a proof-of-work network such as Bitcoin."),
    ("Halving", "The scheduled event, roughly every four years, that cuts Bitcoin's new-coin issuance in half."),
    ("Stablecoin", "A token designed to hold a steady value, usually pegged to the U.S. dollar."),
    ("Spot ETP", "An exchange-traded product that holds the actual asset, so shares track its price directly."),
    ("Funding rate", "The periodic payment between long and short traders in perpetual futures; a gauge of leverage."),
    ("Liquidation", "A forced closing of a leveraged position when losses exhaust its collateral."),
    ("TVL", "Total value locked: the amount of assets deposited in DeFi protocols."),
    ("Fear &amp; Greed Index", "A composite score of market sentiment, from extreme fear to extreme greed."),
]


def _build_resources():
    hero = (
        '<section class="res-band res-band--black res-hero"><div class="res-inner">'
        '<span class="res-eyebrow">The Play<img class="res-btc" src="assets/email-notable-b.png" alt="B">ack Library</span>'
        '<h1 class="res-hero-title">Resources</h1>'
        '<p class="res-hero-sub">Hand-picked tools, research and reading for retail and institutional investors. Quality over quantity.</p>'
        '<div class="res-legend">'
        '<span class="res-tag res-tag--retail">Retail</span>'
        '<span class="res-tag res-tag--inst">Institutional</span>'
        '<span class="res-tag res-tag--all">All levels</span></div>'
        '<nav class="res-jump" aria-label="Resource sections">'
        '<a href="#start">Start Here</a><a href="#tools">Tools</a><a href="#institutional">Institutional</a>'
        '<a href="#protect">Protect &amp; Plan</a><a href="#reading">Essential Reading</a>'
        '<a href="#signals">Our Signals</a><a href="#glossary">Glossary</a></nav>'
        '</div></section>'
    )
    start = _section("start", "paper", "New to Crypto", "Start Here",
                     "Clear, trustworthy primers from established educators. Read these first.", START_HERE)
    tools = _section("tools", "dark", "Calculators &amp; Data", "Tools &amp; Analytics",
                     "Run the numbers yourself and track the network with live data.", TOOLS)
    inst = _section("institutional", "sand", "Advanced", "Institutional &amp; Advanced",
                    "Market structure, regulation and investment research for professional allocators and serious investors.",
                    INSTITUTIONAL)
    protect = _section("protect", "stone", "Safeguard Your Assets", "Protect &amp; Plan",
                       "Custody, security, taxes and estate planning &mdash; the unglamorous parts that matter most.", PROTECT)

    read_items = "".join(
        f'<a class="res-read-item" href="{url}" target="_blank" rel="noopener noreferrer">'
        f'<span class="res-tag res-tag--topic">{topic}</span>'
        f'<span class="res-read-title">{title}</span><span class="res-read-by">by {author}</span></a>'
        for title, author, topic, url in READING
    )
    reading = (
        '<section class="res-band res-band--dark" id="reading"><div class="res-inner">'
        '<div class="res-head"><span class="res-kicker">The Canon</span>'
        '<h2 class="res-title">Essential Bitcoin Reading</h2>'
        '<p class="res-sub">The long reads Bitcoin investors keep coming back to &mdash; on money, energy, investing and law.</p></div>'
        f'<div class="res-read">{read_items}</div>'
        '<p class="res-more">Curated from <a href="https://bitcoin-resources.com/" target="_blank" rel="noopener noreferrer">bitcoin-resources.com</a>.</p>'
        '</div></section>'
    )

    chips = "".join(f'<a class="res-signal" href="{href}">{label}</a>' for href, label in SIGNALS)
    signals = (
        '<section class="res-band res-band--stone" id="signals"><div class="res-inner">'
        '<div class="res-head"><span class="res-kicker">On This Site</span>'
        '<h2 class="res-title">Know Your Signals</h2>'
        '<p class="res-sub">Every indicator on our dashboard has its own page explaining what it measures and how it is scored.</p></div>'
        f'<div class="res-signals">{chips}</div></div></section>'
    )

    terms = "".join(f'<div class="res-term"><dt>{t}</dt><dd>{d}</dd></div>' for t, d in GLOSSARY)
    glossary = (
        '<section class="res-band res-band--paper" id="glossary"><div class="res-inner">'
        '<div class="res-head"><span class="res-kicker">Plain English</span>'
        '<h2 class="res-title">Glossary</h2>'
        '<p class="res-sub">The terms you will run into most often here and in the newsletter.</p></div>'
        f'<dl class="res-gloss">{terms}</dl>'
        '<p class="res-links">Want more? '
        '<a href="https://bitcoinmagazine.com/bitcoin-glossary" target="_blank" rel="noopener noreferrer">Bitcoin Magazine glossary</a>'
        '<a href="https://www.fidelity.com/learning-center/trading-investing/crypto-definitions" target="_blank" rel="noopener noreferrer">Fidelity crypto definitions</a></p>'
        '<p class="res-note">Links on this page lead to third-party websites and are shared for educational purposes only. '
        'Inclusion is not an endorsement, and some tools require a paid subscription. '
        'Nothing here is financial advice &mdash; see the note at the bottom of every page for the full disclosure.</p>'
        '</div></section>'
    )
    return hero + start + tools + inst + protect + reading + signals + glossary


RESOURCES_BODY = _build_resources()


def build():
    year = datetime.now().year
    with open(os.path.join(ROOT, "about.html"), "w") as f:
        f.write(page("", "About — The Crypto Playback", ABOUT_BODY, year))
    with open(os.path.join(ROOT, "resources.html"), "w") as f:
        f.write(page("", "Resources — The Crypto Playback", RESOURCES_BODY, year))
    print("Built about.html and resources.html")


if __name__ == "__main__":
    build()
