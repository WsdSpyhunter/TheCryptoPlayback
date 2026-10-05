"""
blocked_terms.py - words Buttondown refuses to publish (it rejects the email
with "contains prohibited word"). Found so far: Bitget. Add new ones here the
moment Buttondown rejects another - nothing else needs to change.

Two layers keep them out of every issue:
  1. filter_headlines(): a news item that mentions a blocked word (in its
     headline, summary, link or image URL) is never shown to the writer model,
     so it can't be picked as a story.
  2. mask_result(): last line of defense - if the model still writes one
     (from its own knowledge), it is swapped for a generic phrase.
"""
import re

BLOCKED_TERMS = ["Bitget"]
REPLACEMENT = "a major crypto exchange"

_PATTERN = re.compile("|".join(re.escape(t) for t in BLOCKED_TERMS), re.IGNORECASE)


def contains_blocked(text):
    return bool(text) and bool(_PATTERN.search(text))


def mask_blocked(text):
    return _PATTERN.sub(REPLACEMENT, text)


def filter_headlines(headlines):
    """Drops news items that mention a blocked word; strips a blocked image
    URL (keeps the story). Returns (kept, dropped_count)."""
    kept, dropped = [], 0
    for h in headlines:
        blob = " ".join(str(h.get(k) or "") for k in ("headline", "summary", "link", "source"))
        if contains_blocked(blob):
            dropped += 1
            continue
        if contains_blocked(h.get("image_url") or ""):
            h = {**h, "image_url": None}
        kept.append(h)
    return kept, dropped


def mask_result(result):
    """Masks blocked words in every piece of WRITTEN text in the model's
    result (titles, intro, stories, missed story). Links are left alone - the
    input filter already keeps blocked words out of them. Returns how many
    replacements were made."""
    count = 0

    def fix(value):
        nonlocal count
        if isinstance(value, str):
            new, n = _PATTERN.subn(REPLACEMENT, value)
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
