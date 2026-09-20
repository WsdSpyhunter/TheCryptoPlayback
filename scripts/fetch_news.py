"""
fetch_news.py — pulls recent headlines from crypto news RSS feeds.
No API key needed — RSS is public and free.

Also pulls an image URL per story when the feed provides one (most do, via
the media:content or media:thumbnail RSS extensions, or an enclosure tag).
If a feed doesn't include one for a given story, image_url is just None —
the site/email templates already handle that case by skipping the image.
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


def _extract_image_url(entry):
    """Try the common RSS image extensions, in order, and return the first
    real image URL found. Returns None if the feed didn't include one."""
    if getattr(entry, "media_thumbnail", None):
        return entry.media_thumbnail[0].get("url")
    if getattr(entry, "media_content", None):
        return entry.media_content[0].get("url")
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            return enc.get("href") or enc.get("url")
    summary = entry.get("summary", "")
    if "<img" in summary:
        start = summary.find('src="')
        if start != -1:
            start += len('src="')
            end = summary.find('"', start)
            if end != -1:
                return summary[start:end]
    return None


def get_recent_headlines(hours=36, max_per_feed=8):
    """Returns a list of {headline, summary, link, source, published, image_url}
    dicts, newest first, from the last `hours` hours across all feeds.
    image_url is None when the feed didn't provide one for that story."""
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
                "image_url": _extract_image_url(entry),
            })
    items.sort(key=lambda x: x["published"] or "", reverse=True)
    return items


if __name__ == "__main__":
    import json
    print(json.dumps(get_recent_headlines(), indent=2))
