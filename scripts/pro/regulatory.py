"""Regulatory & ETF-Pipeline Tracker.

Two public, free, US-government sources (no key, no scraping of a private site):

  1. The Federal Register API (federalregister.gov): every rule, proposed rule and notice that
     mentions crypto terms, by week, agency and type. Shows whether regulatory attention is
     rising or cooling and lists the latest substantive actions.
  2. SEC EDGAR daily filing indexes (sec.gov/Archives/edgar/daily-index): crypto-linked
     S-1 / S-1/A registrations, 8-A12B exchange registrations and 424B prospectuses. Since the SEC
     adopted generic listing standards, most new spot crypto ETPs no longer need an individual
     exchange rule filing; their registration paperwork on EDGAR is the early signal, and an
     8-A12B means the product is about to list.

Pipeline stage per filer (evidence within the last 120 days, plus the filer's first-ever EDGAR
filing date from its submissions history, so a routine prospectus update from an old fund is not
mistaken for a new product):
    8-A12B filed                        -> "Listing registered"          (about to trade)
    NEW filer (first filing < 90 days) with a 424B -> "Prospectus filed (launching)"
    NEW filer with S-1/A                -> "Registration amended"
    NEW filer with S-1 only             -> "Registration filed"
    older filer                         -> "Established, updating"
Products are labelled ETF/ETP, Treasury company or SPAC from their names.

Regulatory heat: documents in the last 4 weeks versus the average 4-week pace of the prior 12
weeks (Rising above +25%, Cooling below -25%, otherwise Steady).

Limits: the Federal Register search is a TEXT match (a document that mentions "bitcoin" once is
counted), name-based classification of filers is a heuristic, and an S-1 is an intention, not an
approval. Nothing here predicts what the SEC will do.

Data is cached in data/pro/reg_cache.json so each run only fetches what is new.
"""
import json
import os
import re
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

import requests

from .net import get_json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, "data", "pro", "reg_cache.json")
FR = "https://www.federalregister.gov/api/v1/documents.json"
EDGAR_DAILY = "https://www.sec.gov/Archives/edgar/daily-index"
SEC_UA = {"User-Agent": "The Crypto Playback info@cryptoplayback.com", "Accept-Encoding": "gzip, deflate"}

TERMS = ["digital assets", "crypto assets", "crypto-assets", "cryptocurrency", "cryptocurrencies", "bitcoin", "stablecoin", "stablecoins"]
SINCE = "2024-01-01"
EDGAR_BACKFILL_DAYS = 125
PIPELINE_WINDOW_DAYS = 120

CRYPTO_NAME = re.compile(r"\b(bitcoin|btc|ether|ethereum|solana|xrp|ripple|crypto|cryptocurrency|digital assets?|dogecoin|litecoin|sui|avalanche|"
                         r"chainlink|hedera|cardano|polkadot|aptos|near|staking|token|stablecoin|hyperliquid|tron|stellar|bnb)\b", re.I)
FORMS = {"S-1", "S-1/A", "8-A12B", "424B1", "424B2", "424B3", "424B4", "424B5"}
FOCUS = re.compile(r"digital asset|crypto|virtual currency|bitcoin|stablecoin|token|blockchain|distributed ledger|\\bether\\b|custody|commodity-based|commodity based", re.I)
AGENCY_SHORT = {
    "Securities and Exchange Commission": "SEC", "Commodity Futures Trading Commission": "CFTC", "Treasury Department": "Treasury",
    "Comptroller of the Currency": "OCC", "Federal Reserve System": "Fed", "Federal Deposit Insurance Corporation": "FDIC",
    "Internal Revenue Service": "IRS", "Financial Crimes Enforcement Network": "FinCEN", "Consumer Financial Protection Bureau": "CFPB",
}


def _load_cache():
    try:
        return json.load(open(CACHE))
    except (OSError, ValueError):
        return {"fr": {}, "edgar": {"days": [], "filings": []}}


