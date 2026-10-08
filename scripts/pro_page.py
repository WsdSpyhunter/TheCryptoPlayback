"""Renders institutional.html (the "Institutional / Pro Indicators" page) in the
Version 2 look from the JSON files written by `pro.refresh_pro`.

Markup only: nothing here fetches data. Charts are inline SVG generated at
build time (no JavaScript, no chart library), so the page is fast, printable
and each section can later be gated independently (every indicator is its own
<section> fed by its own data file).
"""
import json
import os
from datetime import datetime, timezone
from html import escape

from partials import page
import v2_ui as ui

try:
    from zoneinfo import ZoneInfo
    CENTRAL = ZoneInfo("America/Chicago")
except Exception:  # pragma: no cover
    CENTRAL = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "pro")
PAGE_FILE = "institutional.html"


# ------------------------------ helpers ------------------------------------

def _load(name):
    try:
        return json.load(open(os.path.join(DATA, f"{name}.json")))
    except (OSError, ValueError):
        return None


def money(v, dp=1):
    if v is None:
        return "n/a"
    a = abs(v)
    sign = "-" if v < 0 else ""
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"{sign}${a / div:,.{dp}f}{suf}"
    return f"{sign}${a:,.0f}"


def signed_money(v, dp=1):
    return "n/a" if v is None else ("+" if v >= 0 else "") + money(v, dp)


def pct(v, dp=1, signed=True):
    if v is None:
        return "n/a"
    if round(v, dp) == 0:
        v = 0.0                                   # avoid "-0%"
    return f"{v:+.{dp}f}%" if signed else f"{v:.{dp}f}%"


def updated(iso):
    if not iso:
        return "pending"
    dt = datetime.fromisoformat(iso)
    if CENTRAL:
        dt = dt.astimezone(CENTRAL)
        return dt.strftime("%b %-d, %-I:%M %p CT")
    return dt.strftime("%b %-d, %H:%M UTC")


def _tone(v, good_high=True):
    if v is None:
        return "flat"
    return "up" if (v > 0) == good_high and v != 0 else ("down" if v != 0 else "flat")


def heat(v):
    """0-100 risk -> cell colour on the dark panel (navy -> brass -> red)."""
    if v is None:
        return "#12294A"
    v = max(0, min(100, v))
    stops = [(0, (18, 41, 74)), (50, (138, 106, 31)), (100, (179, 55, 47))]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if v <= b:
            t = (v - a) / (b - a)
            return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))
    return "#B3372F"


# ------------------------------ SVG charts ---------------------------------

