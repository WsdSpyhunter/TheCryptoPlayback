"""
send_email_test.py — creates a clearly-marked TEST draft of the Version 2
newsletter in Buttondown, built from the latest published post + the latest
live indicator data. Like everything in buttondown_client.py it only ever
creates a DRAFT - nothing is sent to subscribers. Open the draft in the
Buttondown dashboard and use "Send test" to mail it to yourself.

Run it from GitHub: Actions -> "Email test (Version 2 layout)" -> Run
workflow (it needs the BUTTONDOWN_API_KEY repo secret).

Issues generated before Version 2 have no saved "missed_story", so the test
falls back to a real, labeled sample story (taken from an earlier issue) so
the "Here's A Story You Missed" section can be reviewed.
"""
from buttondown_client import create_draft
from preview_email import render_latest

SAMPLE_MISSED_STORY = {
    "headline": "Grayscale's Zcash ETF Is So Hot It's Splitting Its Shares",
    "body": ("Grayscale's Zcash ETF has pulled in more than $233 million in under a month, and the firm is now "
             "splitting shares three ways to make the fund more accessible to a wider set of buyers. It is a "
             "genuinely odd twist: after years of regulators treating privacy tech with suspicion, one of the "
             "most aggressively private assets in crypto is turning into a mainstream ETF product."),
    "source_title": "Decrypt",
    "source_url": "https://decrypt.co/378675/grayscale-zcash-etf-more-affordable-split",
}

if __name__ == "__main__":
    post, html = render_latest(fallback_missed=SAMPLE_MISSED_STORY)
    draft = create_draft(f"[TEST - Version 2 layout] The Crypto Playback — {post['title']}", html)
    print(f"Created TEST draft from {post['slug']}: {draft.get('id', '(no id returned)')}")