def _save_cache(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(c, open(CACHE + ".tmp", "w"), separators=(",", ":"))
    os.replace(CACHE + ".tmp", CACHE)


# ------------------------------ Federal Register ----------------------------------

def _fr_pull(term, since):
    out, page = [], 1
    while page <= 15:
        params = [("conditions[term]", f'"{term}"'), ("conditions[publication_date][gte]", since), ("per_page", "500"), ("page", str(page)),
                  ("order", "oldest")]
        for f in ("document_number", "title", "type", "publication_date", "agency_names", "html_url"):
            params.append(("fields[]", f))
        d = get_json(FR + "?" + urllib.parse.urlencode(params), timeout=60)
        out.extend(d.get("results", []))
        if page >= d.get("total_pages", 1):
            break
        page += 1
    return out


def update_federal_register(cache):
    fr = cache.setdefault("fr", {})
    since = SINCE
    if fr:
        newest = max(v[0] for v in fr.values())
        since = (datetime.strptime(newest, "%Y-%m-%d") - timedelta(days=21)).strftime("%Y-%m-%d")    # re-check recent days
    for term in TERMS:
        for r in _fr_pull(term, since):
            fr[r["document_number"]] = [r["publication_date"], r.get("type"), "; ".join(r.get("agency_names") or []), (r.get("title") or "")[:190], r.get("html_url")]
    return fr


def _short_agency(names):
    first = (names or "").split("; ")[0]
    return AGENCY_SHORT.get(first, first or "Other")


def summarise_fr(fr):
    rows = [{"d": v[0], "type": v[1], "agency": v[2], "title": v[3], "url": v[4]} for v in fr.values()]
    rows.sort(key=lambda r: r["d"])
    today = datetime.now(timezone.utc).date()

    def weeks_ago(n):
        return (today - timedelta(days=7 * n))
    # weekly counts for the last 52 weeks (weeks start Monday)
    monday = today - timedelta(days=today.weekday())
    wk = {}
    for r in rows:
        d = datetime.strptime(r["d"], "%Y-%m-%d").date()
        m = d - timedelta(days=d.weekday())
        wk[m] = wk.get(m, 0) + 1
    weeks = [monday - timedelta(weeks=i) for i in range(51, -1, -1)]
    counts = [wk.get(w, 0) for w in weeks]
    last4 = sum(counts[-4:])
    prior = counts[-16:-4]
    pace = sum(prior) / 3.0 if prior else None            # prior 12 weeks = three 4-week blocks
    change = None if not pace else (last4 / pace - 1.0) * 100.0
    trend = "Building baseline" if change is None else "Rising" if change > 25 else "Cooling" if change < -25 else "Steady"

    cutoff = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    by_agency, by_type = {}, {}
    for r in rows:
        if r["d"] >= cutoff:
            a = _short_agency(r["agency"])
            by_agency[a] = by_agency.get(a, 0) + 1
            by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    top_agencies = sorted(by_agency.items(), key=lambda kv: -kv[1])[:8]
    # latest substantive actions: rules and proposed rules first, then notices
    focused = [r for r in rows if FOCUS.search(r["title"])]
    substantive = [r for r in focused if r["type"] in ("Rule", "Proposed Rule")][-8:][::-1]
    notices = [r for r in focused if r["type"] == "Notice"][-6:][::-1]
    focused_90d = sum(1 for r in focused if r["d"] >= cutoff)
    return {
        "weekly": {"t": [int(datetime(w.year, w.month, w.day, tzinfo=timezone.utc).timestamp()) for w in weeks], "count": counts},
        "last_4_weeks": last4, "prior_12_week_pace_per_4w": pace, "change_pct": change, "trend": trend,
        "total_since_2024": len(rows), "last_90d": sum(by_type.values()), "focused_90d": focused_90d,
        "by_agency_90d": [{"agency": a, "count": c} for a, c in top_agencies],
        "by_type_90d": by_type,
        "latest_rules": substantive, "latest_notices": notices,
    }


# ------------------------------ EDGAR pipeline ----------------------------------

_LINE = re.compile(r"^(?P<left>.*?)\s+(?P<cik>\d+)\s+(?P<date>\d{8})\s+(?P<file>edgar/\S+)\s*$")


def _edgar_get(url):
    for attempt in range(4):
        r = requests.get(url, headers=SEC_UA, timeout=40)
        if r.status_code == 200:
            return r.text
        if r.status_code == 404:
            return None
        time.sleep(1.5 * (attempt + 1))
    return None


def _parse_daily(text, day):
    out = []
    for line in text.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        left = m.group("left")
        form = left[:17].strip()
        if form not in FORMS:
            continue
        name = left[17:].strip()
        if CRYPTO_NAME.search(name):
            out.append([form, name, m.group("cik"), day, m.group("file")])
    return out


def update_edgar(cache):
    ed = cache.setdefault("edgar", {"days": [], "filings": []})
    done = set(ed["days"])
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=EDGAR_BACKFILL_DAYS)
    d = start
    fetched = 0
    while d <= today:
        day = d.strftime("%Y-%m-%d")
        if d.weekday() < 5 and (day not in done or d >= today - timedelta(days=2)):
            q = (d.month - 1) // 3 + 1
            text = _edgar_get(f"{EDGAR_DAILY}/{d.year}/QTR{q}/form.{d.strftime('%Y%m%d')}.idx")
            if text is not None:
                ed["filings"] = [f for f in ed["filings"] if f[3] != day] + _parse_daily(text, day)
                done.add(day)
                fetched += 1
            elif d < today - timedelta(days=3):
                done.add(day)                        # market holiday: no file, do not retry
            time.sleep(0.15)
        d += timedelta(days=1)
    ed["days"] = sorted(done)
    cutoff = (today - timedelta(days=EDGAR_BACKFILL_DAYS + 10)).strftime("%Y-%m-%d")
    ed["filings"] = [f for f in ed["filings"] if f[3] >= cutoff]
    return ed, fetched


