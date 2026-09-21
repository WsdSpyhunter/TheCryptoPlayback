"""
generate_weekly.py — the flagship weekly Playback: 5-7 stories from the
past week, each with a short summary + your editorial take, plus the price
ticker, Fear & Greed Index, and biggest mover of the week. Mirrors the
approved design exactly: masthead, Top 5 Market/subscribe bar, sentiment
band, release-date box, issue pill + headline, top-story callout, stories,
disclaimer, footer.

Model: Sonnet (holds voice/quality across a longer, multi-story piece better
than Haiku — see notes on when to reconsider this in README.md).

Also creates a DRAFT (never sends) in Buttondown, so the email version is
ready the moment you approve the site post.
"""
import base64
import os
import sys
from datetime import datetime, timezone

from fetch_prices import get_top_prices
from fetch_news import get_recent_headlines
from fetch_sentiment import get_fear_greed
from claude_client import ask_claude_json
from build_site import (
    add_post_and_rebuild, render_ticker_bar, render_sentiment_combined,
    render_issue_pill, render_top_story_box, compute_biggest_mover, load_index,
    save_gauge_image, format_date_abbrev, ROOT,
)
from buttondown_client import create_draft

MODEL = "claude-sonnet-5"
STORY_COUNT_MIN, STORY_COUNT_MAX = 5, 7

# Real, public URLs — these images live in the site's own assets/ folder,
# so they resolve correctly inside an actual email sent to real inboxes
# (unlike design-tool preview URLs, which only work inside that tool).
ASSET_BASE = "https://cryptoplayback.com/assets"


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
- "issue_title" must NOT include the words "The Crypto Playback" — the brand \
  name is already shown separately in the header and subject line. Write \
  just the punchy theme of the week (e.g. "Clarity Act RIP, Bitcoin Says Hi").
- For each story, if its headline has an image URL listed, copy it EXACTLY \
  into that story's "image_url". Never invent or guess an image URL. If a \
  headline has no image URL listed, set that story's "image_url" to null.
