"""
preview_email.py — renders the Version 2 newsletter email from the latest
published post + the latest live indicator data, with NO network calls and
nothing sent or uploaded. Used to eyeball the layout locally and by
send_email_test.py (which turns the same HTML into a clearly-marked TEST
Buttondown draft).

Usage:  python preview_email.py [out.html] [--missed missed_story.json]

If the latest post has no saved "missed_story" (issues generated before
Version 2 don't), pass --missed with a JSON file shaped like
{"headline", "body", "source_title", "source_url"} to try the section out.
"""
import json
import os
import sys

from datetime import datetime, timezone

from build_site import DATA_DIR, LIVE_DATA_FILE, format_date_abbrev, load_index, load_market_overview
from email_render import stories_to_plain_email_html, load_playback_read


def render_latest(missed_override=None, fallback_missed=None):
    entry = load_index()[0]
    with open(os.path.join(DATA_DIR, "posts", entry["slug"] + ".json")) as f:
        post = json.load(f)
    overview = load_market_overview()
    if overview is None:
        raise SystemExit("No live indicator data on disk - run refresh_indicators.py first.")
    intro = post["top_story_html"]
    # top_story_html is the site's rendered box; the email wants just the sentence.
    import re
    intro = re.sub(r"<[^>]+>", "", intro).replace("TOP STORY", "").strip()
    missed = missed_override if missed_override is not None else (post.get("missed_story") or fallback_missed)
    # Older posts predate the saved prices/date_abbrev fields - fall back to
    # the latest live data (a real issue run always has fresh ones).
    with open(LIVE_DATA_FILE) as f:
        live = json.load(f)
    prices = post.get("prices") or live["prices"]
    date_abbrev = post.get("date_abbrev") or format_date_abbrev(datetime.now(timezone.utc))
    html = stories_to_plain_email_html(
        post["title"], intro, post["stories"], prices, post["tag"],
        post["date_display"], date_abbrev, post["issue_number"], overview, missed, load_playback_read(),
    )
    return post, html


if __name__ == "__main__":
    args = sys.argv[1:]
    missed = None
    if "--missed" in args:
        i = args.index("--missed")
        with open(args[i + 1]) as f:
            missed = json.load(f)
        del args[i:i + 2]
    out = args[0] if args else "email_preview.html"
    post, html = render_latest(missed)
    with open(out, "w") as f:
        f.write(html)
    print(f"Wrote {out} ({len(html) / 1024:.1f} KB) from {post['slug']}")