def enrich_first_filing(cache, ciks):
    """{cik: earliest filing date on EDGAR} from each filer's submissions history (cached; one small request per new filer)."""
    first = cache.setdefault("first_filing", {})
    for cik in ciks:
        if cik in first:
            continue
        try:
            r = requests.get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", headers=SEC_UA, timeout=30)
            if r.status_code == 200:
                dates = r.json().get("filings", {}).get("recent", {}).get("filingDate", [])
                first[cik] = min(dates) if dates else None
        except (requests.RequestException, ValueError):
            pass
        time.sleep(0.15)
    return first


def _kind(name):
    n = name.lower()
    if re.search(r"acquisition|spac", n):
        return "SPAC"
    if re.search(r"treasury", n):
        return "Treasury company"
    if re.search(r"etf|etp|trust|fund|shares|index|income|strategy|yield|staking", n):
        return "ETF / ETP"
    return "Other"


def _underlying(name):
    n = name.lower()
    for key, label in (("bitcoin", "Bitcoin"), ("btc", "Bitcoin"), ("ether", "Ether"), ("ethereum", "Ether"), ("solana", "Solana"), ("xrp", "XRP"),
                       ("ripple", "XRP"), ("dogecoin", "Dogecoin"), ("litecoin", "Litecoin"), ("avalanche", "Avalanche"), ("chainlink", "Chainlink"),
                       ("hedera", "Hedera"), ("cardano", "Cardano"), ("sui", "Sui"), ("polkadot", "Polkadot"), ("aptos", "Aptos"), ("near", "NEAR"),
                       ("hyperliquid", "Hyperliquid"), ("tron", "Tron"), ("stellar", "Stellar"), ("bnb", "BNB")):
        if re.search(r"\b" + key + r"\b", n):
            return label
    return "Multi-asset / other"


