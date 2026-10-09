"""
preview_email.py - renders the Version 3 newsletter email from the latest published post + the latest live
indicator data, with NO network calls and nothing sent or uploaded (header/gauge images are drawn into /tmp).

Usage:  python preview_email.py [out.html] [--local-assets] [--indicators-first]
"""
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone

import build_site as b
import email_images
import email_v3


def render_latest(local_assets=False, indicators_last=True, upload=False, fallback_missed=None):
    entries = b.load_index()
    entry = entries[0]
    post = json.load(open(os.path.join(b.DATA_DIR, "posts", entry["slug"] + ".json")))
    live = b._live_context(entries)
    if live is None:
        raise SystemExit("No live indicator data on disk - run refresh_indicators.py first.")
    intro = re.sub(r"<[^>]+>", "", post["top_story_html"]).replace("TOP STORY", "").strip()
    prices = post.get("prices") or live["prices"]
    tmp = tempfile.mkdtemp()
    dt = datetime.strptime(post["slug"][:10], "%Y-%m-%d")
    header = email_images.make_issue_header(dt, os.path.join(tmp, "header.png"))
    gauge = email_images.render_gauge_png(live["fng"]["value"], os.path.join(tmp, "gauge.png"))
    base = f"file://{b.ROOT}/assets" if local_assets else email_v3.ASSET_BASE
    if local_assets:
        header, gauge = f"file://{header}", f"file://{gauge}"
    elif upload:        # real email: images hosted by Buttondown so they show in the draft immediately
        from buttondown_client import upload_image
        header, gauge = upload_image(header), upload_image(gauge)
    html = email_v3.render(
        issue_title=post["title"], intro=intro, stories=post["stories"], ticker_prices=prices, tag=post["tag"],
        date_display=post["date_display"], date_abbrev=post.get("date_abbrev") or live["date_abbrev"],
        issue_number=post["issue_number"], live=live, missed_story=post.get("missed_story") or fallback_missed,
        header_url=header, gauge_url=gauge, slug=post["slug"], year=datetime.now().year, base=base, indicators_last=indicators_last)
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
