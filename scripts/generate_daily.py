"""
generate_daily.py — the daily "lite" post: top 5 prices + one story on the
single biggest thing that happened in crypto today, with a short take.

Model: Haiku (cheap, fast, plenty for one story a day).
Output: writes the post via build_site.py, then leaves it staged for the
GitHub Actions workflow to open as a Pull Request (see daily.yml).
"""
import sys
from datetime import datetime, timezone

from fetch_prices import get_top_prices
from fetch_news import get_recent_headlines
from claude_client import ask_claude_json
from build_site import add_post_and_rebuild, render_ticker

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are the writer for "The Crypto Playback," a Bitcoin/crypto \
newsletter with a distinct voice: informed, a little wry, opinionated but \
never giving financial advice. You are given a list of real headlines from \
the last day. Pick the SINGLE most significant story — the one crypto \
investors most need to know about today — and write a short commentary on it.

Rules:
- Base every fact ONLY on the headlines/summaries given to you. Never invent \
  numbers, quotes, or events not present in the source material.
- Write 2-4 short paragraphs of commentary/analysis on the story, in the \
  newsletter's voice.
- Never phrase anything as investment advice or a prediction of what to do \
  with money — commentary and analysis only.
- Pick the source headline that is clearly the most consequential, not just \
  the most recent.

Respond with ONLY a JSON object, no markdown fences, no other text:
{
  "headline": "a punchy headline for this story, in your own words",
  "body": "2-4 paragraphs of commentary, as HTML with <p> tags",
  "source_title": "the exact source name from the list (e.g. CoinDesk)",
  "source_url": "the exact link from the list for the story you chose"
}"""


def build_user_prompt(headlines):
    lines = [
        f"- [{h['source']}] {h['headline']}: {h['summary']} ({h['link']})"
        for h in headlines[:25]
    ]
    return "Headlines from the last day:\n" + "\n".join(lines)


def main():
    prices = get_top_prices()
    headlines = get_recent_headlines(hours=36)
    if not headlines:
        print("No recent headlines found — aborting so we don't publish a stale/empty post.")
        sys.exit(1)

    result = ask_claude_json(MODEL, SYSTEM_PROMPT, build_user_prompt(headlines))

    now = datetime.now(timezone.utc)
    slug = now.strftime("%Y-%m-%d") + "-daily"
    post = {
        "slug": slug,
        "title": result["headline"],
        "date_display": now.strftime("%B %d, %Y"),
        "tag": "Daily",
        "ticker_html": render_ticker(prices),
        "stories": [{
            "headline": result["headline"],
            "body": result["body"],
            "source_title": result["source_title"],
            "source_url": result["source_url"],
        }],
        "excerpt": result["body"].split("</p>")[0].replace("<p>", "")[:220] + "...",
    }
    add_post_and_rebuild(post)
    print(f"Generated daily post: {slug}")


if __name__ == "__main__":
    main()
