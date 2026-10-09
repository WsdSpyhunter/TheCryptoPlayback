"""
rebuild_draft.py <slug> - repairs a pending issue's EMAIL in place, without
rewriting any of its text.

Re-checks every story image (swapping in the article's own image when the
feed's was dead), rebuilds the email from the saved issue with the same
stories and wording, updates the existing Buttondown draft, and mails you a
fresh [PREVIEW] copy. Use it when a reviewed draft has a fixable problem
(e.g. a broken image) and you don't want a brand-new write-up.

Run from GitHub: Actions -> "Rebuild a pending draft" -> Run workflow.
Locally add --dry-run to just write the HTML to /tmp and touch nothing else.
"""
import json
import os
import sys

import build_site as b
from blocked_terms import contains_blocked, neutralize_links
from buttondown_client import get_email_status, send_draft_to_reviewer, update_draft_body
from email_build import build_email
from story_images import fix_story_images


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if len(args) != 1:
        raise SystemExit("usage: rebuild_draft.py <slug> [--dry-run]")
    path = os.path.join(b.PENDING_DIR, f"{args[0]}.json")
    if not os.path.exists(path):
        raise SystemExit(f"No pending issue '{args[0]}' (already published, or never created).")
    post = json.load(open(path))

    fixed, dropped = fix_story_images(post["stories"])
    neutralize_links({"stories": post["stories"], "missed_story": post.get("missed_story")}, b.ROOT)

    email_body = build_email(
        issue_title=post["title"], intro=post["top_story_html"], stories=post["stories"], prices=post["prices"], tag=post["tag"],
        date_display=post["date_display"], date_abbrev=post["date_abbrev"], issue_number=post["issue_number"], slug=post["slug"],
        missed_story=post.get("missed_story"), upload=not dry, local_assets=dry,
    )
    if contains_blocked(email_body):
        raise SystemExit("A blocked term is in the rebuilt email - not updating the draft.")

    if dry:
        with open("/tmp/rebuilt_email.html", "w") as f:
            f.write(email_body)
        print(f"DRY RUN: images fixed={fixed} dropped={dropped}; wrote /tmp/rebuilt_email.html ({len(email_body)//1024} KB)")
        return

    email_id = post["buttondown_email_id"]
    status = get_email_status(email_id)
    if status != "draft":
        # Never edit an email that is gone, scheduled, or already published.
        raise SystemExit(f"Draft {email_id} is '{status}', not 'draft' - leaving it alone.")
    stored = update_draft_body(email_id, email_body)
    # confirm Buttondown really holds the repaired content
    still_broken = [s["headline"][:40] for s in post["stories"] if s.get("image_url") and s["image_url"] not in stored.get("body", "")]
    print(f"Updated draft {email_id}: images fixed={fixed} dropped={dropped}; "
          f"{'all story images present in the stored draft' if not still_broken else 'MISSING from stored draft: ' + str(still_broken)}")
    with open(path, "w") as f:
        json.dump(post, f, indent=2)
    send_draft_to_reviewer(email_id, os.environ.get("REVIEW_EMAIL", "").strip())


if __name__ == "__main__":
    main()
