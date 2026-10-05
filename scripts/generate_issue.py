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

from fetch_prices import get_top_prices, TICKER_COINS, MOVER_POOL
from fetch_news import get_recent_headlines
from fetch_sentiment import get_fear_greed
from fetch_sectors import get_top_sectors
from fetch_stablecoins import get_stablecoin_liquidity
from claude_client import ask_claude_json
from blocked_terms import BLOCKED_TERMS, contains_blocked, sanitize_headlines, mask_result, neutralize_links
from build_site import (
    save_pending_post, render_ticker_bar, render_sentiment_combined,
    render_issue_pill, render_top_story_box, compute_biggest_mover, compute_weekly_mover,
    load_index, save_gauge_image, format_date_abbrev, load_market_overview, ROOT,
)
from email_render import stories_to_plain_email_html, stories_to_plain_email_html_v1, upload_gauge_image
import os

from buttondown_client import create_draft, send_draft_to_reviewer


def build_system_prompt(story_min, story_max, cadence_label):
    preferred_floor = min(story_min + 1, story_max)
    blocked_list = ", ".join(BLOCKED_TERMS)  # the names (dict keys)
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
- ALSO pick ONE extra story for the "Here's A Story You Missed" slot: the \
  most genuinely intriguing, unusual, or surprising crypto-related item in \
  the list — an offbeat on-chain event, a strange legal or cultural moment, \
  an unexpected use of the technology, a curiosity. It must be a DIFFERENT \
  headline from every story you selected above, and not routine price or \
  regulation news. Base it ENTIRELY on that one headline's own summary \
  (never invent details), and write it as plain text in 2-3 sentences with \
  NO HTML tags. If nothing in the list is genuinely unusual, set \
  "missed_story" to null rather than forcing a dull pick.
- Some company names can't appear in the newsletter. In the source material \
  they have already been replaced with a generic description (for example \
  "a large overseas crypto exchange"). Use that wording and write naturally \
  around it - still tell the whole story, just never name, guess or hint at \
  the missing name. Never write any of these words in any form: {blocked_list}.
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
  ],
  "missed_story": {{
    "headline": "punchy headline, your own words",
    "body": "2-3 plain-text sentences, no HTML",
    "source_title": "exact source name from the list",
    "source_url": "exact link from the list"
  }}
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


def validated_missed_story(result, headlines):
    """The "Here's A Story You Missed" pick, or None. Dropped (not repaired)
    if the model left it out, left a field empty, or cited a link that isn't
    one of the real headlines it was given - this slot is only ever built
    from real source material."""
    m = result.get("missed_story")
    if not isinstance(m, dict):
        return None
    if not all(isinstance(m.get(k), str) and m[k].strip() for k in ("headline", "body", "source_title", "source_url")):
        return None
    if m["source_url"] not in {h["link"] for h in headlines}:
        print("missed_story cited a link not in the headline list - dropping it.")
        return None
    if m["source_url"] in {st.get("source_url") for st in result["stories"]}:
        print("missed_story duplicates one of the main stories - dropping it.")
        return None
    return {k: m[k].strip() for k in ("headline", "body", "source_title", "source_url")}


