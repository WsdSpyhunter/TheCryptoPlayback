"""
should_run.py - decides whether a scheduled Daily/Weekly workflow start should
actually generate an issue. Used by the `guard` job in daily.yml / weekly.yml.

Why it exists: GitHub's cron is UTC-only (no daylight-saving awareness) and
best-effort - starts can be delayed or dropped. So each workflow is scheduled
at several UTC times that bracket 6:30 AM Central, and every start asks this
script one question: "is it 6:30 AM Central or later, and has today's issue
not already been made?" The first start that says yes generates the issue;
the rest skip. A dropped 6:30 run is therefore covered by the later backups,
and no morning ever gets two drafts.

Manual (workflow_dispatch) runs always go ahead.

Writes `run=true|false` to $GITHUB_OUTPUT.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
EARLIEST = (6, 30)  # local time; scheduled starts earlier than this skip


def decide(event, now_utc, already_made_today, other_run_in_progress):
    """Pure decision logic (unit-tested). Returns (run: bool, reason: str)."""
    if event != "schedule":
        return True, f"manual start ({event}) - always runs"
    local = now_utc.astimezone(CENTRAL)
    if (local.hour, local.minute) < EARLIEST:
        return False, f"{local:%H:%M} Central is before 6:30 AM - waiting for the next start"
    if already_made_today:
        return False, "today's issue was already generated"
    if other_run_in_progress:
        return False, "another run is generating today's issue right now"
    return True, f"{local:%H:%M} Central and no issue yet today - generating"


def _get(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def todays_state(repo, workflow_file, token, current_run_id, now_utc):
    """(already_made_today, other_run_in_progress) for this workflow since
    local midnight Central. A run only counts if its `generate` JOB succeeded
    - a run whose guard said "skip" also finishes green, but made nothing."""
    local_midnight = now_utc.astimezone(CENTRAL).replace(hour=0, minute=0, second=0, microsecond=0)
    since = local_midnight.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs = _get(
        f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/runs"
        f"?per_page=30&created=%3E%3D{since}", token,
    ).get("workflow_runs", [])
    made, in_progress = False, False
    for run in runs:
        if str(run["id"]) == str(current_run_id):
            continue
        jobs = _get(run["jobs_url"], token).get("jobs", [])
        for job in jobs:
            if job["name"] != "generate":
                continue
            if job["conclusion"] == "success":
                made = True
            elif job["status"] in ("queued", "in_progress"):
                in_progress = True
    return made, in_progress


if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    made = running = False
    if event == "schedule":
        made, running = todays_state(
            os.environ["GITHUB_REPOSITORY"], os.environ["WORKFLOW_FILE"],
            os.environ["GITHUB_TOKEN"], os.environ.get("GITHUB_RUN_ID", ""), now,
        )
    run, reason = decide(event, now, made, running)
    print(f"{'RUN' if run else 'SKIP'}: {reason}")
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"run={'true' if run else 'false'}\n")
