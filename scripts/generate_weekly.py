"""
generate_weekly.py — the flagship weekly Playback: 5-7 stories from the
past week, each with a short summary + your editorial take, plus the price
ticker, Fear & Greed Index, and biggest mover of the week. Mirrors the
original newsletter's format exactly.

Model: Sonnet (holds voice/quality across a longer, multi-story piece better
than Haiku — see notes on when to reconsider this in README.md).

Also creates a DRAFT (never sends) in Buttondown, so the email version is
ready the moment you approve the site post.
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
from buttondown_client import create_draft

MODEL = "claude-sonnet-5"
STORY_COUNT_MIN, STORY_COUNT_MAX = 5, 7

SYSTEM_PROMPT = f"""You are the writer for "The Crypto Playback," a weekly \
Bitcoin/crypto newsletter. Your voice: informed, a little wry, willing to \
share an opinion, but you NEVER give financial advice or tell readers what \
to buy/sell. You are given real headlines from the past week, each with a \
source, a summary, a link, and sometimes an image URL. Select the \
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
- For each story, if its headline has an image URL listed, copy it EXACTLY \
  into that story's "image_url". Never invent or guess an image URL. If a \
  headline has no image URL listed, set that story's "image_url" to null.
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
      "source_url": "exact link from the list",
      "image_url": "exact image URL from the list for this headline, or null"
    }}
  ]
}}"""


def build_user_prompt(headlines):
    lines = []
    for h in headlines[:60]:
        img_note = f" [image: {h['image_url']}]" if h.get("image_url") else " [image: none]"
        lines.append(f"- [{h['source']}] {h['headline']}: {h['summary']} ({h['link']}){img_note}")
    return "Headlines from the past week:\n" + "\n".join(lines)


def sentiment_to_email_html(fng, mover):
    """Simple, email-safe (no writing-mode, minimal flex reliance) version of the
    Fear & Greed + Biggest Mover callout for the Buttondown draft."""
    fng_color = "#E24C4C" if fng["value"] <= 45 else ("#256B32" if fng["value"] >= 55 else "#8A7F5C")
    mover_up = mover["change_24h"] >= 0
    mover_color = "#256B32" if mover_up else "#E24C4C"
    mover_sign = "+" if mover_up else ""
    return (
        f"<table role='presentation' width='100%' style='margin:14px 0;'><tr>"
        f"<td style='background:#F1EEE7;border:1.5px solid {fng_color};border-radius:6px;padding:10px 14px;'>"
        f"<strong style='color:#975F25;font-size:11px;letter-spacing:0.05em;'>FEAR &amp; GREED</strong><br>"
        f"<span style='color:{fng_color};font-weight:bold;font-size:19px;'>{fng['value']}</span> "
        f"<span style='color:{fng_color};'>{fng['classification']}</span>"
        f"</td>"
        f"<td style='width:14px;'></td>"
        f"<td style='background:#F1EEE7;border:1.5px solid {mover_color};border-radius:6px;padding:10px 14px;'>"
        f"<strong style='color:#975F25;font-size:11px;letter-spacing:0.05em;'>BIGGEST MOVER OF THE WEEK</strong><br>"
        f"<span style='color:{mover_color};font-weight:bold;font-size:19px;'>{mover['symbol']}</span> "
        f"<span style='color:{mover_color};font-weight:bold;'>{mover_sign}{mover['change_24h']:.1f}%</span>"
        f"</td>"
        f"</tr></table>"
    )


def top_story_to_email_html(intro):
    return (
        f"<table role='presentation' width='100%' style='margin:14px 0;background:#F1EEE7;border-radius:4px;'><tr>"
        f"<td style='width:26px;background:#F2C94C;text-align:center;font-weight:bold;font-size:11px;'>TOP<br>STORY</td>"
        f"<td style='padding:14px 16px;font-style:italic;'>{intro}</td>"
        f"</tr></table>"
    )


def stories_to_plain_email_html(issue_title, intro, stories, ticker_prices, fng, mover):
    """A simpler HTML rendering for the email body (Buttondown handles its
    own layout/branding chrome around this)."""
    price_line = " &middot; ".join(
        f"{c['symbol']} ${c['price']:,.2f} ({c['change_24h']:+.1f}%)" for c in ticker_prices
    )
    parts = [
        f"<p><strong>{price_line}</strong></p>",
        sentiment_to_email_html(fng, mover),
        top_story_to_email_html(intro),
    ]
    for s in stories:
        img_html = f"<p><img src='{s['image_url']}' style='max-width:100%;'></p>" if s.get("image_url") else ""
        parts.append(f"<h3>{s['headline']}</h3>{img_html}{s['body']}"
                      f"<p><a href='{s['source_url']}'>Read more at {s['source_title']}</a></p><hr>")
    return "\n".join(parts)


def main():
    prices = get_top_prices()
    headlines = get_recent_headlines(hours=24 * 7, max_per_feed=15)
    if len(headlines) < STORY_COUNT_MIN:
        print("Not enough headlines this week — aborting rather than publishing a thin issue.")
        sys.exit(1)

    result = ask_claude_json(MODEL, SYSTEM_PROMPT, build_user_prompt(headlines), max_tokens=6000)

    fng = get_fear_greed()
    mover = compute_biggest_mover(prices)
    issue_number = sum(1 for e in load_index() if e["tag"] == "Weekly") + 1

    now = datetime.now(timezone.utc)
    slug = now.strftime("%Y-%m-%d") + "-weekly"
    post = {
        "slug": slug,
        "title": result["issue_title"],
        "date_display": now.strftime("%B %d, %Y"),
        "tag": "Weekly",
        "issue_number": issue_number,
        "ticker_html": render_ticker(prices),
        "sentiment_html": render_sentiment_bar(fng, mover, "Weekly"),
        "issue_pill_html": render_issue_pill("Weekly"),
        "top_story_html": render_top_story_box(result["intro"]),
        "stories": result["stories"],
        "excerpt": result["intro"][:220],
    }
    add_post_and_rebuild(post)
    print(f"Generated weekly post: {slug}")

    email_body = stories_to_plain_email_html(
        result["issue_title"], result["intro"], result["stories"], prices, fng, mover
    )
    draft = create_draft(f"The Crypto Playback — {result['issue_title']}", email_body)
    print(f"Created Buttondown draft: {draft.get('id', '(no id returned)')}")


if __name__ == "__main__":
    main()
