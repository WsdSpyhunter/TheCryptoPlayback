"""
blocked_terms.py - names Buttondown refuses to publish (it rejects the email
with "contains prohibited word"). Found so far: Bitget. Add a new entry the
moment Buttondown rejects another word - nothing else needs to change.

The story is still told; the NAME is replaced by a generic description:

  1. sanitize_headlines(): before the writer model sees a news item, a blocked
     name in its headline/summary/source is swapped for the generic phrase, so
     the model writes "a $387M hack of a large overseas crypto exchange"
     instead of naming it. A blocked name in an image URL just drops the image.
  2. The prompt tells the model to use the generic wording and never reveal or
     guess the name.
  3. mask_result(): backstop - if the model writes the name anyway, it's swapped.
  4. neutralize_links(): the source link of such a story often contains the
     name (e.g. ".../bitget-hack-north-korea"), and the email body is scanned
     including links - so those links go through a small redirect page on our
     own site (go/<id>.html) that forwards the reader to the real article.
"""
import hashlib
import html
import os
import re

# name -> the generic phrase that stands in for it. Pick a phrase that is
# true of the company (the wording is read by subscribers).
BLOCKED_TERMS = {
    "Bitget": "a large overseas crypto exchange",
}
SITE_URL = "https://cryptoplayback.com"

_PATTERN = re.compile("|".join(re.escape(t) for t in BLOCKED_TERMS), re.IGNORECASE)
_LOOKUP = {t.lower(): phrase for t, phrase in BLOCKED_TERMS.items()}


def _generic(match):
    return _LOOKUP[match.group(0).lower()]


def contains_blocked(text):
    return bool(text) and bool(_PATTERN.search(text))


def mask_blocked(text):
    return _PATTERN.sub(_generic, text)


def sanitize_headlines(headlines):
    """Swaps blocked names for their generic phrase in the text the model will
    read; strips a blocked image URL. The real `link` is kept untouched (it is
    needed to cite the source and is handled by neutralize_links later).
    Returns (new_list, how_many_items_changed)."""
    out, changed = [], 0
    for h in headlines:
        h = dict(h)
        touched = False
        for key in ("headline", "summary", "source"):
            if contains_blocked(h.get(key)):
                h[key] = mask_blocked(h[key])
                touched = True
        if contains_blocked(h.get("image_url") or ""):
            h["image_url"] = None
            touched = True
        changed += touched
        out.append(h)
    return out, changed


def mask_result(result):
    """Backstop: swaps a blocked name the model wrote anyway in WRITTEN text
    (titles, intro, stories, missed story). Returns the number of swaps."""
    count = 0

    def fix(value):
        nonlocal count
        if isinstance(value, str):
            new, n = _PATTERN.subn(_generic, value)
            count += n
            return new
        return value

    for key in ("issue_title", "intro"):
        if key in result:
            result[key] = fix(result[key])
    for story in result.get("stories", []):
        for key in ("headline", "body", "source_title"):
            if key in story:
                story[key] = fix(story[key])
    missed = result.get("missed_story")
    if isinstance(missed, dict):
        for key in ("headline", "body", "source_title"):
            if key in missed:
                missed[key] = fix(missed[key])
    return count


def redirect_url(url, root):
    """Writes go/<id>.html under `root` (a tiny page that forwards to `url`)
    and returns its public address on our site."""
    ident = hashlib.sha1(url.encode()).hexdigest()[:12]
    go_dir = os.path.join(root, "go")
    os.makedirs(go_dir, exist_ok=True)
    safe = html.escape(url, quote=True)
    page = (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0;url={safe}">'
        '<meta name="robots" content="noindex,nofollow">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Taking you to the article…</title></head>'
        '<body style="font-family:Arial,sans-serif;text-align:center;padding:48px 16px;">'
        f'<p>Taking you to the article… <a href="{safe}">Tap here if nothing happens.</a></p>'
        f'<script>location.replace({html.escape(repr(url), quote=True)});</script>'
        '</body></html>'
    )
    with open(os.path.join(go_dir, f"{ident}.html"), "w") as f:
        f.write(page)
    return f"{SITE_URL}/go/{ident}.html"


def neutralize_links(result, root):
    """Routes any story/missed-story source link that contains a blocked name
    through a redirect page. Returns how many links were rerouted."""
    count = 0
    targets = list(result.get("stories", []))
    if isinstance(result.get("missed_story"), dict):
        targets.append(result["missed_story"])
    for item in targets:
        url = item.get("source_url") or ""
        if contains_blocked(url):
            item["source_url"] = redirect_url(url, root)
            count += 1
        if contains_blocked(item.get("image_url") or ""):
            item["image_url"] = None
    return count
