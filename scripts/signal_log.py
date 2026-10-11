"""signal_log.py - a daily, timestamped record of the homepage Signal Confluence reading.

Once per US Central day (the first refresh at or after 7 AM CT, close to when the newsletter goes out)
we save how many of the signals were positive, which ones, and the Bitcoin price at that moment.
Months from now this lets us measure, honestly, how past readings related to what Bitcoin did next
(see data/signal_log.json). Nothing here changes what the site displays.
"""
import json
import os
from html import unescape
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
    CT = ZoneInfo("America/Chicago")
except Exception:       # noqa: BLE001
    CT = timezone.utc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "data", "signal_log.json")
RECORD_FROM_HOUR = 7
MAX_ENTRIES = 1500


def record(ctx, btc_price, fng_value=None, now=None):
    """Append today's reading if none exists yet and it is 7 AM CT or later. Returns True if written."""
    if not ctx or btc_price is None:
        return False
    now = (now or datetime.now(timezone.utc)).astimezone(CT)
    if now.hour < RECORD_FROM_HOUR:
        return False
    today = now.strftime("%Y-%m-%d")
    try:
        log = json.load(open(LOG))
    except (OSError, ValueError):
        log = []
    if any(e["d"] == today for e in log):
        return False
    log.append({
        "d": today, "t": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "pos": ctx["positive_count"], "total": ctx["total_count"], "btc": btc_price, "fng": fng_value,
        "signals": {unescape(name): bool(pos) for name, pos, _ in ctx["confluence_items"]},
    })
    with open(LOG, "w") as f:
        json.dump(log[-MAX_ENTRIES:], f, separators=(",", ":"))
    return True
