"""Protocol Revenue / TVL Quality Score (DeFi).

Ranks DeFi protocols by how much real fee income each dollar of locked value
produces, and how steady and growing that income is. Data: DefiLlama's free
public API (no key): /protocols (TVL), /overview/fees (fees and revenue
windows), /summary/fees/{slug} (daily fee history).

Universe: protocols with TVL >= $100M and 30-day fees >= $250k, then the
top 60 by 30-day fees (so the percentile baseline is stable).

Score (0-100) = weighted average of four percentile ranks within that universe:
  Fee yield      35%  annualised fees (30d x 365/30) / TVL
  Stability      25%  low coefficient of variation of daily fees (last 90 days)
  Growth         20%  50% 30d-vs-previous-30d, 50% 7d-vs-previous-7d fee growth
  Scale          20%  annualised fees in dollars (log scale)
Revenue yield (protocol revenue / TVL) is shown beside fee yield but is not
scored, because DefiLlama's revenue definition differs by protocol type.

Concentration: share of all tracked 30-day fees earned by the top 5 / top 10
protocols and the Herfindahl index (HHI, 0-10,000) across protocols.

Caveats: fees and TVL are self-reported by DefiLlama adapters and can be
revised; TVL is point-in-time while fees are windows; protocols with no TVL
(stablecoin issuers, some perps) are excluded because the ratio is undefined.
Score history is accumulated by this job once a day (data/pro/quality_history.json).
"""
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .net import get_json
from .stats import mean, stdev, percentile_rank

LLAMA = "https://api.llama.fi"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HIST_FILE = os.path.join(ROOT, "data", "pro", "quality_history.json")
WEIGHTS = {"yield": 0.35, "stability": 0.25, "growth": 0.20, "scale": 0.20}
MIN_TVL, MIN_FEES_30D, UNIVERSE = 100e6, 250e3, 60


def _overview(kind):
    d = get_json(f"{LLAMA}/overview/fees", timeout=90,
                 params={"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true", "dataType": kind})
    return {p["slug"]: p for p in d["protocols"] if p.get("slug")}


def _fee_history(slug):
    try:
        d = get_json(f"{LLAMA}/summary/fees/{slug}", params={"dataType": "dailyFees"}, timeout=60)
        return [v for _, v in d.get("totalDataChart", [])][:-1][-90:]       # drop today's partial day
    except Exception:       # noqa: BLE001
        return []


def _growth(cur, prev):
    return None if not prev else (cur / prev - 1.0) * 100.0


