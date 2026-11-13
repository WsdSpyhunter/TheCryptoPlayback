"""gsc_report.py - read-only Google Search Console report for cryptoplayback.com.

Uses a read-only service account (it is a "Restricted" user on the property, so it can look but never change
anything). The key file is NEVER in this repo: it lives at ~/.config/cryptoplayback/gsc-key.json (override with
the GSC_KEY environment variable). Reports are written to ~/.config/cryptoplayback/reports/ (not committed).

Needs: pip install google-auth requests
Run:   python scripts/gsc_report.py [--days 28] [--no-inspect]
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

SITE = "https://cryptoplayback.com/"
API = "https://www.googleapis.com/webmasters/v3"
KEY = os.environ.get("GSC_KEY", os.path.expanduser("~/.config/cryptoplayback/gsc-key.json"))
OUT = os.path.expanduser("~/.config/cryptoplayback/reports")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def session():
    creds = service_account.Credentials.from_service_account_file(KEY, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    return AuthorizedSession(creds)


def query(s, start, end, dims=None, limit=25):
    body = {"startDate": str(start), "endDate": str(end), "rowLimit": limit}
    if dims:
        body["dimensions"] = dims
    r = s.post(f"{API}/sites/{quote(SITE, safe='')}/searchAnalytics/query", json=body)
    r.raise_for_status()
    return r.json().get("rows", [])


def totals(s, start, end):
    rows = query(s, start, end)
    return rows[0] if rows else {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}


def inspect(s, url):
    r = s.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect", json={"inspectionUrl": url, "siteUrl": SITE})
    if r.status_code != 200:
        return f"error {r.status_code}"
    st = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
    return st.get("coverageState", "unknown")


def pct(a, b):
    return "n/a" if not b else f"{(a - b) / b * 100:+.0f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--no-inspect", action="store_true")
    a = ap.parse_args()
    s = session()
    end = date.today() - timedelta(days=2)          # Search Console data lags about two days
    start = end - timedelta(days=a.days - 1)
    p_end = start - timedelta(days=1)
    p_start = p_end - timedelta(days=a.days - 1)
    cur, prev = totals(s, start, end), totals(s, p_start, p_end)
    L = [f"# Search Console report: cryptoplayback.com ({start} to {end}, vs {p_start} to {p_end})", ""]
    L += ["## Totals", "",
          f"- Clicks: {cur['clicks']:.0f} ({pct(cur['clicks'], prev['clicks'])} vs prior period)",
          f"- Impressions: {cur['impressions']:.0f} ({pct(cur['impressions'], prev['impressions'])})",
          f"- Average click-through rate: {cur['ctr'] * 100:.1f}%",
          f"- Average position: {cur['position']:.1f}", ""]
    q = query(s, start, end, ["query"], 250)
    L += ["## Top searches (by impressions)", ""]
    for r in sorted(q, key=lambda r: -r["impressions"])[:15]:
        L.append(f"- {r['keys'][0]}: {r['impressions']:.0f} impressions, {r['clicks']:.0f} clicks, position {r['position']:.1f}")
    near = [r for r in q if 8 <= r["position"] <= 20 and r["impressions"] >= 2]
    L += ["", "## Near page one (positions 8-20, 2+ impressions): best targets for improvement", ""]
    L += [f"- {r['keys'][0]}: position {r['position']:.1f}, {r['impressions']:.0f} impressions" for r in sorted(near, key=lambda r: -r["impressions"])[:12]] or ["- none yet"]
    L += ["", "## Top pages", ""]
    for r in sorted(query(s, start, end, ["page"], 100), key=lambda r: -r["impressions"])[:15]:
        L.append(f"- {r['keys'][0].replace(SITE, '/')}: {r['impressions']:.0f} impressions, {r['clicks']:.0f} clicks, position {r['position']:.1f}")
    sm = s.get(f"{API}/sites/{quote(SITE, safe='')}/sitemaps").json().get("sitemap", [])
    L += ["", "## Sitemaps", ""]
    for x in sm:
        L.append(f"- {x['path']}: last read {x.get('lastDownloaded', 'never')[:10]}, errors {x.get('errors', 0)}, warnings {x.get('warnings', 0)}")
    if not a.no_inspect:
        try:
            idx = json.load(open(os.path.join(ROOT, "data", "posts_index.json")))[:10]
        except (OSError, ValueError):
            idx = []
        urls = [SITE, SITE + "playback-lab.html", SITE + "archive.html"] + [f"{SITE}posts/{e['slug']}.html" for e in idx]
        L += ["", "## Is Google indexing our key pages? (URL Inspection)", ""]
        for u in urls:
            L.append(f"- {u.replace(SITE, '/')}: {inspect(s, u)}")
    text = "\n".join(L) + "\n"
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"gsc-report-{date.today()}.md")
    open(path, "w").write(text)
    print(text)
    print(f"(saved to {path})")


if __name__ == "__main__":
    sys.exit(main())
