"""
generate_issue.py — shared multi-story issue generator for both the daily
and weekly Playback posts. Both now pick a handful of the most significant,
distinct stories from their respective windows and write a short take on
each — the only real differences between them are the model, the story-count
range, and how far back they look for headlines, so that's what's
parameterized here rather than duplicated across two files.

Publishes the post to the site (via build_site.py) and creates the matching
Buttondown draft (never sends — see buttondown_client.py).
"""
import sys
from datetime import datetime, timezone

from fetch_prices import get_top_prices
from fetch_news import get_recent_headlines
from fetch_sentiment import get_fear_greed
from claude_client import ask_claude_json
from build_site import (
    add_post_and_rebuild, render_ticker_bar, render_sentiment_combined,
    render_issue_pill, render_top_story_box, compute_biggest_mover, load_index,
    save_gauge_image, format_date_abbrev,
)
from email_render import stories_to_plain_email_html, upload_gauge_image
from buttondown_client import create_draft


def build_system_prompt(story_min, story_max, cadence_label):
    preferred_floor = min(story_min + 1, story_max)
    return f"""You are the writer for "The Crypto Playback," a Bitcoin/crypto \
newsletter. Your voice: informed, a little wry, willing to share an opinion, \
but you NEVER give financial advice or tell readers what to buy/sell. You are \
given real headlines from {cadence_label}, each with a source, a summary, a \
link, and sometimes an image URL. Select between {story_min} and {story_max} \
of the most genuinely significant, distinct stories — as many as the real \
news actually warrants. Prefer the higher end of that range \
({preferred_floor}-{story_max}) when there's enough substantive, distinct \
news to support it; only drop toward the {story_min}-story floor on a \
genuinely quiet stretch. Never pad with minor or duplicate stories just to \
hit a higher count. For each story, write a short summary plus a sentence or \
two of personal take/analysis — this is exactly the format of the original \
Crypto Playback newsletter (news item, then "here's what I think about it").

Rules:
- Base every fact ONLY on the headlines/summaries given to you. Never invent \
  numbers, quotes, or events not present in the source material.
- Base each story ENTIRELY on the ONE headline/summary you cite for it — do \
  not pull in facts from other headlines in the list, even true ones, once \
  you've picked a story.
- Choose a genuinely diverse set of stories (regulatory, market, adoption, \
  technology, culture) rather than several versions of the same story.
- Never phrase anything as investment advice or a prediction of what to do \
  with money.
- Write a one-sentence intro for the whole issue (a framing line for what's \
  happening right now).
- "issue_title" must NOT include the words "The Crypto Playback" — the brand \
  name is already shown separately in the header and subject line. Write \
  just the punchy theme (e.g. "Clarity Act RIP, Bitcoin Says Hi").
- For each story, if its headline has an image URL listed, copy it EXACTLY \
  into that story's "image_url". Never invent or guess an image URL. If a \
  headline has no image URL listed, set that story's "image_url" to null.
- CRITICAL for valid output: never use a literal double-quote character (") \
  inside any string value. If you need quotation marks for HTML attributes, \
  use single quotes (e.g. <a href='...'>). If you need to quote a phrase in \
  your writing, use single quotes ('like this') instead of double quotes.

Respond with ONLY a JSON object, no markdown fences, no other text:
{{
  "issue_title": "a short title for this issue (no brand name in it)",
  "intro": "one sentence framing the issue",
  "stories": [
    {{
      "headline": "punchy headline, your own words",
      "body": "1-2 paragraphs: summary + your take, as HTML with <p> tags",
      "source_title": "exact source name from the list",
      "source_url": "exact link from the list",
      "image_url": "exact image URL from the list for this headline, or null"
    }}
  ]
}}"""


def build_user_prompt(headlines, cadence_label, max_headlines):
    lines = []
    for h in headlines[:max_headlines]:
        img_note = f" [image: {h['image_url']}]" if h.get("image_url") else " [image: none]"
        lines.append(f"- [{h['source']}] {h['headline']}: {h['summary']} ({h['link']}){img_note}")
    return f"Headlines from {cadence_label}:\n" + "\n".join(lines)


def clean_issue_title(title):
    """Defensive backstop: strip a leading brand-name prefix if the model
    includes it anyway, so the subject/headline never doubles up."""
    prefixes = ["the crypto playback:", "the crypto playback -", "the crypto playback —"]
    stripped = title.strip()
    lower = stripped.lower()
    for p in prefixes:
        if lower.startswith(p):
            stripped = stripped[len(p):].strip()
            break
    return stripped


def generate_issue(model, tag, slug_suffix, cadence_label, headlines_hours,
                    max_per_feed, max_headlines, story_min, story_max, max_tokens=8000):
    """Generates one issue (daily or weekly — same shape now, just different
    cadence/model/story-count knobs), publishes it to the site, and creates
    the matching Buttondown draft. Exits early (code 1) if there isn't
    enough real news to hit the story-count floor, rather than publish a
    thin issue."""
    prices = get_top_prices()
    headlines = get_recent_headlines(hours=headlines_hours, max_per_feed=max_per_feed)
    if len(headlines) < story_min:
        print(f"Only {len(headlines)} headlines found (need at least {story_min}) — "
              f"aborting rather than publishing a thin issue.")
        sys.exit(1)

    system_prompt = build_system_prompt(story_min, story_max, cadence_label)
    user_prompt = build_user_prompt(headlines, cadence_label, max_headlines)
    result = ask_claude_json(model, system_prompt, user_prompt, max_tokens=max_tokens)
    result["issue_title"] = clean_issue_title(result["issue_title"])

    fng = get_fear_greed()
    mover = compute_biggest_mover(prices)
    issue_number = sum(1 for e in load_index() if e["tag"] == tag) + 1

    now = datetime.now(timezone.utc)
    date_display = now.strftime("%B %d, %Y")
    date_abbrev = format_date_abbrev(now)
    slug = now.strftime("%Y-%m-%d") + slug_suffix
    gauge_path = save_gauge_image(fng["value"], slug)
    post = {
        "slug": slug,
        "title": result["issue_title"],
        "date_display": date_display,
        "tag": tag,
        "issue_number": issue_number,
        "gauge_path": gauge_path,
        "ticker_html": render_ticker_bar(prices, date_abbrev),
        "sentiment_html": render_sentiment_combined(fng, mover, tag),
        "issue_pill_html": render_issue_pill(tag),
        "top_story_html": render_top_story_box(result["intro"]),
        "stories": result["stories"],
        "excerpt": result["intro"][:220],
    }
    add_post_and_rebuild(post)
    print(f"Generated {tag.lower()} post: {slug} ({len(result['stories'])} stories)")

    email_body = stories_to_plain_email_html(
        result["issue_title"], result["intro"], result["stories"], prices,
        fng, mover, tag, date_display, date_abbrev, issue_number, upload_gauge_image(gauge_path),
    )
    draft = create_draft(f"The Crypto Playback — {result['issue_title']}", email_body)
    print(f"Created Buttondown draft: {draft.get('id', '(no id returned)')}")
