"""Thin wrapper around Buttondown's API. Always creates a DRAFT — this
script never sends. Sending is a manual click in the Buttondown dashboard,
by design, so nothing goes to subscribers without you reviewing it there."""
import os
import requests

API_URL = "https://api.buttondown.com/v1/emails"
IMAGES_URL = "https://api.buttondown.com/v1/images"


def upload_image(file_path):
    """Uploads an image to Buttondown's own hosting and returns its public
    URL. Used for the Fear & Greed gauge, which is generated fresh per-post
    and needs to be viewable in the email/draft immediately — before (or
    without) the site's own PR ever getting merged to GitHub Pages."""
    headers = {"Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}"}
    with open(file_path, "rb") as f:
        resp = requests.post(IMAGES_URL, headers=headers, files={"image": f}, timeout=30)
    resp.raise_for_status()
    return resp.json()["image"]


def create_draft(subject, body_html):
    # Buttondown auto-detects body format and, left to its own devices, runs
    # custom HTML through its "Fancy mode" WYSIWYG converter — which doesn't
    # preserve table-based layouts and silently reflows them. This comment
    # marker forces plaintext/passthrough handling instead, so our HTML
    # reaches the inbox unmodified.
    body_html = "<!-- buttondown-editor-mode: plaintext -->\n" + body_html

    headers = {
        "Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}",
        "Content-Type": "application/json",
    }
    payload = {"subject": subject, "body": body_html, "status": "draft"}
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


SEND_DRAFT_URL = "https://api.buttondown.com/v1/emails/{id}/send-draft"


def send_draft_to_reviewer(draft_id, reviewer_email):
    """Mails a copy of an existing DRAFT to ONE reviewer address (Buttondown
    marks it as a preview) - this is the "your draft is ready, come review it"
    alert. It never reaches subscribers: `recipients` is an explicit list of
    just the reviewer. Returns True on success; any failure is reported but
    never raised, because a missed alert must not fail the newsletter run
    (the draft itself is already safely created)."""
    if not reviewer_email or not draft_id:
        return False
    headers = {
        "Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(SEND_DRAFT_URL.format(id=draft_id), headers=headers,
                             json={"recipients": [reviewer_email]}, timeout=30)
        resp.raise_for_status()
        print(f"Sent a review copy of draft {draft_id} to {reviewer_email}.")
        return True
    except Exception as exc:  # noqa: BLE001 - alert is best-effort by design
        detail = getattr(getattr(exc, "response", None), "text", "")[:300]
        print(f"WARNING: could not send the review alert ({exc}) {detail}")
        return False


# Statuses that mean the email has actually been published to subscribers
# (the author pressed Publish). "scheduled" is deliberately NOT here - a
# scheduled email goes to the site only once it really starts sending.
PUBLISHED_STATUSES = {"about_to_send", "in_flight", "sent", "throttled", "resending", "partially_sent"}


def get_email_status(email_id):
    """Returns the email's status string, or None if Buttondown says it no
    longer exists (HTTP 404 - i.e. the draft was deleted). Any other problem
    raises, so a hiccup is never mistaken for a deleted draft."""
    headers = {"Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}"}
    resp = requests.get(f"{API_URL}/{email_id}", headers=headers, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json().get("status", "")


def update_draft_body(email_id, body_html):
    """Replaces the body of an existing DRAFT (same plaintext passthrough marker
    as create_draft) and returns the email as Buttondown now stores it."""
    body_html = "<!-- buttondown-editor-mode: plaintext -->\n" + body_html
    headers = {
        "Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}",
        "Content-Type": "application/json",
    }
    resp = requests.patch(f"{API_URL}/{email_id}", headers=headers, json={"body": body_html}, timeout=30)
    resp.raise_for_status()
    return resp.json()
