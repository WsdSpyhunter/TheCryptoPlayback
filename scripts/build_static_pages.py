"""Run once (or whenever you want to edit About/Resources copy) to regenerate
the two static pages. Unlike index/archive/posts, these are NOT touched by
the daily/weekly automation — edit this file and rerun it by hand."""
import os
from datetime import datetime
from partials import page, SITE_URL
import v2_ui as ui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ABOUT_BODY = """<section class="v2-ind-hero" aria-labelledby="about-h">
  <div class="v2-wrap">
    <nav class="v2-crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a><span aria-hidden="true">›</span><span aria-current="page">About</span></nav>
    <div class="v2-kicker v2-kicker-brass v2-ind-kicker">One stop. One look.</div>
    <h1 class="v2-ind-title" id="about-h">About The Crypto Playback</h1>
    <p class="v2-arch-sub">Your trusted source for efficient Bitcoin and crypto news and data.</p>
  </div>
</section>
<section class="v2-section v2-ind-body">
  <div class="v2-wrap v2-about">
    <article class="v2-ind-card v2-about-card">
      <p>The website and newsletter both offer a quick scan of the top headlines plus deep, high-value data. All in one place, on a single page, free for subscribers.</p>
      <p>No more spending your day scrolling Crypto Twitter or hunting across multiple sites for the information you need.</p>
      <p>One stop. One look. A quick Crypto Playback and you&rsquo;re fully informed on the fastest-moving industry on the planet.</p>
      <p class="v2-about-note">Nothing here is financial advice. See the note at the bottom of every page for the full disclosure.</p>
    </article>
    <div class="v2-about-tiles">
      <a class="v2-about-tile" href="archive.html"><span>The briefing</span><strong>Daily and weekly issues</strong><em>Browse the archive &rarr;</em></a>
      <a class="v2-about-tile" href="index.html#alerts"><span>The data</span><strong>16 live indicators</strong><em>See the dashboard &rarr;</em></a>
      <a class="v2-about-tile" href="playback-lab.html"><span>The research</span><strong>The Playback Lab</strong><em>Open the Lab &rarr;</em></a>
    </div>
    <article class="v2-ind-card v2-about-card" id="contact">
      <h2>Contact</h2>
      <p>Questions, tips, or feedback: <a href="mailto:info@cryptoplayback.com">info@cryptoplayback.com</a></p>
    </article>
    <p class="v2-ind-sub"><a class="v2-btn v2-btn-navy" href="index.html#subscribe">Get the daily playback free</a></p>
  </div>
</section>"""