- CRITICAL for valid output: never use a literal double-quote character (") \
  inside any string value. If you need quotation marks for HTML attributes, \
  use single quotes (e.g. <a href='...'>). If you need to quote a phrase in \
  your writing, use single quotes ('like this') instead of double quotes.

Respond with ONLY a JSON object, no markdown fences, no other text:
{{
  "issue_title": "a short title for this week's issue (no brand name in it)",
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


def masthead_email_html():
    return (
        f"<img src='{ASSET_BASE}/header-a.png' width='640' "
        f"style='width:100%;max-width:640px;display:block;' alt='The Crypto Playback'>"
    )


def ticker_bar_email_html(prices, date_abbrev):
    """Matches the approved design exactly: Top 5 Market tab with the arrow
    pointing into a centered, evenly-spaced 2-row price grid, caption under
    the tab, a separate news-date pill, and a share/subscribe row.

    Built entirely from flex divs, NOT tables. Tables are what caused the
    catastrophic column-collapse bug in Buttondown's rendering pipeline —
    this design deliberately avoids that whole category of risk."""
    row1, row2 = prices[:3], prices[3:]

    def chip(c):
        arrow_color = "#8FBF5C" if c["change_24h"] >= 0 else "#E8837A"
        return (f'<span style="color:#FBF9F5; font-family:Arial,sans-serif; font-size:12px; white-space:nowrap;">'
                f'{c["symbol"]} ${c["price"]:,.2f} <span style="color:{arrow_color};">({c["change_24h"]:+.1f}%)</span></span>')

    row1_html = f'<div style="display:flex; justify-content:center; gap:22px;">{"".join(chip(c) for c in row1)}</div>'
    row2_html = f'<div style="display:flex; justify-content:center; gap:22px; margin-top:9px;">{"".join(chip(c) for c in row2)}</div>'

    return f"""<div style="background:#171512; padding:20px 20px;">
  <div style="display:flex; align-items:center;">
    <div style="flex-shrink:0; display:flex; flex-direction:column;">
      <div style="display:flex; align-items:center;">
        <span style="display:inline-block;background:#DE9547;color:#171512;font-family:Arial,sans-serif;font-weight:bold;font-size:14px;padding:10px 12px;white-space:nowrap;">Top 5 Market</span>
        <span style="display:inline-block;width:0;height:0;border-top:19px solid transparent;border-bottom:19px solid transparent;border-left:14px solid #DE9547;"></span>
      </div>
      <span style="color:#FBF9F5;opacity:0.6;font-size:10px;margin-top:8px;line-height:1.3;">prices as of 6AM (cst)<br>on printed date</span>
    </div>
    <div style="flex:1; padding-top:6px;">
      {row1_html}
      {row2_html}
    </div>
  </div>
</div>
<div style="background:#3a3835; padding:10px 20px; text-align:center;">
  <span style="font-family:Arial,sans-serif; font-size:15px; color:#FBF9F5;">TOP NEWS: <em style="color:#F2C94C;">{date_abbrev}</em></span>
</div>
<div style="background:#171512; padding:12px 20px; display:flex; align-items:center; justify-content:center; gap:14px;">
  <span style="font-family:Georgia,serif; font-style:italic; font-size:12px; color:#FBF9F5; opacity:0.75;">Enjoying this? Share it with a friend &rarr;</span>
  <span style="font-family:Arial,sans-serif; font-size:16px; font-weight:bold; color:#FBF9F5;">SUBSCRIBE HERE</span>
  <a href="#" style="display:inline-flex;align-items:center;justify-content:center;width:27px;height:27px;border-radius:50%;background:#B5702E;color:#FBF9F5;text-align:center;font-size:13px;text-decoration:none;">&#9993;</a>
  <a href="https://x.com/cryptoplayback" style="display:inline-flex;align-items:center;justify-content:center;width:27px;height:27px;border-radius:50%;background:#4A90D9;color:#FBF9F5;text-align:center;font-size:13px;text-decoration:none;">X</a>
</div>"""


def sentiment_to_email_html(fng, mover, gauge_data_uri):
    """Single combined box (Fear & Greed + Biggest Mover on one line,
    separated by a divider) inside a light-grey band — matches the approved
    design. Built from flex divs, not tables, for the same reason as above."""
    fng_color = "#E24C4C" if fng["value"] <= 45 else ("#256B32" if fng["value"] >= 55 else "#8A7F5C")
    mover_up = mover["change_24h"] >= 0
    mover_color = "#256B32" if mover_up else "#E24C4C"
    mover_sign = "+" if mover_up else ""
    icon_path = (
        '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>' if mover_up
        else '<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>'
    )
    return f"""<div style="background:#AFAA9E; padding:14px 16px;">
  <div style="background:rgba(255,255,255,0.06); border:1.5px solid #3A362F; border-radius:6px; padding:12px 16px; text-align:center;">
    <img src="{gauge_data_uri}" width="40" height="26" style="vertical-align:middle; display:inline;" alt="Fear and Greed gauge">
    <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:11px; color:#975F25; vertical-align:middle; margin-left:6px;">FEAR &amp; GREED</span>
    <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:18px; color:{fng_color}; vertical-align:middle; margin-left:4px;">{fng['value']}</span>
    <span style="font-size:12px; color:{fng_color}; vertical-align:middle;">{fng['classification']}</span>
    <span style="display:inline-block; width:1.5px; height:26px; background:#3A362F; vertical-align:middle; margin:0 16px;"></span>
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{mover_color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;">{icon_path}</svg>
    <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:11px; color:#975F25; vertical-align:middle; margin-left:6px;">BIGGEST MOVER</span>
    <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:18px; color:{mover_color}; vertical-align:middle; margin-left:4px;">{mover['symbol']}</span>
    <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:13px; color:{mover_color}; vertical-align:middle;">{mover_sign}{mover['change_24h']:.1f}%</span>
  </div>
</div>"""


def release_row_email_html(date_display, issue_number):
    return f"""<div style="margin:20px 20px 0; padding:10px 16px; background:#F1EEE7; border-radius:4px; box-shadow:0 2px 5px rgba(23,21,18,0.18); display:flex; justify-content:space-between;">
  <span style="font-family:Arial,sans-serif; font-size:12px; color:#666666;">Release date: {date_display}</span>
  <span style="font-family:Arial,sans-serif; font-size:12px; color:#666666;">Issue #{issue_number}</span>
</div>"""


def issue_title_block_email_html(tag, title):
    label = "DAILY ISSUE" if tag == "Daily" else "WEEKLY ISSUE"
    return f"""<div style="padding:16px 20px 8px;">
<span style="display:inline-block;font-family:Arial,sans-serif;font-weight:bold;font-size:11px;letter-spacing:0.04em;color:#FBF9F5;background:#268CCA;padding:4px 10px;border-radius:3px;">{label}</span>
<h1 style="font-family:Arial,sans-serif;font-weight:bold;font-size:26px;color:#171512;margin:8px 0 0;line-height:1.15;">{title}</h1>
</div>"""


def top_story_to_email_html(intro):
    return f"""<div style="margin:14px 20px 0; display:flex; background:#F1EEE7; border-radius:4px; overflow:hidden;">
  <span style="flex-shrink:0; width:38px; background:#F2C94C; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; font-family:Arial,sans-serif; font-weight:bold; font-size:10px; padding:4px 2px;"><span style="white-space:nowrap;">TOP</span><span style="white-space:nowrap;">STORY</span></span>
  <p style="padding:14px 16px; font-family:Georgia,serif; font-style:italic; font-size:18px; margin:0;">{intro}</p>
</div>"""


def footer_email_html():
    year = datetime.now().year
    return f"""<img src='{ASSET_BASE}/disclaimer.png' width='640' style='width:100%;max-width:640px;display:block;margin-top:24px;' alt='Legal disclaimer: The Crypto Playback is not financial advice.'>
<div style="background:#975F25; padding:14px 20px; display:flex; justify-content:space-between; align-items:center;">
  <span style="color:#FBF9F5;font-family:Arial,sans-serif;font-size:12px;">&copy; {year} The Crypto Playback &middot; cryptoplayback@gmail.com</span>
  <img src='{ASSET_BASE}/logo-white.png' width='90' style='width:90px;display:inline-block;'>
</div>
<p style="text-align:center;font-family:Arial,sans-serif;font-size:11px;color:#666666;padding:10px 0;margin:0;background:#FBF9F5;">
  <a href="{{{{ unsubscribe_url }}}}" style="color:#666666;">Unsubscribe from The Crypto Playback</a>
</p>"""


def stories_to_plain_email_html(issue_title, intro, stories, ticker_prices, fng, mover, tag, date_display, date_abbrev, issue_number, gauge_data_uri):
    """Full HTML rendering for the email body — masthead through footer,
    matching the approved design exactly."""
    parts = [
        masthead_email_html(),
        ticker_bar_email_html(ticker_prices, date_abbrev),
        sentiment_to_email_html(fng, mover, gauge_data_uri),
        release_row_email_html(date_display, issue_number),
        issue_title_block_email_html(tag, issue_title),
        top_story_to_email_html(intro),
    ]
    for s in stories:
        img_html = f"<p><img src='{s['image_url']}' style='max-width:100%;'></p>" if s.get("image_url") else ""
        parts.append(f"<h3 style='font-family:Arial,Helvetica,sans-serif;font-weight:bold;font-size:20px;color:#171512;margin:0 0 10px;'>{s['headline']}</h3>{img_html}{s['body']}"
                      f"<p><a href='{s['source_url']}' style='color:#B5702E;font-weight:bold;text-decoration:none;'>Read more at {s['source_title']} &rarr;</a></p><hr>")
    parts.append(footer_email_html())
    body_html = "\n".join(parts[1:])  # everything except the masthead image
    wrapped = f"<div style='font-family:Arial,Helvetica,sans-serif;color:#171512;font-size:15px;line-height:1.5;'>{body_html}</div>"
    return parts[0] + "\n" + wrapped


def main():
    prices = get_top_prices()
    headlines = get_recent_headlines(hours=24 * 7, max_per_feed=15)
    if len(headlines) < STORY_COUNT_MIN:
        print("Not enough headlines this week — aborting rather than publishing a thin issue.")
        sys.exit(1)

    result = ask_claude_json(MODEL, SYSTEM_PROMPT, build_user_prompt(headlines), max_tokens=6000)
    result["issue_title"] = clean_issue_title(result["issue_title"])

    fng = get_fear_greed()
    mover = compute_biggest_mover(prices)
    issue_number = sum(1 for e in load_index() if e["tag"] == "Weekly") + 1

    now = datetime.now(timezone.utc)
    date_display = now.strftime("%B %d, %Y")
    date_abbrev = format_date_abbrev(now)
    slug = now.strftime("%Y-%m-%d") + "-weekly"
    gauge_path = save_gauge_image(fng["value"], slug)
    # Website: relative path, goes live atomically with the post when the PR merges.
    # Email: base64-embedded, so it works immediately, before/without any merge at all.
    with open(os.path.join(ROOT, gauge_path), "rb") as f:
        gauge_data_uri = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    post = {
        "slug": slug,
        "title": result["issue_title"],
        "date_display": date_display,
        "tag": "Weekly",
        "issue_number": issue_number,
        "gauge_path": gauge_path,
        "ticker_html": render_ticker_bar(prices, date_abbrev),
        "sentiment_html": render_sentiment_combined(fng, mover, "Weekly"),
        "issue_pill_html": render_issue_pill("Weekly"),
        "top_story_html": render_top_story_box(result["intro"]),
        "stories": result["stories"],
        "excerpt": result["intro"][:220],
    }
    add_post_and_rebuild(post)
    print(f"Generated weekly post: {slug}")

    email_body = stories_to_plain_email_html(
        result["issue_title"], result["intro"], result["stories"], prices,
        fng, mover, "Weekly", date_display, date_abbrev, issue_number, gauge_data_uri,
    )
    draft = create_draft(f"The Crypto Playback — {result['issue_title']}", email_body)
    print(f"Created Buttondown draft: {draft.get('id', '(no id returned)')}")


if __name__ == "__main__":
    main()
