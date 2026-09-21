"""
generate_daily.py — the daily "lite" post: top 5 prices + Fear & Greed +
biggest mover + one story on the single biggest thing that happened in
crypto today, with a short take.

Model: Haiku (cheap, fast, plenty for one story a day).
Output: writes the post via build_site.py, then leaves it staged for the
GitHub Actions workflow to open as a Pull Request (see daily.yml).
"""
import sys
from datetime import datetime, timezone

from fetch_prices import get_top_prices
from fetch_news import get_recent_headlines
from fetch_sentiment import get_fear_greed
from claude_client import ask_claude_json
from build_site import (
    add_post_and_rebuild, render_ticker, render_sentiment_bar,
    render_issue_pill, render_top_story_box, compute_biggest_mover, load_index,
)

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are the writer for "The Crypto Playback," a Bitcoin/crypto \
newsletter with a distinct voice: informed, a little wry, opinionated but \
never giving financial advice. You are given a list of real headlines from \
the last day, each with a source, a summary, a link, and sometimes an image \
URL. Pick the SINGLE most significant story — the one crypto investors most \
need to know about today — and write a short commentary on it.

Rules:
- Base every fact ONLY on the headlines/summaries given to you. Never invent numbers, quotes, or events not present in the source material. \
Base the ENTIRE story on the ONE headline/summary you cite — do not pull in \
facts from other headlines in the list, even true ones, once you've picked \
your story.
- Write a one-sentence "intro" that teases the story (this appears in a highlighted \
  callout box above the full story).
- Write 2-4 short paragraphs of commentary/analysis on the story, in the \
  newsletter's voice.
- Never phrase anything as investment advice or a prediction of what to do \
  with money — commentary and analysis only.
- Pick the source headline that is clearly the most consequential, not just \
  the most recent.
- If the headline you chose has an image URL listed, copy it EXACTLY into \
  "image_url". Never invent or guess an image URL. If that headline has no \
  image URL listed, set "image_url" to null.
- CRITICAL for valid output: never use a literal double-quote character (") \
  inside any string value. If you need quotation marks for HTML attributes, \
  use single quotes (e.g. <a href='...'>). If you need to quote a phrase in \
  your writing, use single quotes ('like this') instead of double quotes.

Respond with ONLY a JSON object, no markdown fences, no other text:
{
  "headline": "a punchy headline for this story, in your own words",
  "intro": "one sentence teasing the story",
  "body": "2-4 paragraphs of commentary, as HTML with <p> tags",
  "source_title": "the exact source name from the list (e.g. CoinDesk)",
  "source_url": "the exact link from the list for the story you chose",
  "image_url": "the exact image URL from the list for that headline, or null"
}"""


def build_user_prompt(headlines):
    lines = []
    for h in headlines[:25]:
        img_note = f" [image: {h['image_url']}]" if h.get("image_url") else " [image: none]"
        lines.append(f"- [{h['source']}] {h['headline']}: {h['summary']} ({h['link']}){img_note}")
    return "Headlines from the last day:\n" + "\n".join(lines)


def main():
    prices = get_top_prices()
    headlines = get_recent_headlines(hours=36)
    if not headlines:
        print("No recent headlines found — aborting so we don't publish a stale/empty post.")
        sys.exit(1)

    result = ask_claude_json(MODEL, SYSTEM_PROMPT, build_user_prompt(headlines))

    fng = get_fear_greed()
    mover = compute_biggest_mover(prices)
    issue_number = sum(1 for e in load_index() if e["tag"] == "Daily") + 1

    now = datetime.now(timezone.utc)
    slug = now.strftime("%Y-%m-%d") + "-daily"
    post = {
        "slug": slug,
        "title": result["headline"],
        "date_display": now.strftime("%B %d, %Y"),
        "tag": "Daily",
        "issue_number": issue_number,
        "ticker_html": render_ticker(prices),
        "sentiment_html": render_sentiment_bar(fng, mover, "Daily"),
        "issue_pill_html": render_issue_pill("Daily"),
        "top_story_html": render_top_story_box(result["intro"]),
        "stories": [{
            "headline": result["headline"],
            "body": result["body"],
            "source_title": result["source_title"],
            "source_url": result["source_url"],
            "image_url": result.get("image_url"),
        }],
        "excerpt": result["body"].split("</p>")[0].replace("<p>", "")[:220] + "...",
    }
    add_post_and_rebuild(post)
    print(f"Generated daily post: {slug}")


if __name__ == "__main__":
    main()
