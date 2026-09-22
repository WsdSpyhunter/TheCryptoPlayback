"""
generate_daily.py — the daily Playback: 4-10 of the most significant,
distinct stories from the last day (as many as the day's real news
warrants), each with a short summary + editorial take, plus the price
ticker, Fear & Greed Index, and biggest mover of the day.

Model: Sonnet — same as weekly, and for the same reason: this is now a
multi-story piece that needs to hold voice/quality across several stories,
not the single-pick job Haiku was originally chosen for.

Output: writes the post via build_site.py, then leaves it staged for the
GitHub Actions workflow to open as a Pull Request (see daily.yml). Also
creates a DRAFT (never sends) in Buttondown, so the email version is ready
the moment you approve the site post.
"""
from generate_issue import generate_issue

MODEL = "claude-sonnet-5"
STORY_COUNT_MIN, STORY_COUNT_MAX = 4, 10


def main():
    generate_issue(
        model=MODEL,
        tag="Daily",
        slug_suffix="-daily",
        cadence_label="the last day",
        headlines_hours=40,
        max_per_feed=12,
        max_headlines=50,
        story_min=STORY_COUNT_MIN,
        story_max=STORY_COUNT_MAX,
    )


if __name__ == "__main__":
    main()
