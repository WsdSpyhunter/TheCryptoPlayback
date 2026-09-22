"""
generate_weekly.py — the flagship weekly Playback: 4-10 of the most
significant, distinct stories from the past week (as many as the week's real
news warrants), each with a short summary + editorial take, plus the price
ticker, Fear & Greed Index, and biggest mover of the week.

Model: Sonnet (holds voice/quality across a longer, multi-story piece better
than Haiku).

Also creates a DRAFT (never sends) in Buttondown, so the email version is
ready the moment you approve the site post.
"""
from generate_issue import generate_issue

MODEL = "claude-sonnet-5"
STORY_COUNT_MIN, STORY_COUNT_MAX = 4, 10


def main():
    generate_issue(
        model=MODEL,
        tag="Weekly",
        slug_suffix="-weekly",
        cadence_label="the past week",
        headlines_hours=24 * 7,
        max_per_feed=15,
        max_headlines=80,
        story_min=STORY_COUNT_MIN,
        story_max=STORY_COUNT_MAX,
    )


if __name__ == "__main__":
    main()
