"""
story_images.py - makes sure every story image in an issue actually loads.

RSS feeds sometimes hand us an image address that is dead (2026-10-07: CoinDesk
sent a ".jpg" URL its image host answers with 404 - the email showed a broken
image icon). Before an issue is built, each story's image is checked the way a
mail app would fetch it. If it fails, the article's own page is read for its
og:image (the picture the publisher itself uses) and that is tried instead; if
nothing works the story simply goes out without an image.
"""
import html
import re
from urllib.parse import urljoin

import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
MIN_BYTES = 3000  # smaller than this is a placeholder/tracking pixel, not a picture


def image_ok(url, timeout=20):
    """True if the URL answers 200 with an image content type and real bytes."""
    try:
        with requests.get(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"},
                          timeout=timeout, stream=True) as resp:
            if resp.status_code != 200:
                return False
            if not resp.headers.get("Content-Type", "").lower().startswith("image/"):
                return False
            got = 0
            for chunk in resp.iter_content(1024):
                got += len(chunk)
                if got >= MIN_BYTES:
                    return True
            return False
    except requests.RequestException:
        return False


def page_image(page_url, timeout=25):
    """The article's own og:image / twitter:image, or None."""
    try:
        resp = requests.get(page_url, headers={"User-Agent": UA}, timeout=timeout)
        if resp.status_code != 200:
            return None
        head = resp.text[:900_000]
    except requests.RequestException:
        return None
    for prop in ("og:image", "twitter:image"):
        for pattern in (
            r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*content=["\']([^"\']+)["\']' % prop,
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']%s["\']' % prop,
        ):
            m = re.search(pattern, head, re.IGNORECASE)
            if m:
                return urljoin(page_url, html.unescape(m.group(1)))
    return None


def fix_story_images(stories, log=print):
    """Checks every story's image in place. Returns (fixed, dropped)."""
    fixed = dropped = 0
    for story in stories:
        url = story.get("image_url")
        if not url or image_ok(url):
            continue
        alt = page_image(story.get("source_url", ""))
        if alt and image_ok(alt):
            log(f"Image for '{story['headline'][:50]}' was dead - using the article's own image.")
            story["image_url"] = alt
            fixed += 1
        else:
            log(f"Image for '{story['headline'][:50]}' was dead and no replacement worked - sending without an image.")
            story["image_url"] = None
            dropped += 1
    return fixed, dropped
