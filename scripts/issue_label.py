"""issue_label.py - how an issue is named for readers now that the Playback is one product ("The Playback"):
"Your Crypto Playback for Wednesday, October 21, 2026". The Saturday issue also carries a "Weekend Edition"
label. The internal tag ("Daily" / "Weekly") is unchanged in the data; only what readers see changes."""
from datetime import datetime


def issue_date(slug):
    return datetime.strptime(slug[:10], "%Y-%m-%d")


def weekday_date(slug):
    d = issue_date(slug)
    return f"{d.strftime('%A, %B')} {d.day}, {d.year}"


def your_playback(slug):
    return f"Your Crypto Playback for {weekday_date(slug)}"


def edition(tag):
    """'Weekend Edition' for the Saturday weekly, '' for the Mon/Wed/Fri issues."""
    return "Weekend Edition" if tag == "Weekly" else ""