def line_chart(ts, ys, color="#8A6A1F", w=760, h=230, zero=False, fmt="{:.2f}", band=None, area=True, label=""):
    pts = [(t, y) for t, y in zip(ts, ys) if y is not None]
    if len(pts) < 2:
        return '<p class="pro-empty">Chart builds as history accumulates.</p>'
    pad_l, pad_r, pad_t, pad_b = 52, 14, 14, 26
    xs = [p[0] for p in pts]
    vals = [p[1] for p in pts]
    lo, hi = min(vals), max(vals)
    if zero:
        lo, hi = min(lo, 0), max(hi, 0)
    if band:
        lo, hi = min(lo, band[0]), max(hi, band[1])
    if hi == lo:
        hi, lo = hi + 1, lo - 1
    span = hi - lo
    lo, hi = lo - span * 0.08, hi + span * 0.08
    X = lambda t: pad_l + (t - xs[0]) / (xs[-1] - xs[0]) * (w - pad_l - pad_r)      # noqa: E731
    Y = lambda v: pad_t + (hi - v) / (hi - lo) * (h - pad_t - pad_b)                  # noqa: E731
    path = "M" + " L".join(f"{X(t):.1f} {Y(v):.1f}" for t, v in pts)
    out = [f'<svg class="pro-chart" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}" preserveAspectRatio="xMidYMid meet">']
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = Y(v)
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="pro-grid"/>'
                   f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" class="pro-axis">{fmt.format(v)}</text>')
    if band:
        out.append(f'<rect x="{pad_l}" y="{Y(band[1]):.1f}" width="{w - pad_l - pad_r}" height="{Y(band[0]) - Y(band[1]):.1f}" class="pro-band"/>')
    if zero and lo < 0 < hi:
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" class="pro-zero"/>')
    if area:
        base = Y(max(lo, min(hi, 0))) if zero else h - pad_b
        out.append(f'<path d="{path} L{X(xs[-1]):.1f} {base:.1f} L{X(xs[0]):.1f} {base:.1f} Z" fill="{color}" opacity=".12"/>')
    out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round"/>')
    out.append(f'<circle cx="{X(xs[-1]):.1f}" cy="{Y(vals[-1]):.1f}" r="4" fill="{color}"/>')
    for t in (xs[0], xs[len(xs) // 2], xs[-1]):
        d = datetime.fromtimestamp(t, timezone.utc).strftime("%b %-d")
        anchor = "start" if t == xs[0] else "end" if t == xs[-1] else "middle"
        out.append(f'<text x="{X(t):.1f}" y="{h - 6}" text-anchor="{anchor}" class="pro-axis">{d}</text>')
    out.append("</svg>")
    return "".join(out)


def sparkline(vals, color="#D4B063", w=120, h=34):
    v = [x for x in vals if x is not None]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    hi = hi if hi != lo else lo + 1
    pts = " ".join(f"{i * (w - 4) / (len(v) - 1) + 2:.1f},{h - 3 - (x - lo) / (hi - lo) * (h - 6):.1f}" for i, x in enumerate(v))
    return (f'<svg class="pro-spark" viewBox="0 0 {w} {h}" aria-hidden="true"><polyline points="{pts}" fill="none" '
            f'stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>')


def zbar(z, scale=3.0):
    """Diverging bar: red to the left of centre, green to the right."""
    if z is None:
        return '<span class="pro-zbar"><span class="pro-zmid"></span></span>'
    width = min(abs(z) / scale, 1.0) * 50
    side = "pos" if z >= 0 else "neg"
    left = 50 if z >= 0 else 50 - width
    return (f'<span class="pro-zbar" aria-hidden="true"><span class="pro-zfill {side}" '
            f'style="left:{left:.1f}%;width:{width:.1f}%"></span><span class="pro-zmid"></span></span>')


def _stale(data):
    return ('<p class="pro-stale">Showing the last good reading: a data source was unavailable on the latest refresh.</p>'
            if data and data.get("status") == "stale" else "")


def _empty(title):
    return f'<p class="pro-empty">{escape(title)} is collecting its first reading. Check back after the next refresh.</p>'


# ------------------------------ sections -----------------------------------

def overview_cards(p, u, q, s):
    cards = []
    if p:
        z = p["score_z"]
        cards.append(("pressure", "Institutional Pressure", f"{z:+.2f}", p["regime"], _tone(z) if abs(z) >= 1 else "flat",
                      sparkline([h["z"] for h in p["history"]]), p["updated_at"]))
    if u:
        top = u["assets"][0]
        cards.append(("unwind", "Crowded Unwind Risk", f"{top['score']:.0f}", f"Highest: {top['symbol']} ({top['label']})",
                      "down" if top["score"] >= 75 else "flat", sparkline([h["score"] for h in top["history"]]), u["updated_at"]))
    if q:
        top = q["protocols"][0]
        cards.append(("quality", "Revenue / TVL Quality", f"{top['score']:.0f}", f"Top: {top['name']}", "up",
                      "", q["updated_at"]))
    if s:
        cards.append(("stables", "Stablecoin Flows", pct(s["totals"]["change_7d_pct"]), f"{s['flow']['label']} · velocity {s['velocity']['label'].lower()}",
                      _tone(s["totals"]["change_7d_pct"]), sparkline(s["history"]["supply_usd"][-60:]), s["updated_at"]))
    html = ""
    for key, name, big, sub, tone, spark, upd in cards:
        html += (f'<a class="pro-ov" href="#{key}"><span class="pro-ov-name">{name}</span>'
                 f'<span class="pro-ov-big {tone}">{big}</span><span class="pro-ov-sub">{escape(sub)}</span>{spark}'
                 f'<span class="pro-ov-upd">Updated {updated(upd)}</span></a>')
    return f'<div class="pro-overview">{html}</div>' if html else ""


def sec_pressure(p):
    head = ui.title_box("capital_flow", '<span id="pressure-h">Basic Institutional Pressure Index</span>',
                        f"Updated {updated(p['updated_at'])}" if p else "")
    if not p:
        return f'<section class="v2-section" id="pressure">{_wrap(head + _empty("The Institutional Pressure Index"))}</section>'
    z = p["score_z"]
    tone = "up" if z >= 1 else "down" if z <= -1 else "flat"
    comps = ""
    for c in p["components"]:
        comps += (f'<div class="pro-comp"><div class="pro-comp-top"><span class="pro-comp-name">{escape(c["label"])}</span>'
                  f'<span class="pro-comp-w">{c["weight"] * 100:.0f}% weight</span></div>'
                  f'<div class="pro-comp-z {_tone(c["z"])}">{"n/a" if c["z"] is None else f"{c["z"]:+.2f}"}<small> z</small></div>'
                  f'{zbar(c["z"])}<div class="pro-comp-read">{escape(c["readout"])}</div></div>')
    chart = line_chart([h["t"] for h in p["history"]], [h["z"] for h in p["history"]], zero=True,
                       band=(-1, 1), fmt="{:+.1f}", label="Institutional Pressure Index, z-score, last 30 days")
    method = """<details class="pro-method"><summary>How this score is calculated</summary>
      <p>Each component is converted to a trailing z-score (how unusual today's reading is versus its own recent past, with no look-ahead),
      clipped to ±3, and blended with the weights shown. The blend is the score (z, roughly −2 to +2); the percentile is the normal-curve
      position of that z (0–100). Regimes: z ≥ +1.0 Strong Buy Pressure, z ≤ −1.0 Strong Sell Pressure, otherwise Neutral.</p>
      <ul><li><strong>ETF net flow (30%):</strong> US spot Bitcoin ETF daily net flow; half 1-day flow, half rolling 5-day sum. A day counts from the next 00:00 UTC.</li>
      <li><strong>Coinbase Premium (20%):</strong> Coinbase BTC-USD versus OKX BTC-USDT converted to dollars with the Kraken USDT/USD rate; half 6-hour mean, half 24-hour mean.</li>
      <li><strong>Funding pressure (25%):</strong> open-interest-weighted perpetual funding (per 8 hours) across OKX, Gate and Hyperliquid. Positive means longs are paying shorts.</li>
      <li><strong>Open interest × price (25%):</strong> 24-hour change in aggregate BTC open interest (Gate + OKX), signed by the 24-hour price direction.</li></ul>
      <p class="pro-caveat">A descriptive gauge of positioning, not a forecast. Weights are configurable (scripts/pro/pressure.py). ETF history is short
      (the dataset began in late September), so the ETF z-score is based on fewer observations than the other components.</p></details>"""
    body = f"""{_stale(p)}
    <div class="pro-hero-grid">
      <div class="pro-score-card">
        <div class="pro-score-label">Current reading</div>
        <div class="pro-score-big {tone}">{z:+.2f}</div>
        <div class="pro-score-regime {tone}">{escape(p['regime'])}</div>
        <div class="pro-score-pct">{p['score_pct']:.0f}<small>/100 percentile</small></div>
      </div>
      <div class="pro-chart-card"><div class="pro-chart-title">Score history, last 30 days (shaded band = Neutral)</div>{chart}</div>
    </div>
    <div class="pro-comps">{comps}</div>
    {method}"""
    return f'<section class="v2-section" id="pressure" aria-labelledby="pressure-h">{_wrap(head + body)}</section>'


def sec_unwind(u):
    head = ui.title_box("liquidations", '<span id="unwind-h">Crowded Unwind Risk Map</span>',
                        f"Updated {updated(u['updated_at'])}" if u else "", dark=True)
    if not u:
        return f'<section class="v2-dark" id="unwind">{_wrap(head + _empty("The Crowded Unwind Risk Map"))}</section>'
    cols = [("oi", "OI"), ("funding", "Funding"), ("lsr", "L/S skew"), ("liq", "Liq. heat"), ("adverse", "Adverse")]
    rows = ""
    for a in u["assets"]:
        cells = "".join(
            f'<td class="pro-hm" style="background:{heat(a["components"].get(k))}" title="{lab} percentile: {a["components"].get(k)}">'
            f'{"–" if a["components"].get(k) is None else a["components"][k]}</td>' for k, lab in cols)
        dir_cls = "long" if a["direction"] == "Crowded long" else "short" if a["direction"] == "Crowded short" else "bal"
        fund = a.get("funding_8h_agg")
        venues = ""
        for v in a.get("venues", []):
            venues += (f'<tr><td>{v["venue"]}</td><td>{money(v["oi_usd"])}</td>'
                       f'<td>{v["funding_8h"] * 100:+.4f}%</td></tr>')
        detail = (f'<details class="pro-venues"><summary>Cross-venue</summary><table><thead><tr><th>Venue</th><th>Open interest</th><th>Funding / 8h</th></tr></thead>'
                  f'<tbody>{venues}</tbody></table></details>') if venues else ""
        rows += (f'<tr><th scope="row"><span class="pro-sym">{a["symbol"]}</span></th>'
                 f'<td><span class="pro-scorebar"><span style="width:{a["score"]:.0f}%;background:{heat(a["score"])}"></span></span>'
                 f'<span class="pro-scoreval">{a["score"]:.0f}</span><span class="pro-lab {a["label"].lower()}">{a["label"]}</span></td>'
                 f'<td><span class="pro-dir {dir_cls}">{a["direction"]}</span></td>{cells}'
                 f'<td class="pro-num">{money(a.get("oi_all_venues_usd"))}</td>'
                 f'<td class="pro-num">{"n/a" if fund is None else f"{fund * 100:+.4f}%"}</td>'
                 f'<td class="pro-num">{"n/a" if a.get("lsr_gate") is None else f"{a['lsr_gate']:.2f}"}</td>'
                 f'<td>{sparkline([h["score"] for h in a["history"]], w=90, h=26)}{detail}</td></tr>')
    th = "".join(f"<th>{lab}</th>" for _, lab in cols)
    method = """<details class="pro-method dark"><summary>How this score is calculated</summary>
      <p>Each asset gets a 0–100 score from five components, each a percentile of that asset's own trailing 30 days (so a coin is compared with itself):
      <strong>OI crowding 30%</strong> (open interest versus its own range), <strong>Funding 30%</strong> (60% size of |funding| versus its history + 40%
      persistence: how much of the last 24 hours had the same sign and at least median size), <strong>Long/short skew 20%</strong> (how far the long/short
      account ratio sits from its own median), <strong>Liquidation heat 10%</strong> (24-hour liquidations as a share of open interest) and
      <strong>Adverse move 10%</strong> (a 24-hour price move against the crowded side). Bands: Low under 35, Moderate 35–55, High 55–75, Extreme 75+.</p>
      <p>Direction is a vote between the sign of funding and the sign of the long/short ratio's deviation from its median. The score and its history are computed on
      Gate.io hourly contract statistics; the cross-venue table (OKX, Gate, Hyperliquid, Bitget, Deribit, Kraken) is shown for context and does not change the score.</p>
      <p class="pro-caveat">Not modelled because free data does not exist: liquidation-price cluster maps and order-book depth. Liquidation volumes are those observed on Gate.io
      (a sample of the market). Binance and Bybit block US servers and are not used.</p></details>"""
    body = f"""{_stale(u)}
    <p class="pro-lead dark">Which large perpetual-futures markets look most crowded and fragile? Higher scores mean positioning is more stretched and a leveraged unwind
    would be more violent. Cells show each component's percentile (0–100).</p>
    <div class="pro-table-wrap"><table class="pro-table pro-unwind"><thead><tr><th>Asset</th><th>Risk score</th><th>Direction</th>{th}
      <th>Total OI</th><th>Funding/8h</th><th>L/S</th><th>14d</th></tr></thead><tbody>{rows}</tbody></table></div>
    {method}"""
    return f'<section class="v2-dark" id="unwind" aria-labelledby="unwind-h">{_wrap(head + body)}</section>'


def sec_quality(q):
    head = ui.title_box("stablecoin_liquidity", '<span id="quality-h">Protocol Revenue / TVL Quality Score</span>',
                        f"Updated {updated(q['updated_at'])}" if q else "")
    if not q:
        return f'<section class="v2-section" id="quality">{_wrap(head + _empty("The Quality Score"))}</section>'
    c = q["concentration"]
    kpis = (f'<div class="pro-kpis"><div class="pro-kpi"><span>Top 5 protocols</span><strong>{c["top5_share_pct"]:.1f}%</strong><small>of tracked 30-day fees</small></div>'
            f'<div class="pro-kpi"><span>Top 10 protocols</span><strong>{c["top10_share_pct"]:.1f}%</strong><small>of tracked 30-day fees</small></div>'
            f'<div class="pro-kpi"><span>Fee concentration (HHI)</span><strong>{c["hhi"]:,}</strong><small>0 = spread out · 10,000 = one protocol</small></div>'
            f'<div class="pro-kpi"><span>Tracked 30-day fees</span><strong>{money(c["fees_30d_usd"])}</strong><small>{c["protocols_tracked"]:,} protocols reporting</small></div></div>')
    rows = ""
    for r in q["protocols"][:30]:
        comp = r["components"]
        hist = sparkline([h["score"] for h in r["history"]], color="#8A6A1F", w=80, h=24) if len(r["history"]) >= 2 else '<span class="pro-muted">building</span>'
        rows += (f'<tr><td class="pro-num">{r["rank"]}</td><th scope="row"><span class="pro-pname">{escape(r["name"])}</span>'
                 f'<span class="pro-pcat">{escape(r.get("category") or "")}</span></th>'
                 f'<td><span class="pro-scorebar light"><span style="width:{r["score"]:.0f}%"></span></span><span class="pro-scoreval">{r["score"]:.0f}</span></td>'
                 f'<td class="pro-num">{money(r["tvl_usd"])}</td><td class="pro-num">{money(r["fees_30d_usd"])}</td>'
                 f'<td class="pro-num">{r["fee_yield_pct"]:.1f}%</td>'
                 f'<td class="pro-num">{"n/a" if r["revenue_yield_pct"] is None else f"{r['revenue_yield_pct']:.1f}%"}</td>'
                 f'<td class="pro-num">{"n/a" if r["fee_cv"] is None else f"{r['fee_cv']:.2f}"}</td>'
                 f'<td class="pro-num {_tone(r["growth_30d_pct"])}">{pct(r["growth_30d_pct"], 0)}</td>'
                 f'<td class="pro-sub">{comp.get("yield", "–")}/{comp.get("stability", "–")}/{comp.get("growth", "–")}/{comp.get("scale", "–")}</td>'
                 f'<td>{hist}</td></tr>')
    method = """<details class="pro-method"><summary>How this score is calculated</summary>
      <p>Universe: DeFi protocols with TVL ≥ $100M and 30-day fees ≥ $250k, limited to the top 60 by 30-day fees. The score (0–100) is a weighted average of four
      percentile ranks inside that universe: <strong>Fee yield 35%</strong> (annualised 30-day fees ÷ TVL), <strong>Stability 25%</strong> (low coefficient of variation of daily fees over
      90 days), <strong>Growth 20%</strong> (half 30-day-over-previous-30-day, half 7-day-over-previous-7-day fee growth) and <strong>Scale 20%</strong> (annualised fees, log scale).
      The four sub-scores are listed as yield/stability/growth/scale. Revenue yield (protocol revenue ÷ TVL) is shown but not scored because DefiLlama's revenue definition differs by protocol type.</p>
      <p class="pro-caveat">Fees and TVL are self-reported through DefiLlama adapters and can be revised. Fee yield is not an LP return. Protocols without TVL (stablecoin issuers, some perpetual venues) are excluded.
      Score history is recorded once a day and builds from the first run.</p></details>"""
    body = f"""{_stale(q)}
    <p class="pro-lead">Which protocols turn locked capital into the most reliable, growing fee income? Ranked by a transparent four-part score.</p>
    {kpis}
    <div class="pro-table-wrap"><table class="pro-table pro-quality"><thead><tr><th>#</th><th>Protocol</th><th>Quality score</th><th>TVL</th><th>30d fees</th>
      <th>Fee yield (ann.)</th><th>Revenue yield</th><th>Fee volatility (CV)</th><th>30d growth</th><th>Y/S/G/S</th><th>Trend</th></tr></thead><tbody>{rows}</tbody></table></div>
    {method}"""
    return f'<section class="v2-section" id="quality" aria-labelledby="quality-h">{_wrap(head + body)}</section>'


def sec_stables(s):
    head = ui.title_box("stablecoin_liquidity", '<span id="stables-h">Basic Stablecoin Velocity &amp; Flows</span>',
                        f"Updated {updated(s['updated_at'])}" if s else "", dark=True)
    if not s:
        return f'<section class="v2-dark" id="stables">{_wrap(head + _empty("Stablecoin Flows"))}</section>'
    t = s["totals"]
    f, v = s["flow"], s["velocity"]
    kpis = (f'<div class="pro-kpis dark"><div class="pro-kpi"><span>Stablecoin supply</span><strong>{money(t["supply_usd"])}</strong><small>{pct(t["change_7d_pct"], 2)} 7d · {pct(t["change_30d_pct"], 2)} 30d</small></div>'
            f'<div class="pro-kpi"><span>Net issuance, 7 days</span><strong class="{_tone(t["net_issuance_7d_usd"])}">{signed_money(t["net_issuance_7d_usd"])}</strong><small>{signed_money(t["net_issuance_30d_usd"])} over 30 days</small></div>'
            f'<div class="pro-kpi"><span>Flow signal</span><strong>{escape(f["label"])}</strong><small>z {"n/a" if f["z"] is None else f"{f["z"]:+.2f}"} vs trailing year</small></div>'
            f'<div class="pro-kpi"><span>Velocity (DEX turnover)</span><strong>{v["turnover_pct"]:.2f}%/day</strong><small>{escape(v["label"])} · z {"n/a" if v["z"] is None else f"{v["z"]:+.2f}"}</small></div></div>')
    h = s["history"]
    ch1 = line_chart(h["t"], [x / 1e9 for x in h["supply_usd"]], color="#D4B063", fmt="${:.0f}B", label="Stablecoin supply, last 180 days")
    ch2 = line_chart(h["t"], h["turnover_pct"], color="#8FD0AC", fmt="{:.1f}%", label="DEX turnover as a percent of stablecoin supply, last 180 days")
    coins = "".join(
        f'<tr><th scope="row">{c["symbol"]}</th><td class="pro-num">{money(c["supply_usd"])}</td><td class="pro-num">{c["share_pct"]:.1f}%</td>'
        f'<td class="pro-num {_tone(c["change_7d_pct"])}">{pct(c["change_7d_pct"], 2)}</td><td class="pro-num {_tone(c["change_30d_pct"])}">{pct(c["change_30d_pct"], 2)}</td>'
        f'<td class="pro-num">{"non-par" if c.get("non_par") else ("n/a" if c["peg_deviation_bps"] is None else f"{c["peg_deviation_bps"]:+.1f} bps")}</td></tr>'
        for c in s["coins"])
    chains = "".join(
        f'<tr><th scope="row">{c["chain"]}</th><td class="pro-num">{money(c["supply_usd"])}</td><td class="pro-num">{c["share_pct"]:.1f}%</td>'
        f'<td class="pro-num {_tone(c["net_7d_usd"])}">{signed_money(c["net_7d_usd"])}</td><td class="pro-num {_tone(c["net_30d_usd"])}">{signed_money(c["net_30d_usd"])}</td></tr>'
        for c in s["chains"])
    movers = ", ".join(f'{m["chain"]} ({signed_money(m["net_7d_usd"])})' for m in s["chain_movers"][:4])
    method = """<details class="pro-method dark"><summary>How these readings are calculated</summary>
      <p><strong>Supply and net issuance:</strong> total circulating USD-pegged stablecoins; the dollar change in supply over 1, 7 and 30 days is a net mint-minus-burn proxy.
      <strong>Chain deployment:</strong> supply per chain and its 7- and 30-day net change, showing where new dollars land. <strong>Velocity proxy:</strong> 7-day average daily DEX volume ÷ stablecoin supply ("DEX turnover").
      <strong>Flow signal:</strong> z-score of the latest 7-day supply change against the last 365 days of 7-day changes. <strong>Velocity signal:</strong> z-score of turnover against its trailing 365 days.
      Coins priced more than 3% from $1.00 are yield-bearing or tokenised-fund products and are shown as non-par, not as depegs.</p>
      <p class="pro-caveat">Free exchange-reserve and exchange-netflow data does not exist, so those are not modelled. DEX turnover is an on-chain activity proxy, not payments velocity,
      and perpetual-DEX volume is not included.</p></details>"""
    body = f"""{_stale(s)}
    <p class="pro-lead dark">Is dollar liquidity being created, and is it being used? Net issuance, where new supply is landing, and how actively it trades on-chain.</p>
    {kpis}
    <div class="pro-two"><div class="pro-chart-card dark"><div class="pro-chart-title">Total stablecoin supply</div>{ch1}</div>
      <div class="pro-chart-card dark"><div class="pro-chart-title">DEX turnover (7-day avg DEX volume ÷ supply)</div>{ch2}</div></div>
    <div class="pro-two">
      <div class="pro-table-wrap"><table class="pro-table"><caption>Major stablecoins</caption><thead><tr><th>Coin</th><th>Supply</th><th>Share</th><th>7d</th><th>30d</th><th>Peg</th></tr></thead><tbody>{coins}</tbody></table></div>
      <div class="pro-table-wrap"><table class="pro-table"><caption>Where stablecoins are deployed</caption><thead><tr><th>Chain</th><th>Supply</th><th>Share</th><th>7d net</th><th>30d net</th></tr></thead><tbody>{chains}</tbody></table>
      <p class="pro-note">Biggest 7-day movers: {movers}.</p></div>
    </div>
    {method}"""
    return f'<section class="v2-dark" id="stables" aria-labelledby="stables-h">{_wrap(head + body)}</section>'


def sec_sources():
    head = ui.title_box("book", '<span id="sources-h">Methodology, Data Sources &amp; Limits</span>', "Everything is free public data")
    body = """<p class="pro-lead">Every number on this page is computed from free public data with no paid vendor and no API key. The formulas are
    published beside each indicator and in the open source code (<code>scripts/pro/</code>).</p>
    <div class="pro-sources">
      <div><h3>Derivatives</h3><p>OKX, Gate.io, Hyperliquid, Bitget, Deribit and Kraken Futures public market-data endpoints: open interest, funding, long/short ratios and liquidations.
      Binance and Bybit refuse US-based servers, so they are not used.</p></div>
      <div><h3>Prices</h3><p>Coinbase Exchange, OKX and Kraken public prices for the Coinbase Premium (Coinbase versus OKX, dollar-adjusted with Kraken USDT/USD).</p></div>
      <div><h3>ETF flows</h3><p>US spot Bitcoin ETF daily net flows from the site's own ETF dataset (SoSoValue, cross-checked against XOOMAR). Farside Investors was not used because it blocks automated access.</p></div>
      <div><h3>DeFi and stablecoins</h3><p>DefiLlama's free public API: protocols, TVL, fees and revenue, stablecoin supply by coin and chain, and DEX volume.</p></div>
    </div>
    <div class="pro-disclaimer"><strong>Experimental research tools, not financial advice.</strong> These indicators describe market positioning and data
    reported by third parties; they are not forecasts, and sources can be delayed, revised or wrong. Do not trade on any single number here.</div>"""
    return f'<section class="v2-section v2-section-white" id="sources" aria-labelledby="sources-h">{_wrap(head + body)}</section>'


def _wrap(inner):
    return f'<div class="v2-wrap">{inner}</div>'


def hero(meta):
    return f"""<section class="pro-hero">
  <div class="v2-wrap">
    <div class="v2-kicker v2-kicker-brass">Institutional indicators · experimental</div>
    <h1>Institutional Indicators</h1>
    <p>Four institutional-style readings of Bitcoin and crypto market structure: who is pressing, who is crowded, which protocols earn their keep,
    and where dollar liquidity is flowing. Built only from free public data and fully documented.</p>
    <nav class="pro-jump" aria-label="Indicators"><a href="#pressure">Pressure Index</a><a href="#unwind">Unwind Risk</a><a href="#quality">Revenue / TVL</a><a href="#stables">Stablecoin Flows</a><a href="#sources">Methodology</a></nav>
  </div>
</section>"""


def _footer_links():
    """Footer 'Live indicators' list (same registry the homepage uses)."""
    try:
        import build_site as bs
        import home_v2
        entries = bs.load_index()
        dash = bs._load_dashboard_data(entries)
        ctx = bs._build_indicator_registry(dash, dash["gauge_path"])
        return home_v2.indicator_footer_links(ctx["indicators"])
    except Exception:       # noqa: BLE001 - footer links are optional
        return ""


def render_institutional():
    p, u, q, s = _load("pressure"), _load("unwind"), _load("quality"), _load("stables")
    meta = _load("meta") or {}
    ov = overview_cards(p, u, q, s)
    body = (hero(meta) + f'<section class="pro-ov-band"><div class="v2-wrap">{ov}</div></section>'
            + sec_pressure(p) + sec_unwind(u) + sec_quality(q) + sec_stables(s) + sec_sources())
    return page("", "Institutional Indicators | The Crypto Playback", body, datetime.now().year, theme="v2",
                indicator_links=_footer_links(),
                description="Four free institutional-style crypto indicators: pressure index, crowded unwind risk, protocol revenue/TVL quality and stablecoin flows.",
                path=PAGE_FILE, noindex=True)


def write_institutional_page():
    with open(os.path.join(ROOT, PAGE_FILE), "w") as f:
        f.write(render_institutional())
    return PAGE_FILE


if __name__ == "__main__":
    print("wrote", write_institutional_page())