TERMS_SECTIONS = [
    ("Using this site", """<p>These terms apply to cryptoplayback.com, The Crypto Playback newsletter, and the Playback Lab (together, the &ldquo;Service&rdquo;), operated by The Crypto Playback (&ldquo;we&rdquo;, &ldquo;us&rdquo;). By using the Service you agree to them. If you do not agree, please do not use it.</p>"""),
    ("Not financial advice", """<p>Everything in the Service is independent market research and commentary for general information only. It is not investment, financial, tax or legal advice, and it is not an offer or solicitation to buy or sell anything. Indicators describe market conditions as measured by third-party data; they are not forecasts, and past readings do not predict future results. Do your own research and consult a licensed, qualified advisor before making any investment decision. You are solely responsible for your decisions.</p>"""),
    ("Our content and copyright", """<p>The Service, including its text, newsletters, indicator pages, the Playback Lab, charts, page design, software and artwork, is protected by copyright and other laws. Unless a page says otherwise, &copy; The Crypto Playback. All rights reserved.</p>
<p>You may read, share links to, and quote short excerpts of our content for personal, non-commercial use, with attribution and a link back to the original page. You may not, without our written permission: copy, republish or redistribute our content or any substantial part of it; scrape or harvest the Service by automated means; build a competing product or database from it; or use it to train machine-learning models.</p>"""),
    ("Trademarks", """<p>&ldquo;The Crypto Playback&rdquo;, &ldquo;Playback Lab&rdquo;, &ldquo;The Playback Read&rdquo;, the PlayBack wordmark and our mascot are trademarks or branding of The Crypto Playback. Other names, logos and marks on the Service belong to their respective owners, and their appearance does not imply endorsement.</p>"""),
    ("The Playback Lab and our indicators", """<p>Our indicators and scores (for example the Institutional Positioning Index, Basis-Trade Crowding, Miner Stress, Net Liquidity &amp; Macro, Crowded Unwind Risk, Stablecoin Flows and The Playback Read) are our own composite measures, calculated from third-party and public data. We publish methodology so readers can understand how they work. Publishing it does not give you a licence to copy our pages, scores or presentation, or to present them as your own.</p>"""),
    ("Third-party data, links and promotions", """<p>We rely on data and news from third parties and cannot guarantee that it is accurate, complete or timely; it can be delayed, revised or wrong. Their own terms apply to their data. The Service links to third-party sites, which we do not control. Some items, such as featured shows or sponsored placements, may be promotions. We label paid sponsorships as such. Inclusion of any resource is not an endorsement.</p>"""),
    ("Newsletter", """<p>If you subscribe, we will email you our newsletter. You can unsubscribe at any time using the link in every email. Emails are delivered through a third-party email provider.</p>"""),
    ("No warranty; limit of liability", """<p>The Service is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;, without warranties of any kind, express or implied. To the fullest extent permitted by law, we are not liable for any loss or damage (including trading or investment losses) arising from your use of, or reliance on, the Service.</p>"""),
    ("Changes and contact", """<p>We may update these terms from time to time; the effective date below shows the latest version, and continued use means you accept the changes. These terms are governed by the laws of the State of Tennessee, without regard to its conflict-of-law rules. Questions: <a href="mailto:info@cryptoplayback.com">info@cryptoplayback.com</a>.</p>
<p class="v2-about-note">Effective October 9, 2026.</p>"""),
]

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


TAG_CLS = {"R": "retail", "I": "inst", "A": "all"}
SEC_ICONS = {"start": "book", "tools": "network_health", "institutional": "structure", "protect": "risk_radar",
             "reading": "news", "listen": "mic", "signals": "alerts", "glossary": "book"}


def _card(source, title, desc, url, tag):
    cls, label = TAG_CLS[tag], TAGS[tag][1]
    # External links open in a new tab; links to our own pages stay put.
    target = ' target="_blank" rel="noopener noreferrer"' if url.startswith("http") else ""
    return (
        f'<a class="v2-res-card" href="{url}"{target}>'
        f'<span class="v2-res-top"><span class="v2-res-source">{source}</span><span class="v2-res-tag v2-res-{cls}">{label}</span></span>'
        f'<h3>{title}</h3><p>{desc}</p><span class="v2-res-go">Visit &rarr;</span></a>'
    )