def generate_issue(model, tag, slug_suffix, cadence_label, headlines_hours,
                    max_per_feed, max_headlines, story_min, story_max, max_tokens=8000):
    """Generates one issue (daily or weekly — same shape now, just different
    cadence/model/story-count knobs), publishes it to the site, and creates
    the matching Buttondown draft. Exits early (code 1) if there isn't
    enough real news to hit the story-count floor, rather than publish a
    thin issue."""
    coins = get_top_prices(MOVER_POOL)
    prices = coins[:TICKER_COINS]
    headlines = get_recent_headlines(hours=headlines_hours, max_per_feed=max_per_feed)
    headlines, changed = sanitize_headlines(headlines)
    if changed:
        print(f"Replaced a name Buttondown won't publish with a generic description in {changed} headline(s).")
    if len(headlines) < story_min:
        print(f"Only {len(headlines)} headlines found (need at least {story_min}) — "
              f"aborting rather than publishing a thin issue.")
        sys.exit(1)

    system_prompt = build_system_prompt(story_min, story_max, cadence_label)
    user_prompt = build_user_prompt(headlines, cadence_label, max_headlines)
    result = ask_claude_json(model, system_prompt, user_prompt, max_tokens=max_tokens)
    result["issue_title"] = clean_issue_title(result["issue_title"])
    masked = mask_result(result)
    if masked:
        print(f"WARNING: replaced {masked} blocked term(s) the model wrote anyway.")

    missed_story = validated_missed_story(result, headlines)
    # Source links that contain a blocked name (e.g. ".../bitget-hack") go through
    # a redirect page on our own site; the pending commit publishes those pages.
    rerouted = neutralize_links({"stories": result["stories"], "missed_story": missed_story}, ROOT)
    if rerouted:
        print(f"Routed {rerouted} source link(s) through our own redirect page (their addresses contain a blocked name).")
    fng = get_fear_greed()
    mover = compute_biggest_mover(coins)
    week_mover = compute_weekly_mover(prices)
    sectors = get_top_sectors()
    stablecoins = get_stablecoin_liquidity()
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
        # Raw data, not just the rendered HTML below - lets any future
        # design (homepage widgets, a live version, etc.) work from real
        # structured numbers instead of having to re-parse HTML strings.
        "prices": prices,
        "fng": fng,
        "mover": mover,
        "week_mover": week_mover,
        "sectors": sectors,
        "stablecoins": stablecoins,
        "date_abbrev": date_abbrev,
        "ticker_html": render_ticker_bar(prices, date_abbrev),
        "sentiment_html": render_sentiment_combined(fng, mover, tag),
        "issue_pill_html": render_issue_pill(tag),
        "top_story_html": render_top_story_box(result["intro"]),
        "stories": result["stories"],
        "missed_story": missed_story,
        "excerpt": result["intro"][:220],
    }
    print(f"Generated {tag.lower()} post: {slug} ({len(result['stories'])} stories)")

    # Newsletter Version 2 (Market Snapshot, Signal Confluence, news section).
    # Falls back to the Version 1 layout only if there's no live indicator
    # data on disk to build the new sections from.
    overview = load_market_overview()
    if overview is not None:
        email_body = stories_to_plain_email_html(
            result["issue_title"], result["intro"], result["stories"], prices,
            tag, date_display, date_abbrev, issue_number, overview, missed_story,
        )
    else:
        print("No live indicator data found - falling back to the Version 1 email layout.")
        email_body = stories_to_plain_email_html_v1(
            result["issue_title"], result["intro"], result["stories"], prices,
            fng, mover, tag, date_display, date_abbrev, issue_number, upload_gauge_image(gauge_path),
        )
    # Last gate: never create a draft Buttondown would refuse to publish. Failing
    # here makes the workflow retry with a fresh write-up instead of leaving a
    # draft you can't send.
    if contains_blocked(email_body) or contains_blocked(result["issue_title"]):
        raise SystemExit("A blocked term is still in the email body/subject - not creating the draft.")
    draft = create_draft(f"The Crypto Playback — {result['issue_title']}", email_body)
    print(f"Created Buttondown draft: {draft.get('id', '(no id returned)')}")

    # The website does NOT get this issue yet. It is saved as "pending", tied to
    # its Buttondown draft; publish_approved.py (every 10 minutes) puts it on the
    # homepage and in the archive once the draft has actually been published.
    post["buttondown_email_id"] = draft["id"]
    path = save_pending_post(post)
    print(f"Saved pending post (waits for you to publish the email): {path}")
    # "Ready to review" alert: a preview copy of the draft goes to the
    # reviewer's own inbox (REVIEW_EMAIL, set in the workflow). Best-effort.
    send_draft_to_reviewer(draft.get("id"), os.environ.get("REVIEW_EMAIL", "").strip())
