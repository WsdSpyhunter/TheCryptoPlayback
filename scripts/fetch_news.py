"""
fetch_news.py — pulls recent headlines from crypto news RSS feeds.
No API key needed — RSS is public and free.
"""
import feedparser
from datetime import datetime, timezone, timedelta

FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "Bitcoin Magazine": "https://bitcoinmagazine.com/.rss/full/",
    "The Block": "https://www.theblock.co/rss.xml",
}


def get_recent_headlines(hours=36, max_per_feed=8):
    """Returns a list of {headline, summary, link, source, published} dicts,
    newest first, from the last `hours` hours across all feeds."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items = []
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"WARNING: failed to fetch {source}: {e}")
            continue
        for entry in feed.entries[:max_per_feed]:
            published = None
            if getattr(entry, "published_parsed", None):
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published and published < cutoff:
                continue
            items.append({
                "headline": entry.get("title", "").strip(),
                "summary": entry.get("summary", "")[:400],
                "link": entry.get("link", ""),
                "source": source,
                "published": published.isoformat() if published else None,
            })
    items.sort(key=lambda x: x["published"] or "", reverse=True)
    return items


if __name__ == "__main__":
    import json
    print(json.dumps(get_recent_headlines(), indent=2))
