"""
preview_email.py - renders the Version 3 newsletter email from the latest published post + the latest live
indicator data, with NO network calls and nothing sent or uploaded (header/gauge images are drawn into /tmp).

Usage:  python preview_email.py [out.html] [--local-assets] [--indicators-first]
"""
import json
import os
import sys

import build_site as b
from email_build import build_email


def render_latest(local_assets=False, indicators_last=True, upload=False, fallback_missed=None):
    entries = b.load_index()
    entry = entries[0]
    post = json.load(open(os.path.join(b.DATA_DIR, "posts", entry["slug"] + ".json")))
    live = b._live_context(entries)
    prices = post.get("prices") or (live or {}).get("prices")
    html = build_email(
        issue_title=post["title"], intro=post["top_story_html"], stories=post["stories"], prices=prices, tag=post["tag"],
        date_display=post["date_display"], date_abbrev=post.get("date_abbrev"), issue_number=post["issue_number"],
        slug=post["slug"], missed_story=post.get("missed_story") or fallback_missed, upload=upload,
        local_assets=local_assets, indicators_last=indicators_last)
    return post, html


if __name__ == "__main__":
    args = sys.argv[1:]
    local = "--local-assets" in args
    first = "--indicators-first" in args
    args = [a for a in args if not a.startswith("--")]
    out = args[0] if args else "email_preview.html"
    post, html = render_latest(local, not first)
    open(out, "w").write(html)
    print(f"Wrote {out} ({len(html) / 1024:.1f} KB) from {post['slug']}")
