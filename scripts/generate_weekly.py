"""
generate_weekly.py — the flagship weekly Playback: 5-7 stories from the
past week, each with a short summary + your editorial take, plus the price
ticker. Mirrors the original newsletter's format exactly.

Model: Sonnet (holds voice/quality across a longer, multi-story piece better
than Haiku — see notes on when to reconsider this in README.md).

Also creates a DRAFT (never sends) in Buttondown, so the email version is
ready the moment you approve the site post.
"""
import sys
from datetime import datetime, timezone

from fetch_prices import get_top_prices
from fetch_news import get_recent_headlines
from claude_client import ask_claude_json
from build_site import add_post_and_rebuild, render_ticker
from buttondown_client import create_draft

MODEL = "claude-sonnet-5"
STORY_COUNT_MIN, STORY_COUNT_MAX = 5, 7

SYSTEM_PROMPT = f"""You are the writer for "The Crypto Playback," a weekly \
Bitcoin/crypto newsletter. Your voice: informed, a little wry, willing to \
share an opinion, but you NEVER give financial advice or tell readers what \
to buy/sell. You are given real headlines from the past week. Select the \
{STORY_COUNT_MIN}-{STORY_COUNT_MAX} most significant, and for each write a \
short summary plus a sentence or two of personal take/analysis — this is \
exactly the format of the original Crypto Playback newsletter (news item, \
then "here's what I think about it").

Rules:
- Base every fact ONLY on the headlines/summaries given to you. Never invent \
  numbers, quotes, or events not present in the source material.
- Base each story ENTIRELY on the ONE headline/summary you cite for it — do \
  not pull in facts from other headlines in the list, even true ones, once \
  you've picked a story.
- Choose a genuinely diverse set of stories (regulatory, market, adoption, \
  technology, culture) rather than 7 versions of the same story.
- Never phrase anything as investment advice or a prediction of what to do \
  with money.
- Write a one-sentence intro for the whole issue (a "this week in crypto" framing line).
- CRITICAL for valid output: never use a literal double-quote character (") \
  inside any string value. If you need quotation marks for HTML attributes, \
  use single quotes (e.g. <a href='...'>). If you need to quote a phrase in \
  your writing, use single quotes ('like this') instead of double quotes.

Respond with ONLY a JSON object, no markdown fences, no other text:
{{
  "issue_title": "a short title for this week's issue",
  "intro": "one sentence framing the week",
  "stories": [
    {{
      "headline": "punchy headline, your own words",
      "body": "1-2 paragraphs: summary + your take, as HTML with <p> tags",
      "source_title": "exact source name from the list",
      "source_url": "exact link from the list"
    }}
  ]
}}"""


def build_user_prompt(headlines):
    lines = [
        f"- [{h['source']}] {h['headline']}: {h['summary']} ({h['link']})"
        for h in headlines[:60]
    ]
    return "Headlines from the past week:\n" + "\n".join(lines)


def stories_to_plain_email_html(issue_title, intro, stories, ticker_prices):
    """A simpler HTML rendering for the email body (Buttondown handles its
    own layout/branding chrome around this)."""
    price_line = " &middot; ".join(
        f"{c['symbol']} ${c['price']:,.2f} ({c['change_24h']:+.1f}%)" for c in ticker_prices
    )
    parts = [f"<p><em>{intro}</em></p>", f"<p><strong>{price_line}</strong></p><hr>"]
    for s in stories:
        parts.append(f"<h3>{s['headline']}</h3>{s['body']}"
                      f"<p><a href='{s['source_url']}'>Read more at {s['source_title']}</a></p><hr>")
    return "\n".join(parts)


def main():
    prices = get_top_prices()
    headlines = get_recent_headlines(hours=24 * 7, max_per_feed=15)
    if len(headlines) < STORY_COUNT_MIN:
        print("Not enough headlines this week — aborting rather than publishing a thin issue.")
        sys.exit(1)

    result = ask_claude_json(MODEL, SYSTEM_PROMPT, build_user_prompt(headlines), max_tokens=6000)

    now = datetime.now(timezone.utc)
    slug = now.strftime("%Y-%m-%d") + "-weekly"
    post = {
        "slug": slug,
        "title": result["issue_title"],
        "date_display": now.strftime("%B %d, %Y"),
        "tag": "Weekly",
        "ticker_html": render_ticker(prices),
        "stories": result["stories"],
        "excerpt": result["intro"][:220],
    }
    add_post_and_rebuild(post)
    print(f"Generated weekly post: {slug}")

    # Stage the Buttondown draft too, so it's ready the moment the PR merges
    email_body = stories_to_plain_email_html(result["issue_title"], result["intro"], result["stories"], prices)
    draft = create_draft(f"The Crypto Playback — {result['issue_title']}", email_body)
    print(f"Created Buttondown draft: {draft.get('id', '(no id returned)')}")


if __name__ == "__main__":
    main()