def summarise_pipeline(ed, first_filing):
    today = datetime.now(timezone.utc).date()
    cutoff = (today - timedelta(days=PIPELINE_WINDOW_DAYS)).strftime("%Y-%m-%d")
    d90 = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    by_cik = {}
    for form, name, cik, day, file in ed["filings"]:
        if day < cutoff:
            continue
        e = by_cik.setdefault(cik, {"name": name, "cik": cik, "forms": {}, "last": day, "last_form": form, "file": file})
        e["forms"][form] = e["forms"].get(form, 0) + 1
        if day >= e["last"]:
            e["last"], e["last_form"], e["file"], e["name"] = day, form, file, name
    products = []
    for e in by_cik.values():
        forms = e["forms"]
        born = first_filing.get(e["cik"])
        is_new = bool(born and born >= d90)
        if "8-A12B" in forms:
            stage, rank = "Listing registered", 5
        elif is_new and any(f.startswith("424B") for f in forms):
            stage, rank = "Prospectus filed (launching)", 4
        elif is_new and "S-1/A" in forms:
            stage, rank = "Registration amended", 3
        elif is_new:
            stage, rank = "Registration filed", 2
        else:
            stage, rank = "Established, updating", 1
        products.append({"name": e["name"], "cik": e["cik"], "kind": _kind(e["name"]), "underlying": _underlying(e["name"]), "stage": stage,
                         "rank": rank, "new": is_new, "first_filing": born, "last_form": e["last_form"], "last_date": e["last"],
                         "filings": sum(forms.values()), "url": f"https://www.sec.gov/Archives/{e['file']}"})
    products.sort(key=lambda p: (p["rank"], p["last_date"]), reverse=True)
    etf = [p for p in products if p["kind"] == "ETF / ETP"]
    summary = {
        "products_tracked": len(products), "etp_count": len(etf),
        "new_etps_90d": sum(1 for p in etf if p["new"]),
        "listing_registered": sum(1 for p in etf if p["stage"] == "Listing registered"),
        "launching": sum(1 for p in etf if p["stage"] == "Prospectus filed (launching)"),
        "in_registration": sum(1 for p in etf if p["stage"] in ("Registration filed", "Registration amended")),
        "established": sum(1 for p in etf if p["stage"] == "Established, updating"),
        "treasury_and_spac": sum(1 for p in products if p["kind"] in ("Treasury company", "SPAC")),
    }
    # weekly count of NEW crypto products (first EDGAR filing), last 26 weeks
    monday = today - timedelta(days=today.weekday())
    weeks = [monday - timedelta(weeks=i) for i in range(15, -1, -1)]      # 16 full weeks: the EDGAR backfill covers about 17
    wk = {}
    for cik, born in first_filing.items():
        if born and cik in by_cik:
            d = datetime.strptime(born, "%Y-%m-%d").date()
            m = d - timedelta(days=d.weekday())
            wk[m] = wk.get(m, 0) + 1
    wf = {}
    for form, name, cik, day, file in ed["filings"]:
        d = datetime.strptime(day, "%Y-%m-%d").date()
        m = d - timedelta(days=d.weekday())
        wf[m] = wf.get(m, 0) + 1
    return {"summary": summary, "products": products[:45],
            "weekly_filings": {"t": [int(datetime(w.year, w.month, w.day, tzinfo=timezone.utc).timestamp()) for w in weeks], "count": [wf.get(w, 0) for w in weeks]}}


def compute():
    cache = _load_cache()
    fr = update_federal_register(cache)
    ed, fetched = update_edgar(cache)
    recent_ciks = sorted({f[2] for f in ed["filings"] if f[3] >= (datetime.now(timezone.utc).date() - timedelta(days=PIPELINE_WINDOW_DAYS)).strftime("%Y-%m-%d")})
    first = enrich_first_filing(cache, recent_ciks)
    _save_cache(cache)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok",
        "activity": summarise_fr(fr), "pipeline": summarise_pipeline(ed, first),
        "coverage": {"federal_register_docs": len(fr), "edgar_days_indexed": len(ed["days"]), "edgar_days_fetched_this_run": fetched,
                     "edgar_window_days": EDGAR_BACKFILL_DAYS},
    }


if __name__ == "__main__":
    t0 = time.time()
    o = compute()
    print(f"{time.time() - t0:.0f}s")
    a = o["activity"]
    print("FR total", a["total_since_2024"], "| last 90d", a["last_90d"], "| last4w", a["last_4_weeks"], "pace", a["prior_12_week_pace_per_4w"], "trend", a["trend"], a["change_pct"])
    print("agencies:", a["by_agency_90d"])
    for r in a["latest_rules"][:5]:
        print("  RULE", r["d"], r["agency"][:22], "|", r["title"][:100])
    p = o["pipeline"]
    print(p["summary"])
    for x in p["products"][:18]:
        print(f"  {x['last_date']} {x['stage']:30s} {x['kind']:16s} {x['underlying']:10s} {x['name'][:46]} (first {x['first_filing']}, {x['filings']} filings)")
    print(o["coverage"])
