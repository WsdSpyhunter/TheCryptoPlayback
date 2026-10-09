"""One entry point that turns a saved/generated issue into the Version 3 email HTML.

Used by generate_issue.py (the daily/weekly writer), rebuild_draft.py (repair a pending draft) and
send_email_test.py / preview_email.py (previews and test drafts). It gathers the live indicator data, draws the
per-issue header (with that issue's date) and the sentiment gauge, uploads those two images to Buttondown's own
hosting when `upload=True` (so they show in the draft immediately), and renders with email_v3.
"""
import os
import re
import tempfile
from datetime import datetime

import build_site as b
import email_images
import email_v3


def build_email(*, issue_title, intro, stories, prices, tag, date_display, date_abbrev, issue_number, slug,
                missed_story=None, upload=False, local_assets=False, indicators_last=True):
    entries = b.load_index()
    live = b._live_context(entries)
    if live is None:
        raise SystemExit("No live indicator data on disk - cannot build the email.")
    intro = re.sub(r"<[^>]+>", "", intro or "").replace("TOP STORY", "").strip()
    tmp = tempfile.mkdtemp()
    dt = datetime.strptime(slug[:10], "%Y-%m-%d")
    header = email_images.make_issue_header(dt, os.path.join(tmp, "header.png"))
    gauge = email_images.render_gauge_png(live["fng"]["value"], os.path.join(tmp, "gauge.png"))
    base = email_v3.ASSET_BASE
    if local_assets:
        base = f"file://{b.ROOT}/assets"
        header, gauge = f"file://{header}", f"file://{gauge}"
    elif upload:
        from buttondown_client import upload_image
        header, gauge = upload_image(header), upload_image(gauge)
    return email_v3.render(
        issue_title=issue_title, intro=intro, stories=stories, ticker_prices=prices, tag=tag, date_display=date_display,
        date_abbrev=live["date_abbrev"] or date_abbrev, issue_number=issue_number, live=live, missed_story=missed_story,
        header_url=header, gauge_url=gauge, slug=slug, year=datetime.now().year, base=base, indicators_last=indicators_last)
