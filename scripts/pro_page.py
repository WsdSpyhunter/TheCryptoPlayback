"""Renders playback-lab.html (the "Playback Lab" page) in the
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
PAGE_FILE = "playback-lab.html"
# The Revenue / TVL Quality section (DefiLlama-based) is built and styled but taken offline: no clean free source.
# Set True (and re-enable the "quality" job in scripts/pro/refresh_pro.py) to publish it again.
SHOW_QUALITY = False


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

def overview_cards(p, u, q, s, b=None):
    cards = []
    if p:
        z = p["score_z"]
        cards.append(("pressure", "Institutional Positioning", f"{z:+.2f}", p["regime"], _tone(z) if abs(z) >= 1 else "flat",
                      sparkline([h["z"] for h in p["history"]]), p["updated_at"]))
    if b:
        cards.append(("basis", "Basis-Trade Crowding", f"{b['score']:.0f}", f"{b['label']} · {b['phase'].lower()}",
                      "down" if b["score"] >= 55 else "flat", sparkline([x for x in b["history"]["score"][-52:]]), b["updated_at"]))
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


def multi_chart(ts, series, w=760, h=230, fmt="{:+,.0f}", zero=True, label=""):
    """series: [(name, ys, color)] drawn on one time axis, with a legend."""
    allv = [y for _, ys, _ in series for y in ys if y is not None]
    if len(ts) < 2 or not allv:
        return '<p class="pro-empty">Chart builds as history accumulates.</p>'
    pad_l, pad_r, pad_t, pad_b = 56, 14, 30, 26
    lo, hi = min(allv + ([0] if zero else [])), max(allv + ([0] if zero else []))
    span = (hi - lo) or 1
    lo, hi = lo - span * 0.08, hi + span * 0.08
    X = lambda t: pad_l + (t - ts[0]) / (ts[-1] - ts[0]) * (w - pad_l - pad_r)      # noqa: E731
    Y = lambda v: pad_t + (hi - v) / (hi - lo) * (h - pad_t - pad_b)                  # noqa: E731
    out = [f'<svg class="pro-chart" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}" preserveAspectRatio="xMidYMid meet">']
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = Y(v)
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="pro-grid"/>'
                   f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" class="pro-axis">{fmt.format(v)}</text>')
    if zero and lo < 0 < hi:
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" class="pro-zero"/>')
    lx = pad_l
    for name, ys, color in series:
        pts = [(t, y) for t, y in zip(ts, ys) if y is not None]
        if len(pts) >= 2:
            path = "M" + " L".join(f"{X(t):.1f} {Y(y):.1f}" for t, y in pts)
            out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round"/>')
        out.append(f'<rect x="{lx}" y="9" width="12" height="4" fill="{color}"/><text x="{lx + 17}" y="15" class="pro-axis">{escape(name)}</text>')
        lx += 22 + len(name) * 6.3
    for t in (ts[0], ts[len(ts) // 2], ts[-1]):
        d = datetime.fromtimestamp(t, timezone.utc).strftime("%b %-d, %Y")
        anchor = "start" if t == ts[0] else "end" if t == ts[-1] else "middle"
        out.append(f'<text x="{X(t):.1f}" y="{h - 6}" text-anchor="{anchor}" class="pro-axis">{d}</text>')
    out.append("</svg>")
    return "".join(out)


def sec_pressure(p):
    head = ui.title_box("capital_flow", '<span id="pressure-h">Institutional Positioning Index</span>',
                        f"Updated {updated(p['updated_at'])}" if p else "")
    if not p:
        return f'<section class="v2-section" id="pressure">{_wrap(head + _empty("The Institutional Positioning Index"))}</section>'
    z = p["score_z"]
    tone = "up" if z >= 1 else "down" if z <= -1 else "flat"
    comps = ""
    for c in p["components"]:
        z_txt = "n/a" if c["z"] is None else f"{c['z']:+.2f}"
        comps += (f'<div class="pro-comp"><div class="pro-comp-top"><span class="pro-comp-name">{escape(c["label"])}</span>'
                  f'<span class="pro-comp-w">{c["weight"] * 100:.0f}% weight</span></div>'
                  f'<div class="pro-comp-z {_tone(c["z"])}">{z_txt}<small> z</small></div>'
                  f'{zbar(c["z"])}<div class="pro-comp-read">{escape(c["readout"])}</div></div>')
    chart = line_chart([h["t"] for h in p["history"]], [h["z"] for h in p["history"]], zero=True,
                       band=(-1, 1), fmt="{:+.1f}", label="Institutional Positioning Index, z-score, last 30 days")
    cme_html = ""
    cme = p.get("cme")
    if cme:
        rows = ""
        for g in cme["groups"]:
            chg = g["change_net_w"]
            rows += (f'<tr><th scope="row">{g["name"]}</th><td class="pro-num">{g["long"]:,}</td><td class="pro-num">{g["short"]:,}</td>'
                     f'<td class="pro-num {_tone(g["net"])}">{g["net"]:+,}</td><td class="pro-num">{g["net_pct_oi"]:+.1f}%</td>'
                     f'<td class="pro-num {_tone(chg)}">{"n/a" if chg is None else f"{chg:+,}"}</td></tr>')
        hs = cme["history"]
        mc = multi_chart(hs["t"], [("Asset managers", hs["asset_managers_net"], "#8A6A1F"),
                                   ("Leveraged funds", hs["leveraged_funds_net"], "#B3372F"),
                                   ("Dealers", hs["dealers_net"], "#4A5F82")],
                         label="Net positions in CME Bitcoin futures by trader type, last two years")
        cme_html = f"""<div class="pro-cme">
      <div class="pro-chart-title" style="margin-top:30px">What the big players hold: CME Bitcoin futures (CFTC report of {cme['report_date']}, contracts of {cme['contract_size_btc']} BTC)</div>
      <div class="pro-two">
        <div class="pro-table-wrap"><table class="pro-table"><thead><tr><th>Trader type</th><th>Long</th><th>Short</th><th>Net</th><th>Net % of OI</th><th>Net chg w/w</th></tr></thead><tbody>{rows}</tbody></table>
          <p class="pro-note light">Open interest {cme['open_interest_contracts']:,} contracts. Leveraged funds are usually net short because many run the ETF-versus-futures &ldquo;basis trade&rdquo;, so that short is not a bearish bet by itself.</p></div>
        <div class="pro-chart-card"><div class="pro-chart-title">Net positions, last two years (weekly)</div>{mc}</div>
      </div></div>"""
    method = """<details class="pro-method"><summary>How this score is calculated</summary>
      <p>Each component is converted to a trailing z-score (how unusual today's reading is versus its own past, never using future data), clipped to ±3, and blended with the weights shown. The blend is the
      score (z, roughly −2 to +2); the percentile is the normal-curve position of that z (0–100). Regimes: z ≥ +1.0 Bullish Positioning, z ≤ −1.0 Bearish Positioning, otherwise Neutral.</p>
      <ul><li><strong>CME futures positioning (30%):</strong> asset managers' net position in CME Bitcoin futures as a share of open interest, from the CFTC's weekly Traders in Financial Futures report (US government data, 2018 onward),
      z-scored against the trailing two years. A report counts from the Saturday after the Tuesday it describes.</li>
      <li><strong>Spot ETF flows (30%):</strong> US spot Bitcoin ETF daily net flow; half 1-day flow, half rolling 5-day sum.</li>
      <li><strong>On-chain perp funding (20%):</strong> Hyperliquid BTC perpetual funding per 8 hours (positive means longs pay shorts), z-scored over the past 30 days.</li>
      <li><strong>Perp open interest × price (20%):</strong> 24-hour change in Hyperliquid BTC open interest, signed by the 24-hour price direction. Hyperliquid publishes no open-interest history, so this builds from our own hourly snapshots and shows &ldquo;building&rdquo; for the first days.</li></ul>
      <p class="pro-caveat">A descriptive gauge of positioning, not a forecast. When a component is still building, the others are re-weighted. CFTC data is weekly, so that component changes once a week; ETF history in the site dataset is short.
      Coinbase Premium and centralised-exchange funding from the earlier version were removed because there is no clean free source for them. Weights are configurable in scripts/pro/positioning.py.</p></details>"""
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
    {cme_html}
    {method}"""
    return f'<section class="v2-section" id="pressure" aria-labelledby="pressure-h">{_wrap(head + body)}</section>'


def sec_basis(b):
    head = ui.title_box("changed", '<span id="basis-h">Basis-Trade Crowding</span>',
                        f"Updated {updated(b['updated_at'])}" if b else "")
    if not b:
        return f'<section class="v2-section" id="basis">{_wrap(head + _empty("Basis-Trade Crowding"))}</section>'
    c = b["current"]
    tone = "down" if b["score"] >= 55 else "flat"
    comps = ""
    for k in b["components"]:
        pctv = k["percentile"]
        comps += (f'<div class="pro-comp"><div class="pro-comp-top"><span class="pro-comp-name">{escape(k["label"])}</span>'
                  f'<span class="pro-comp-w">{k["weight"] * 100:.0f}% weight</span></div>'
                  f'<div class="pro-comp-z">{"n/a" if pctv is None else pctv}<small> percentile</small></div>'
                  f'<span class="pro-scorebar light" style="width:100%;display:block"><span style="width:{pctv or 0}%;background:{heat(pctv)}"></span></span>'
                  f'<div class="pro-comp-read">{escape(k["readout"])}</div></div>')
    hs = b["history"]
    ts = [int(t) for t in hs["t"]]
    chart = line_chart(ts, hs["lf_net_short_pct_oi"], color="#B3372F", fmt="{:.0f}%", label="Leveraged funds' net short in CME Bitcoin futures as a percent of open interest, last three years")
    hr = c.get("hedge_ratio_pct")
    usd = c.get("lf_net_short_usd")
    kpis = (f'<div class="pro-kpis"><div class="pro-kpi"><span>Hedge-fund net short</span><strong>{c["lf_net_short_btc"]:,.0f} BTC</strong><small>{"about " + money(usd) if usd else "n/a"} at today&#39;s price</small></div>'
            f'<div class="pro-kpi"><span>Share of ETF capital</span><strong>{"n/a" if hr is None else f"{hr:.1f}%"}</strong><small>net short ÷ cumulative ETF net inflows</small></div>'
            f'<div class="pro-kpi"><span>Trade phase</span><strong>{escape(b["phase"])}</strong><small>{c["change_4w_contracts"]:+,} contracts over 4 weeks</small></div>'
            f'<div class="pro-kpi"><span>Asset managers long</span><strong>{c["asset_manager_long_btc"]:,.0f} BTC</strong><small>the other side of the trade</small></div></div>')
    explain = ("<p class=\"pro-lead\">Since spot Bitcoin ETFs launched, many hedge funds have run the &ldquo;basis trade&rdquo;: buy the ETF, short CME Bitcoin futures against it, and collect the gap between the two. "
               "It looks like free money, and that is why it can get crowded: if the gap closes, ETF flows turn or margin tightens, every fund heads for the same exit, forcing ETF selling and futures buying at the same time. "
               "This reading shows how big and how crowded the futures leg is right now, compared with its own last three years.</p>")
    method = """<details class="pro-method"><summary>How this score is calculated</summary>
      <p>Data: the CFTC's weekly Traders in Financial Futures report for CME Bitcoin futures (US government data, published Fridays for the prior Tuesday). The crowding score (0–100) is the weighted average of three percentiles against the trailing 156 weeks:
      <strong>Size 40%</strong> (leveraged funds' net short as a share of open interest), <strong>Absolute size 30%</strong> (their net short in contracts, 5 BTC each) and <strong>Breadth 30%</strong> (how many leveraged-fund traders are short; more funds in the trade is harder to exit).
      Bands: Low under 35, Moderate 35–55, High 55–75, Extreme 75+. Phase compares the net short with four weeks ago (Building above +5%, Unwinding below −5%). The ETF-capital share divides the dollar net short (at the latest Hyperliquid BTC price) by the cumulative net inflows into US spot Bitcoin ETFs from the site's ETF dataset.</p>
      <p class="pro-caveat">Important limits: the CFTC does not label basis trades. A leveraged-fund short is a proxy, since those funds can short for other reasons; ETFs can also be hedged on other venues or not at all; and the data is weekly. This is a gauge of crowding in the regulated futures leg, not a measurement of the whole trade, and not a forecast.</p></details>"""
    body = f"""{_stale(b)}
    {explain}
    <div class="pro-hero-grid">
      <div class="pro-score-card">
        <div class="pro-score-label">Crowding score</div>
        <div class="pro-score-big {tone}">{b['score']:.0f}</div>
        <div class="pro-score-regime {tone}">{escape(b['label'])}</div>
        <div class="pro-score-pct" style="font-size:22px">{escape(b['phase'])}</div>
        <div class="pro-score-label" style="margin-top:8px;font-size:13px">CFTC report of {b['report_date']}</div>
      </div>
      <div class="pro-chart-card"><div class="pro-chart-title">Hedge funds' net short, % of CME Bitcoin futures open interest (3 years, weekly)</div>{chart}</div>
    </div>
    <div class="pro-comps pro-comps-3">{comps}</div>
    {kpis}
    {method}"""
    return f'<section class="v2-section" id="basis" aria-labelledby="basis-h">{_wrap(head + body)}</section>'


def sec_unwind(u):
    head = ui.title_box("liquidations", '<span id="unwind-h">Crowded Unwind Risk Map</span>',
                        f"Updated {updated(u['updated_at'])}" if u else "", dark=True)
    if not u:
        return f'<section class="v2-dark" id="unwind">{_wrap(head + _empty("The Crowded Unwind Risk Map"))}</section>'
    cols = [("premium", "Premium"), ("funding", "Funding"), ("oi", "Open int."), ("adverse", "Adverse")]
    rows = ""
    for a in u["assets"]:
        cells = "".join(
            f'<td class="pro-hm" style="background:{heat(a["components"].get(k))}" title="{lab} percentile: {a["components"].get(k)}">'
            f'{"–" if a["components"].get(k) is None else a["components"][k]}</td>' for k, lab in cols)
        dir_cls = "long" if a["direction"] == "Crowded long" else "short" if a["direction"] == "Crowded short" else "bal"
        fund = a.get("funding_8h")
        prem = a.get("premium_bps")
        rows += (f'<tr><th scope="row"><span class="pro-sym">{a["symbol"]}</span></th>'
                 f'<td><span class="pro-scorebar"><span style="width:{a["score"]:.0f}%;background:{heat(a["score"])}"></span></span>'
                 f'<span class="pro-scoreval">{a["score"]:.0f}</span><span class="pro-lab {a["label"].lower()}">{a["label"]}</span></td>'
                 f'<td><span class="pro-dir {dir_cls}">{a["direction"]}</span></td>{cells}'
                 f'<td class="pro-num">{"n/a" if prem is None else f"{prem:+.1f} bp"}</td>'
                 f'<td class="pro-num">{"n/a" if fund is None else f"{fund * 100:+.4f}%"}</td>'
                 f'<td class="pro-num">{money(a.get("oi_usd"))}</td>'
                 f'<td>{sparkline([h["score"] for h in a["history"]], w=90, h=26)}</td></tr>')
    th = "".join(f"<th>{lab}</th>" for _, lab in cols)
    building = ('<p class="pro-note">Open interest is still building: Hyperliquid publishes no open-interest history, so we record our own snapshots. '
                'Until about two days have accumulated, the score uses the other three components.</p>') if u.get("oi_building") else ""
    method = """<details class="pro-method dark"><summary>How this score is calculated</summary>
      <p>Each coin gets a 0–100 score from four components, each a percentile of that coin's own trailing 30 days (so a coin is compared with itself):
      <strong>Premium 45%</strong> (how far the perpetual trades from its oracle price, a persistent premium or discount means traders are paying up to hold leveraged positions),
      <strong>Funding excess 25%</strong> (funding above or below Hyperliquid's fixed 0.01%-per-8-hours floor, with persistence: raw funding would look falsely elevated because it sits exactly on that floor when the market is balanced),
      <strong>Open interest 15%</strong> (current open interest versus its own range, built from our own snapshots) and <strong>Adverse move 15%</strong> (a 24-hour price move against the crowded side, the stress that forces unwinds).
      Bands: Low under 35, Moderate 35–55, High 55–75, Extreme 75+. Direction is a vote between the sign of the premium and of the funding excess; a Low score is shown as Balanced.</p>
      <p class="pro-caveat">This map describes traders on Hyperliquid, the largest on-chain perpetuals exchange: a big and fast-moving group, but not the whole market. dYdX, the other on-chain venue checked, is 100–500 times smaller and was left out as noise.
      Not modelled because free data does not exist: long/short account ratios, liquidation-price clusters, order-book depth, and centralised-exchange crowding.</p></details>"""
    body = f"""{_stale(u)}
    <p class="pro-lead dark">Which large perpetual-futures markets look most crowded and fragile on-chain? Higher scores mean positioning is more stretched and a leveraged unwind would hit harder.
    Cells show each component's percentile (0–100) against the coin's own last 30 days.</p>
    <div class="pro-table-wrap"><table class="pro-table pro-unwind"><thead><tr><th>Asset</th><th>Risk score</th><th>Direction</th>{th}
      <th>Perp vs index</th><th>Funding/8h</th><th>On-chain OI</th><th>14d</th></tr></thead><tbody>{rows}</tbody></table></div>
    {building}
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
    rate = v.get("net_per_day_7d_usd")
    z_txt = "n/a" if f["z"] is None else f"{f['z']:+.2f}"
    rate_txt = "n/a" if rate is None else signed_money(rate) + " per day (7d avg)"
    kpis = (f'<div class="pro-kpis dark"><div class="pro-kpi"><span>Tracked stablecoin supply</span><strong>{money(t["supply_usd"])}</strong><small>{pct(t["change_7d_pct"], 2)} 7d · {pct(t["change_30d_pct"], 2)} 30d</small></div>'
            f'<div class="pro-kpi"><span>Net issuance, 7 days</span><strong class="{_tone(t["net_issuance_7d_usd"])}">{signed_money(t["net_issuance_7d_usd"])}</strong><small>{signed_money(t["net_issuance_30d_usd"])} over 30 days</small></div>'
            f'<div class="pro-kpi"><span>Flow signal</span><strong>{escape(f["label"])}</strong><small>z {z_txt} vs the last two months</small></div>'
            f'<div class="pro-kpi"><span>Flow velocity</span><strong>{escape(v["label"])}</strong><small>{rate_txt}</small></div></div>')
    h = s["history"]
    ts = [int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) for d in h["d"]]
    ch1 = line_chart(ts, [None if x is None else x / 1e9 for x in h["supply_usd"]], color="#D4B063", fmt="${:.0f}B", label="Tracked stablecoin supply, last 60 days")
    ch2 = line_chart(ts, [None if x is None else x / 1e6 for x in h["net_usd"]], color="#8FD0AC", fmt="{:+.0f}M", zero=True, label="Daily net stablecoin issuance in millions of dollars, last 60 days")
    coins = "".join(
        f'<tr><th scope="row">{c["symbol"]}<span class="pro-pcat">{escape(c["name"])}</span></th><td class="pro-num">{money(c["supply_usd"])}</td><td class="pro-num">{c["share_pct"]:.1f}%</td>'
        f'<td class="pro-num {_tone(c["change_7d_pct"])}">{pct(c["change_7d_pct"], 2)}</td><td class="pro-num {_tone(c["change_30d_pct"])}">{pct(c["change_30d_pct"], 2)}</td>'
        f'<td class="pro-num {_tone(c["net_7d_usd"])}">{signed_money(c["net_7d_usd"])}</td></tr>'
        for c in s["coins"])
    chain_rows = ""
    for c in s["chains"]:
        if c.get("net_7d_usd") is not None:
            tail = (f'<td class="pro-num {_tone(c["net_7d_usd"])}">{signed_money(c["net_7d_usd"])}</td>'
                    f'<td class="pro-num {_tone(c["net_30d_usd"])}">{signed_money(c["net_30d_usd"])}</td>')
        else:
            tail = '<td class="pro-num pro-muted" colspan="2">history building</td>'
        chain_rows += (f'<tr><th scope="row">{c["chain"]}</th><td class="pro-num">{money(c["supply_usd"])}</td>'
                       f'<td class="pro-num">{c["share_pct"]:.1f}%</td>{tail}</tr>')
    movers = ", ".join(f'{m["chain"]} ({signed_money(m["net_7d_usd"])})' for m in s["chain_movers"][:4])
    tt = s.get("tether")
    tether = ""
    if tt:
        track = tt["our_tracked_usdt_usd"] / tt["liabilities_usd"] * 100
        tether = (f'<div class="pro-tether"><div class="pro-chart-title" style="margin-top:26px">Tether reserve cushion (Tether\'s own published figures)</div>'
                  f'<div class="pro-kpis dark"><div class="pro-kpi"><span>Reserves (assets)</span><strong>{money(tt["assets_usd"])}</strong><small>published by Tether</small></div>'
                  f'<div class="pro-kpi"><span>Liabilities (USDT issued)</span><strong>{money(tt["liabilities_usd"])}</strong><small>our chain read covers {track:.1f}% of it</small></div>'
                  f'<div class="pro-kpi"><span>Excess reserves</span><strong>{money(tt["excess_reserves_usd"])}</strong><small>equity above liabilities</small></div>'
                  f'<div class="pro-kpi"><span>Coverage ratio</span><strong>{tt["coverage_ratio"] * 100:.1f}%</strong><small>assets ÷ liabilities</small></div></div></div>')
    method = """<details class="pro-method dark"><summary>How these readings are calculated</summary>
      <p><strong>Source:</strong> supply is read directly from each token's contract on free public blockchain nodes (Ethereum, Base, Arbitrum, Polygon, Optimism, Avalanche, BSC), TronGrid (Tron)
      and Solana's public RPC. History is rebuilt from archive-node reads (EVM chains) and from the Tether treasury's on-chain transfers (Tron); Solana accumulates from the first run.
      <strong>Net issuance:</strong> supply only changes when an issuer mints or burns, so the change in supply is net mint minus burn. For USDT, circulating supply is total supply minus the balance of
      Tether's treasury wallet (Tether mints unissued tokens to itself), which reconciles to Tether's published liabilities. Bridged or Binance-Peg copies are excluded to avoid double counting.
      <strong>Flow velocity:</strong> average daily net issuance over the last 7 days versus the 7 days before. <strong>Flow signal:</strong> z-score of the latest 7-day change versus the last two months of 7-day changes.</p>
      <p class="pro-caveat">Coverage: the nine largest USD stablecoins on the chains listed (USDT counted on Ethereum and Tron, about 97% of Tether's liabilities). Not covered: smaller chains, non-USD stablecoins,
      exchange balances and on-chain transfer volume (no free source). "Velocity" here means the speed of net issuance, not payments velocity.</p></details>"""
    body = f"""{_stale(s)}
    <p class="pro-lead dark">Is dollar liquidity being created or destroyed, how fast, and where? Net issuance read straight from the blockchains, and where new supply is landing.</p>
    {kpis}
    <div class="pro-two"><div class="pro-chart-card dark"><div class="pro-chart-title">Tracked stablecoin supply, daily</div>{ch1}</div>
      <div class="pro-chart-card dark"><div class="pro-chart-title">Daily net issuance</div>{ch2}</div></div>
    <div class="pro-two">
      <div class="pro-table-wrap"><table class="pro-table"><caption>Major stablecoins</caption><thead><tr><th>Coin</th><th>Supply</th><th>Share</th><th>7d</th><th>30d</th><th>7d net</th></tr></thead><tbody>{coins}</tbody></table></div>
      <div class="pro-table-wrap"><table class="pro-table"><caption>Where stablecoins are deployed</caption><thead><tr><th>Chain</th><th>Supply</th><th>Share</th><th>7d net</th><th>30d net</th></tr></thead><tbody>{chain_rows}</tbody></table>
      <p class="pro-note">Biggest 7-day movers: {movers}.</p></div>
    </div>
    {tether}
    {method}"""
    return f'<section class="v2-dark" id="stables" aria-labelledby="stables-h">{_wrap(head + body)}</section>'


def sec_sources():
    head = ui.title_box("book", '<span id="sources-h">Methodology, Data Sources &amp; Limits</span>', "Everything is free public data")
    body = """<p class="pro-lead">Every number on this page is computed from free public data with no paid vendor and no API key. The formulas are
    published beside each indicator and in the open source code (<code>scripts/pro/</code>).</p>
    <div class="pro-sources">
      <div><h3>On-chain perpetuals and futures</h3><p>Hyperliquid's public info endpoint (funding, premium, open interest, prices) and the CFTC's weekly Traders in Financial Futures report for CME Bitcoin futures (US government data).</p></div>
      <div><h3>ETF flows</h3><p>US spot Bitcoin ETF daily net flows from the site's own ETF dataset (SoSoValue, cross-checked against XOOMAR). Farside Investors was not used because it blocks automated access.</p></div>
      <div><h3>Stablecoins</h3><p>Token supply read directly from public blockchain nodes (Ethereum and other EVM chains, Tron via TronGrid, Solana), plus Tether's own published transparency figures.</p></div>
    </div>
    <div class="pro-disclaimer"><strong>Independent market research, not financial advice.</strong> These indicators describe market positioning and data
    reported by third parties; they are not forecasts, and sources can be delayed, revised or wrong. Do not trade on any single number here.</div>"""
    return f'<section class="v2-section v2-section-white" id="sources" aria-labelledby="sources-h">{_wrap(head + body)}</section>'


def _wrap(inner):
    return f'<div class="v2-wrap">{inner}</div>'


def hero(meta):
    return """<section class="pro-hero">
  <div class="v2-wrap">
    <div class="v2-kicker v2-kicker-brass">Playback Lab · transparent methodology</div>
    <h1 class="pro-h1"><span aria-hidden="true" class="pro-brandtitle pro-brandtitle-lg">The
      <img class="pro-brandword" src="assets/v2/the-crypto-playback-word-playback-gold.webp" width="900" height="215" alt=""> Lab</span>
      <span class="v2-sr">The Crypto Playback Lab</span></h1>
    <p>Live readings of crypto market structure: how the big regulated players are positioned, how crowded the ETF basis trade is, which on-chain markets are fragile,
    and where dollar liquidity is flowing. Built only from free public data and fully documented.</p>
    <nav class="pro-jump" aria-label="Playback Lab sections"><a href="#pressure">Positioning Index</a><a href="#basis">Basis Trade</a><a href="#unwind">Unwind Risk</a><a href="#stables">Stablecoin Flows</a><a href="#sources">Methodology</a></nav>
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
    p, u, s, b = _load("pressure"), _load("unwind"), _load("stables"), _load("basis")
    q = _load("quality") if SHOW_QUALITY else None
    meta = _load("meta") or {}
    ov = overview_cards(p, u, q, s, b)
    summary_title = ui.title_box(
        "pulse",
        '<span id="summary-h"><span aria-hidden="true" class="pro-brandtitle">The '
        '<img class="pro-brandword" src="assets/v2/the-crypto-playback-word-playback-gold.webp" width="900" height="215" alt=""> Summary</span>'
        '<span class="v2-sr">The Playback Summary</span></span>',
        "All readings at a glance")
    body = (hero(meta) + f'<section class="pro-ov-band" aria-labelledby="summary-h"><div class="v2-wrap">{summary_title}{ov}</div></section>'
            + sec_pressure(p) + sec_basis(b) + sec_unwind(u) + (sec_quality(q) if SHOW_QUALITY else "") + sec_stables(s) + sec_sources())
    return page("", "The Crypto Playback Lab | Crypto Market Indicators", body, datetime.now().year, theme="v2",
                indicator_links=_footer_links(),
                description="The Crypto Playback Lab: live crypto market-structure indicators updated every 2 hours. Institutional positioning, ETF basis-trade crowding, on-chain crowded unwind risk and stablecoin flows.",
                path=PAGE_FILE,
                extra_head='<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700&display=swap" rel="stylesheet">')


def write_institutional_page():
    with open(os.path.join(ROOT, PAGE_FILE), "w") as f:
        f.write(render_institutional())
    return PAGE_FILE


if __name__ == "__main__":
    print("wrote", write_institutional_page())