def compute():
    fees = _overview("dailyFees")
    rev = _overview("dailyRevenue")
    protos = {p["slug"]: p for p in get_json(f"{LLAMA}/protocols", timeout=120)}

    # concentration over everything that reports fees
    tot30 = {s: (p.get("total30d") or 0) for s, p in fees.items()}
    grand = sum(tot30.values()) or 1.0
    ranked = sorted(tot30.values(), reverse=True)
    conc = {
        "top5_share_pct": round(100 * sum(ranked[:5]) / grand, 1),
        "top10_share_pct": round(100 * sum(ranked[:10]) / grand, 1),
        "hhi": round(sum((100 * v / grand) ** 2 for v in ranked)),
        "protocols_tracked": sum(1 for v in ranked if v > 0),
        "fees_30d_usd": grand,
    }
    cats = {}
    for s, p in fees.items():
        cats[p.get("category") or "Other"] = cats.get(p.get("category") or "Other", 0) + tot30[s]
    top_cats = sorted(cats.items(), key=lambda kv: -kv[1])[:5]
    conc["top_categories"] = [{"category": c, "share_pct": round(100 * v / grand, 1)} for c, v in top_cats]

    cand = []
    for slug, f in fees.items():
        pr = protos.get(slug)
        tvl = (pr or {}).get("tvl")
        f30 = f.get("total30d") or 0
        if pr and tvl and tvl >= MIN_TVL and f30 >= MIN_FEES_30D:
            cand.append((slug, f, pr, tvl, f30))
    cand.sort(key=lambda x: -x[4])
    cand = cand[:UNIVERSE]
    if len(cand) < 15:
        raise RuntimeError(f"only {len(cand)} protocols qualified; refusing to publish a thin ranking")

    with ThreadPoolExecutor(max_workers=6) as ex:
        series = list(ex.map(lambda c: _fee_history(c[0]), cand))

    rows = []
    for (slug, f, pr, tvl, f30), daily in zip(cand, series):
        ann = f30 * 365.0 / 30.0
        r30 = (rev.get(slug) or {}).get("total30d")
        cv = None
        if len(daily) >= 30 and mean(daily):
            cv = stdev(daily) / mean(daily)
        g30 = _growth(f30, f.get("total60dto30d") and (f["total60dto30d"]))
        g7 = _growth(f.get("total7d") or 0, f.get("total14dto7d"))
        gs = [g for g in (g30, g7) if g is not None]
        rows.append({
            "slug": slug, "name": f.get("displayName") or f["name"], "category": f.get("category"),
            "chains": (f.get("chains") or [])[:4], "tvl_usd": tvl, "fees_30d_usd": f30,
            "annualized_fees_usd": ann, "revenue_30d_usd": r30,
            "fee_yield_pct": ann / tvl * 100.0,
            "revenue_yield_pct": (r30 * 365.0 / 30.0 / tvl * 100.0) if r30 is not None else None,
            "fee_cv": cv, "growth_30d_pct": g30, "growth_7d_pct": g7,
            "_growth_blend": mean([max(-100, min(300, g)) for g in gs]) if gs else None,
        })

    ys = [r["fee_yield_pct"] for r in rows]
    cvs = [-r["fee_cv"] for r in rows if r["fee_cv"] is not None]
    gr = [r["_growth_blend"] for r in rows if r["_growth_blend"] is not None]
    sc = [math.log10(r["annualized_fees_usd"]) for r in rows]
    for r in rows:
        comp = {
            "yield": percentile_rank(r["fee_yield_pct"], ys),
            "stability": percentile_rank(-r["fee_cv"], cvs) if r["fee_cv"] is not None else None,
            "growth": percentile_rank(r["_growth_blend"], gr) if r["_growth_blend"] is not None else None,
            "scale": percentile_rank(math.log10(r["annualized_fees_usd"]), sc),
        }
        num = sum(WEIGHTS[k] * v for k, v in comp.items() if v is not None)
        den = sum(WEIGHTS[k] for k, v in comp.items() if v is not None)
        r["score"] = round(num / den, 1)
        r["components"] = {k: (None if v is None else round(v)) for k, v in comp.items()}
        r.pop("_growth_blend")
    rows.sort(key=lambda r: -r["score"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    # accumulate daily score history for the top protocols
    hist = {}
    try:
        hist = json.load(open(HIST_FILE))
    except (OSError, ValueError):
        pass
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hist[today] = {r["slug"]: r["score"] for r in rows[:30]}
    for d in sorted(hist)[:-120]:
        hist.pop(d)
    os.makedirs(os.path.dirname(HIST_FILE), exist_ok=True)
    json.dump(hist, open(HIST_FILE, "w"))
    for r in rows:
        r["history"] = [{"d": d, "score": hist[d][r["slug"]]} for d in sorted(hist) if r["slug"] in hist[d]]

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "ok",
        "weights": WEIGHTS, "universe": len(rows), "protocols": rows, "concentration": conc,
    }


if __name__ == "__main__":
    out = compute()
    for r in out["protocols"][:12]:
        print(f"{r['rank']:2d} {r['score']:5.1f} {r['name'][:22]:22s} {r['category'][:12]:12s} TVL ${r['tvl_usd']/1e6:8.0f}M fees30d ${r['fees_30d_usd']/1e6:6.1f}M "
              f"yield {r['fee_yield_pct']:6.1f}% cv {r['fee_cv'] if r['fee_cv'] is None else round(r['fee_cv'],2)} g30 {r['growth_30d_pct'] if r['growth_30d_pct'] is None else round(r['growth_30d_pct'])}% {r['components']}")
    print(out["concentration"])