def _section(sec_id, band, kicker, title, sub, cards, extra=""):
    white = " v2-section-white" if band in ("white", "paper") else ""
    return (
        f'<section class="v2-section{white}" id="{sec_id}" aria-labelledby="{sec_id}-h"><div class="v2-wrap">'
        f'{ui.title_box(SEC_ICONS[sec_id], f"<span id=\'{sec_id}-h\'>{title}</span>", kicker)}'
        f'<p class="v2-lead">{sub}</p>'
        f'<div class="v2-res-grid">{"".join(_card(*c) for c in cards)}</div>{extra}</div></section>'
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
        '<section class="v2-ind-hero" aria-labelledby="res-h"><div class="v2-wrap">'
        '<nav class="v2-crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a><span aria-hidden="true">›</span><span aria-current="page">Resources</span></nav>'
        '<div class="v2-kicker v2-kicker-brass v2-ind-kicker">Hand-picked. Quality over quantity.</div>'
        '<h1 class="v2-ind-title" id="res-h">Resources</h1>'
        '<p class="v2-arch-sub">Tools, research and reading for retail and institutional investors.</p>'
        '<div class="v2-res-legend"><span class="v2-res-tag v2-res-retail">Retail</span><span class="v2-res-tag v2-res-inst">Institutional</span><span class="v2-res-tag v2-res-all">All levels</span></div>'
        '<nav class="pro-jump" aria-label="Resource sections"><a href="#start">Start Here</a><a href="#tools">Tools</a><a href="#institutional">Institutional</a>'
        '<a href="#protect">Protect &amp; Plan</a><a href="#reading">Essential Reading</a><a href="#listen">Listen</a><a href="#signals">Our Signals</a><a href="#glossary">Glossary</a></nav>'
        '</div></section>'
    )
    start = _section("start", "ivory", "New to Crypto", "Start Here",
                     "Clear, trustworthy primers from established educators. Read these first.", START_HERE)
    tools = _section("tools", "white", "Calculators &amp; Data", "Tools &amp; Analytics",
                     "Run the numbers yourself and track the network with live data.", TOOLS)
    inst = _section("institutional", "ivory", "Advanced", "Institutional &amp; Advanced",
                    "Market structure, regulation and investment research for professional allocators and serious investors.",
                    INSTITUTIONAL)
    protect = _section("protect", "white", "Safeguard Your Assets", "Protect &amp; Plan",
                       "Custody, security, taxes and estate planning &mdash; the unglamorous parts that matter most.", PROTECT)

    read_items = "".join(
        f'<a class="v2-res-read" href="{url}" target="_blank" rel="noopener noreferrer">'
        f'<span class="v2-res-tag v2-res-topic">{topic}</span>'
        f'<span class="v2-res-read-title">{title}</span><span class="v2-res-read-by">by {author}</span></a>'
        for title, author, topic, url in READING
    )
    reading = (
        '<section class="v2-section" id="reading" aria-labelledby="reading-h"><div class="v2-wrap">'
        f'{ui.title_box(SEC_ICONS["reading"], "<span id=\'reading-h\'>Essential Bitcoin Reading</span>", "The Canon")}'
        '<p class="v2-lead">The long reads Bitcoin investors keep coming back to &mdash; on money, energy, investing and law.</p>'
        f'<div class="v2-res-readlist">{read_items}</div>'
        '<p class="v2-res-more">Curated from <a href="https://bitcoin-resources.com/" target="_blank" rel="noopener noreferrer">bitcoin-resources.com</a>.</p>'
        '</div></section>'
    )

    spotify = "https://open.spotify.com/show/03UqgZlYo6VpsfuUrCZlN2?si=0c4aad0b22a348c8"
    listen = (
        '<section class="v2-section v2-section-white" id="listen" aria-labelledby="listen-h"><div class="v2-wrap">'
        f'{ui.title_box(SEC_ICONS["listen"], "<span id=\'listen-h\'>Listen</span>", "Podcasts")}'
        '<p class="v2-lead">Bitcoin and markets, in your ears. Shows we like and recommend.</p>'
        f'<a class="v2-res-feature" href="{spotify}" target="_blank" rel="noopener noreferrer">'
        '<img class="v2-res-feature-img" src="assets/resources/the-money-block-thumb.jpg" width="520" height="287" '
        'alt="The Money Block with Matthew J. Moore: Bitcoin and markets, featured on BizTV and Biz Talk Radio" loading="lazy">'
        '<span class="v2-res-feature-body">'
        '<span class="v2-res-top"><span class="v2-res-source">Spotify &middot; Podcast</span><span class="v2-res-tag v2-res-all">All levels</span></span>'
        '<h3>The Money Block</h3>'
        '<span class="v2-res-feature-by">with Matthew J. Moore</span>'
        '<p>A weekly Bitcoin and money show on BizTV and Biz Talk Radio, Saturdays at 3 PM ET. Clear conversation on Bitcoin, markets and what moves them.</p>'
        '<span class="v2-res-go">Listen on Spotify &rarr;</span></span></a>'
        '</div></section>'
    )

    chips = "".join(f'<a href="{href}">{label}</a>' for href, label in SIGNALS)
    signals = (
        '<section class="v2-section" id="signals" aria-labelledby="signals-h"><div class="v2-wrap">'
        f'{ui.title_box(SEC_ICONS["signals"], "<span id=\'signals-h\'>Know Your Signals</span>", "On This Site")}'
        '<p class="v2-lead">Every indicator on our dashboard has its own page explaining what it measures and how it is scored. '
        'For deeper market-structure research, see the <a href="playback-lab.html">Playback Lab</a>.</p>'
        f'<div class="v2-ind-chips v2-res-chips">{chips}</div></div></section>'
    )

    terms = "".join(f'<div class="v2-res-term"><dt>{t}</dt><dd>{d}</dd></div>' for t, d in GLOSSARY)
    glossary = (
        '<section class="v2-section v2-section-white" id="glossary" aria-labelledby="glossary-h"><div class="v2-wrap">'
        f'{ui.title_box(SEC_ICONS["glossary"], "<span id=\'glossary-h\'>Glossary</span>", "Plain English")}'
        '<p class="v2-lead">The terms you will run into most often here and in the newsletter.</p>'
        f'<dl class="v2-res-gloss">{terms}</dl>'
        '<p class="v2-res-more">Want more? '
        '<a href="https://bitcoinmagazine.com/bitcoin-glossary" target="_blank" rel="noopener noreferrer">Bitcoin Magazine glossary</a> &middot; '
        '<a href="https://www.fidelity.com/learning-center/trading-investing/crypto-definitions" target="_blank" rel="noopener noreferrer">Fidelity crypto definitions</a></p>'
        '<p class="v2-ind-note">Links on this page lead to third-party websites and are shared for educational purposes only. '
        'Inclusion is not an endorsement, and some tools require a paid subscription. '
        'Nothing here is financial advice &mdash; see the note at the bottom of every page for the full disclosure.</p>'
        '</div></section>'
    )
    return hero + start + tools + inst + protect + reading + listen + signals + glossary


