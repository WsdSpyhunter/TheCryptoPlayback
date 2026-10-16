"""quote_story.py - the optional "In their words" story: a direct quote from a public official or
market-moving figure (Federal Reserve, Treasury, White House, regulators, legislators) with a short
take and a link to the news source it came from.

Why it is checked in code: a fabricated or paraphrased quote attributed to a real person is the worst
mistake this newsletter could make. The writer model may only propose a quote that appears
word-for-word in the headline/summary of the ONE news item it cites, and that names the speaker. If
the check fails, the slot is simply dropped (a goal, not a guarantee), and the issue goes out with its
other stories.
"""
import re
from html import escape

from blocked_terms import contains_blocked, mask_blocked

MIN_WORDS, MAX_WORDS = 8, 60


def _norm(text):
    """Lower-case, strip tags, unify quote marks / dashes / whitespace so a verbatim quote still matches
    when the model had to swap double quotes for single quotes."""
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = t.replace("&amp;", "&").replace("&quot;", '"').replace("&#8217;", "'").replace("&#8220;", '"').replace("&#8221;", '"')
    t = re.sub(r"[‘’“”\"'`]", "", t)
    t = re.sub(r"[‒-―]", "-", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def build_quote_story(result, headlines):
    """Returns a story dict (same shape as the other stories) or None. Never raises."""
    q = result.get("quote_story")
    if not isinstance(q, dict):
        return None
    need = ("quote", "speaker", "role", "context", "source_title", "source_url")
    if not all(isinstance(q.get(k), str) and q[k].strip() for k in need):
        return None
    item = next((h for h in headlines if h["link"] == q["source_url"]), None)
    if item is None:
        print("quote_story cited a link not in the headline list - dropping it.")
        return None
    quote = q["quote"].strip().strip("“”\"'")
    words = len(quote.split())
    if not MIN_WORDS <= words <= MAX_WORDS:
        print(f"quote_story quote has {words} words (need {MIN_WORDS}-{MAX_WORDS}) - dropping it.")
        return None
    source_text = _norm(f"{item['headline']} {item['summary']}")
    if _norm(quote) not in source_text:
        print("quote_story quote is not word-for-word in the cited source text - dropping it.")
        return None
    surname = _norm(q["speaker"]).split(" ")[-1]
    if not surname or surname not in source_text:
        print("quote_story speaker is not named in the cited source text - dropping it.")
        return None
    if q["source_url"] in {s.get("source_url") for s in result.get("stories", [])}:
        print("quote_story duplicates one of the main stories - dropping it.")
        return None
    body = f'<p>{escape(q["context"].strip(), quote=False)}</p>'
    take = q.get("take")
    if isinstance(take, str) and take.strip():
        body += f"<p>{escape(take.strip(), quote=False)}</p>"
    story = {
        "headline": f'In Their Words: {q["speaker"].strip()}',
        "body": mask_blocked(body) if contains_blocked(body) else body,
        "quote": {"text": quote, "speaker": q["speaker"].strip(), "role": q["role"].strip()},
        "source_title": q["source_title"].strip(),
        "source_url": q["source_url"].strip(),
        "image_url": item.get("image_url"),
    }
    return story


def insert_quote_story(result, headlines):
    """Adds the quote story as the third story (or last if fewer). Returns True if added."""
    s = build_quote_story(result, headlines)
    if not s:
        return False
    stories = result["stories"]
    stories.insert(min(2, len(stories)), s)
    return True
