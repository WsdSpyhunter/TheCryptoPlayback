"""
publish_approved.py - puts a newsletter issue on the website (homepage +
archive) once its Buttondown email has actually been published.

How the flow works:
  1. The daily/weekly run writes the issue to data/pending/<slug>.json and
     creates the Buttondown draft; the website is NOT touched.
  2. You read the [PREVIEW] email and press Publish in Buttondown.
  3. This script (run every 10 minutes by publish-approved.yml) sees the
     email is no longer a draft and publishes that issue to the site, rebuilt
     against the latest live data.
  A draft you delete in Buttondown is dropped, never published. A pending
  issue whose email is still a draft after 7 days is dropped as stale.

Live indicator data (tickers, Market Snapshot, signals...) is a separate job
and keeps refreshing on its own; nothing here affects it.
"""
import glob
import json
import os
from datetime import datetime, timezone

import build_site as b
from buttondown_client import PUBLISHED_STATUSES, get_email_status

MAX_PENDING_DAYS = 7


def decide(status, age_days):
    """Pure decision (unit-tested). `status` is the Buttondown status string,
    or None when the email no longer exists. Returns publish | wait | drop."""
    if status is None:
        return "drop", "its Buttondown draft was deleted"
    if status in PUBLISHED_STATUSES:
        return "publish", f"email status is '{status}' - it has been published"
    if age_days > MAX_PENDING_DAYS:
        return "drop", f"still '{status}' after {age_days} days - stale"
    return "wait", f"email status is '{status}' - waiting for you to publish it"


def age_in_days(slug, now):
    day = datetime.strptime(slug[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (now - day).days


def main():
    now = datetime.now(timezone.utc)
    files = sorted(glob.glob(os.path.join(b.PENDING_DIR, "*.json")))  # oldest first
    if not files:
        print("No pending issues.")
        return
    for path in files:
        with open(path) as f:
            post = json.load(f)
        slug = post["slug"]
        email_id = post.get("buttondown_email_id")
        if not email_id:
            print(f"{slug}: no Buttondown email id on file - dropping")
            os.remove(path)
            continue
        action, why = decide(get_email_status(email_id), age_in_days(slug, now))
        print(f"{slug}: {action.upper()} - {why}")
        if action == "publish":
            post.pop("buttondown_email_id", None)
            b.add_post_and_rebuild(post)
            os.remove(path)
        elif action == "drop":
            os.remove(path)


if __name__ == "__main__":
    main()