RESOURCES_BODY = _build_resources()


def _crumbs_ld(*items):
    import json
    return json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{SITE_URL}/{u}"} for i, (n, u) in enumerate(items)]},
        separators=(",", ":"))


def _build_terms():
    cards = "".join(f'<article class="v2-ind-card v2-about-card"><h2>{h}</h2>{b}</article>' for h, b in TERMS_SECTIONS)
    return (
        '<section class="v2-ind-hero" aria-labelledby="terms-h"><div class="v2-wrap">'
        '<nav class="v2-crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a><span aria-hidden="true">›</span><span aria-current="page">Terms of Use</span></nav>'
        '<div class="v2-kicker v2-kicker-brass v2-ind-kicker">The fine print</div>'
        '<h1 class="v2-ind-title" id="terms-h">Terms of Use</h1>'
        '<p class="v2-arch-sub">Plain-English terms for using The Crypto Playback, the newsletter and the Playback Lab.</p>'
        '</div></section>'
        f'<section class="v2-section v2-ind-body"><div class="v2-wrap v2-about">{cards}</div></section>'
    )


TERMS_BODY = _build_terms()


def build():
    import build_site
    year = datetime.now().year
    links = build_site._footer_indicator_links()
    with open(os.path.join(ROOT, "about.html"), "w") as f:
        f.write(page("", "About The Crypto Playback | Bitcoin & Crypto Research", ABOUT_BODY, year, theme="v2", indicator_links=links,
                     description="The Crypto Playback is a free daily and weekly briefing on Bitcoin and crypto: top headlines, 16 live indicators and the Playback Lab.",
                     path="about.html", jsonld=_crumbs_ld(("Home", ""), ("About", "about.html"))))
    with open(os.path.join(ROOT, "resources.html"), "w") as f:
        f.write(page("", "Crypto Resources & Glossary | The Crypto Playback", RESOURCES_BODY, year, theme="v2", indicator_links=links,
                     description="Hand-picked crypto tools, research, essential Bitcoin reading and a plain-English glossary for retail and institutional investors.",
                     path="resources.html", jsonld=_crumbs_ld(("Home", ""), ("Resources", "resources.html"))))
    with open(os.path.join(ROOT, "terms.html"), "w") as f:
        f.write(page("", "Terms of Use | The Crypto Playback", TERMS_BODY, year, theme="v2", indicator_links=links,
                     description="Terms of use for The Crypto Playback: copyright, trademarks, data and indicators, and not-financial-advice notice.",
                     path="terms.html", jsonld=_crumbs_ld(("Home", ""), ("Terms of Use", "terms.html"))))
    print("Built about.html, resources.html and terms.html")


if __name__ == "__main__":
    build()
