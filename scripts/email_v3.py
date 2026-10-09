"""The Crypto Playback newsletter, Version 3: an email-safe build of the owner's locked design
(docs/newsletter-v3-design/index.html is the source of truth; see its README for tokens and components).

Everything here is markup only. Numbers come from the same live data the website uses
(build_site._live_context), the issue's own stories, and the Lab's Playback Read.

Email-safe on purpose: nested tables and inline CSS, PNG icons/gauge/arrow (no inline SVG), no flexbox,
grid, position or clip-path. A small media query stacks the grids on phones.

Order (the owner asked to try indicators at the bottom): top bar, header, Top 6 strip, The Bottom Line,
Market Snapshot, Notable, Signal Confluence + What Changed, The Playback Read, Top News Stories,
Alerts & Indicators, CTA, footer.  `indicators_last=False` puts Alerts & Indicators back before the news.
"""
import json
import os
import re
from html import escape

import v2_ui as ui

SITE_URL = "https://cryptoplayback.com/"
ASSET_BASE = "https://cryptoplayback.com/assets"

NAVY, NAVY_TOP, NAVY_CARD, NAVY_LEDE, NAVY_LINE = "#0B1F3A", "#07162B", "#12294A", "#16305A", "#2C4263"
BRASS, BRASS_HI, BRASS_TX = "#B8934A", "#D4B063", "#8A6A1F"
IVORY, PAGE, LINE, CARD_LINE = "#F7F4EC", "#E9E4D6", "#E2DDD0", "#D9D3C3"
TEXT, MUTED = "#1F2937", "#5B6472"
POS_BG, POS_TX, POS_HI = "#1E7A4C", "#145C39", "#8FD0AC"
NEG_BG, NEG_HI, NEG_CARD = "#B3372F", "#F2A29B", "#2B1C2A"
NEU_BG = "#4A5F82"
DK_MUTED, DK_SOFT, DK_TEXT = "#9FB0C8", "#C9D2E0", "#E4E9F1"

SANS = "'IBM Plex Sans',Helvetica,Arial,sans-serif"
FRANK = "'Libre Franklin','Helvetica Neue',Helvetica,Arial,sans-serif"
MONO = "'IBM Plex Mono',Menlo,Consolas,'Courier New',monospace"
COND = "'Barlow Condensed','Arial Narrow',Arial,sans-serif"


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_playback_read():
    """The Lab's Playback Read (data/pro/read.json), or None if it is missing or not current."""
    try:
        r = json.load(open(os.path.join(ROOT, "data", "pro", "read.json")))
    except (OSError, ValueError):
        return None
    return r if r.get("status") == "ok" and r.get("counts") else None


# ------------------------------------------------------------------ small pieces

def _plain(s):
    t = re.sub(r"<[^>]+>", "", s or "")
    for a, b in (("&amp;", "&"), ("&ndash;", "-"), ("&mdash;", "-"), ("&rarr;", "→"), ("&rsquo;", "'"), ("&middot;", "·"), ("&nbsp;", " ")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def icon(key, tone, size, base):
    return (f'<img src="{base}/email-v3/icon-{key}-{tone}.png" width="{size}" height="{size}" alt="" '
            f'style="display:block;width:{size}px;height:{size}px;border:0;">')


def money(v):
    """'$-244.1M' -> '-$244.1M'"""
    return v.replace("$-", "-$").replace("$+", "+$")


def pill(kind):
    bg, label = {"pos": (POS_BG, "Positive"), "neg": (NEG_BG, "Negative"), "neu": (NEU_BG, "Neutral")}[kind]
    return (f'<span style="display:inline-block;font-family:{SANS};font-size:10.5px;font-weight:600;letter-spacing:0.04em;'
            f'background:{bg};color:#FFFFFF;padding:2px 8px;">{label}</span>')


def _kind(positive):
    return "pos" if positive is True else ("neg" if positive is False else "neu")


def section_title(key, title, base, meta="", pad_bottom=20):
    """White shadow box with icon + title sitting on a 2px navy rule (light sections)."""
    meta_cell = (f'<td align="right" valign="bottom" style="padding:0 0 12px 12px;font-family:{SANS};font-size:12px;color:{MUTED};">{meta}</td>'
                 if meta else "")
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="border-bottom:2px solid {NAVY};margin:0 0 {pad_bottom}px 0;"><tr>'
            f'<td valign="bottom" style="padding:0 0 10px 0;">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
            f'style="background:#FFFFFF;border:1px solid {LINE};box-shadow:0 4px 14px rgba(11,31,58,0.16);"><tr>'
            f'<td style="padding:10px 0 10px 18px;" valign="middle">{icon(key, "ink", 22, base)}</td>'
            f'<td style="padding:10px 18px 10px 10px;font-family:{SANS};font-weight:600;font-size:14px;letter-spacing:0.14em;'
            f'text-transform:uppercase;color:{NAVY};white-space:nowrap;" valign="middle">{title}</td>'
            f'</tr></table></td>{meta_cell}</tr></table>')


def dark_title(key, title, base, meta="", margin="0 0 18px 0"):
    meta_cell = (f'<td align="right" valign="middle" style="padding:0 0 10px 12px;font-family:{SANS};font-size:12px;color:{DK_MUTED};">{meta}</td>'
                 if meta else "")
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="border-bottom:1px solid {NAVY_LINE};margin:{margin};"><tr>'
            f'<td width="32" valign="middle" style="padding:0 10px 10px 0;">{icon(key, "gold", 22, base)}</td>'
            f'<td valign="middle" style="padding:0 0 10px 0;font-family:{SANS};font-weight:600;font-size:12px;letter-spacing:0.14em;'
            f'text-transform:uppercase;color:{IVORY};">{title}</td>{meta_cell}</tr></table>')


def story_tile(icon_key, base):
    return (f'<table role="presentation" width="64" cellpadding="0" cellspacing="0" border="0" class="v3-tile">'
            f'<tr><td width="64" height="64" align="center" valign="middle" style="width:64px;height:64px;background:{NAVY};'
            f'border-bottom:3px solid {BRASS};">{icon(icon_key, "gold", 36, base).replace("display:block;", "display:block;margin:0 auto;")}</td></tr></table>')


# ------------------------------------------------------------------ content helpers

_CATEGORIES = [
    (r"\b(etfs?|inflows?|outflows?)\b", "Flows", "etf_flow"),
    (r"\b(hack(ed|er|ers)?|exploit(s|ed|er)?|stolen|breach|drained|attack(s|ed)?|security|phishing)\b", "Security", "lock"),
    (r"\b(stablecoins?|usdc|usdt|tether|circle)\b", "Stablecoins", "stablecoin_liquidity"),
    (r"\b(treasury|treasuries|strategy|saylor|microstrategy|holdings)\b", "Corporate Treasuries", "stack"),
    (r"\b(sec|cftc|occ|congress|senate|bill|regulators?|regulation|lawsuit|sued|court|policy|tax|fed|esma|mica)\b", "Policy", "structure"),
    (r"\b(exchange|okx|coinbase|binance|ice|nasdaq|tokeni[sz]ed|listing|custody|launch(es|ed)?)\b", "Market Infrastructure", "clock"),
    (r"\b(miners?|hashrate|mining)\b", "Network", "network_health"),
]


def categorize(headline, body=""):
    """(label, icon) for a story from its words (headline first). A placeholder until the writer supplies a category per story."""
    for text in (headline.lower(), f"{headline} {body}".lower()):
        for pat, label, ic in _CATEGORIES:
            if re.search(pat, text):
                return label, ic
    return "News", "news"


def bottom_line(live, intro):
    """Three numbered bullets built from the same data as the rest of the email (no new writing needed)."""
    items = live["confluence_items"]
    pos, total = live["positive_count"], live["total_count"]
    fng = live["fng"]
    negs = [_plain(n) for n, p, _ in items if not p]
    if not negs:
        tail = "Every scored signal is positive."
    elif len(negs) == 1:
        tail = f"{negs[0]} is the lone negative."
    elif len(negs) <= 3:
        tail = f"{' and '.join([', '.join(negs[:-1]), negs[-1]] if len(negs) > 2 else negs)} are negative."
    else:
        tail = f"{len(negs)} are negative."
    b1 = f"<strong style=\"color:{NAVY};\">Signals:</strong> {pos} of {total} scored indicators are positive and sentiment reads {escape(str(fng['classification']))} ({fng['value']}). {tail}"
    etf = live.get("etf")
    stable = live["dashboard"].get("stablecoins") or {}
    flow = ""
    if etf and etf.get("history"):
        d, f = etf["history"][0]
        flow = f"Spot Bitcoin ETFs recorded {'inflows' if f >= 0 else 'outflows'} of ${abs(float(f)) / 1e6:,.1f}M on the latest trading day"
    if stable.get("change_7d_pct") is not None:
        s7 = stable["change_7d_pct"]
        sc = f"stablecoin supply is {'up' if s7 >= 0 else 'down'} {abs(s7):.1f}% over 7 days"
        flow = f"{flow}, and {sc}." if flow else sc[0].upper() + sc[1:] + "."
    elif flow:
        flow += "."
    b2 = f"<strong style=\"color:{NAVY};\">Flows:</strong> {flow or 'Flow data is still updating.'}"
    b3 = f"<strong style=\"color:{NAVY};\">Top story:</strong> {_plain(intro)}"
    rows = ""
    for i, txt in enumerate((b1, b2, b3), 1):
        rows += (f'<tr><td width="46" valign="top" style="width:46px;padding:0 0 18px 0;font-family:{FRANK};font-weight:700;font-size:30px;'
                 f'line-height:1;color:{BRASS};">0{i}</td>'
                 f'<td valign="top" style="padding:0 0 18px 0;font-family:{SANS};font-size:15.5px;line-height:1.6;color:{TEXT};">{txt}</td></tr>')
    return rows


# ------------------------------------------------------------------ sections

def top_bar(kicker, issue_no, view_url):
    return (f'<tr><td style="background:{NAVY_TOP};padding:12px 40px;" class="v3-pad">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td style="font-family:{COND};font-weight:500;font-size:14px;letter-spacing:0.14em;text-transform:uppercase;color:{DK_SOFT};">{kicker} &middot; No. {issue_no}</td>'
            f'<td align="right" style="font-family:{COND};font-weight:500;font-size:14px;letter-spacing:0.14em;text-transform:uppercase;">'
            f'<a href="{view_url}" style="color:{BRASS_HI} !important;text-decoration:none;"><span style="color:{BRASS_HI} !important;">View in browser</span></a></td>'
            f'</tr></table></td></tr>')


def header_row(header_url, alt):
    return (f'<tr><td style="background:{NAVY};border-bottom:4px solid {BRASS};line-height:0;font-size:0;">'
            f'<a href="{SITE_URL}" style="display:block;text-decoration:none;"><img src="{header_url}" alt="{escape(alt, quote=True)}" width="670" '
            f'style="display:block;width:100%;max-width:670px;height:auto;border:0;"></a></td></tr>')


def price_strip(prices, caption):
    def cell(c):
        ch = c["change_24h"]
        if abs(ch) < 0.05:
            arrow, color = "&#9644;", MUTED
        elif ch > 0:
            arrow, color = "&#9650;", POS_BG
        else:
            arrow, color = "&#9660;", NEG_BG
        price = f"${c['price']:,.2f}"
        return (f'<td width="33%" align="center" valign="top" style="width:33%;padding:0 4px 14px;">'
                f'<div style="font-family:{MONO};font-size:14px;color:{MUTED};">{c["symbol"]}</div>'
                f'<div class="v3-price" style="font-family:{MONO};font-size:17px;color:{NAVY};">{price}</div>'
                f'<div style="font-family:{MONO};font-size:12px;color:{color};">{arrow} {abs(ch):.1f}%</div></td>')
    rows = ""
    for i in (0, 3):
        rows += "<tr>" + "".join(cell(c) for c in prices[i:i + 3]) + "</tr>"
    return (f'<tr><td style="background:{IVORY};padding:20px 40px 6px;border-bottom:1px solid {LINE};" class="v3-pad">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>'
            f'<div style="text-align:center;font-family:{SANS};font-size:12px;color:{MUTED};padding:0 0 14px;">{caption}</div></td></tr>')


def bottom_line_section(live, intro, base):
    return (f'<tr><td style="padding:36px 40px;" class="v3-pad">{section_title("bottom_line", "The Bottom Line", base)}'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{bottom_line(live, intro)}</table></td></tr>')


def snapshot_section(live, gauge_url, base):
    fng = live["fng"]
    cls = str(fng["classification"])
    v = fng["value"]
    tone = POS_TX if v >= 55 else (NEG_BG if v <= 45 else MUTED)
    return (f'<tr><td style="padding:34px 40px 36px;" class="v3-pad">'
            f'{section_title("snapshot", "Market Snapshot", base, f"Updated {live["date_abbrev"]} &middot; {live["total_count"]} indicators", 18)}'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{IVORY};border:1px solid {LINE};"><tr>'
            f'<td class="v3-stack" width="210" align="center" valign="middle" style="width:210px;padding:22px 10px 22px 26px;">'
            f'<img src="{gauge_url}" width="200" height="122" alt="Sentiment gauge showing {v}, {escape(cls)}" style="display:block;width:200px;height:auto;margin:0 auto;border:0;">'
            f'<div style="font-family:{FRANK};font-weight:700;font-size:32px;line-height:1;color:{NAVY};">{v}</div>'
            f'<div style="font-family:{COND};font-size:15px;letter-spacing:0.16em;text-transform:uppercase;color:{tone};font-weight:600;margin-top:4px;">{escape(cls)}</div></td>'
            f'<td class="v3-stack" valign="middle" style="padding:22px 26px 22px 18px;font-family:{SANS};font-size:15px;line-height:1.65;color:{TEXT};">{live["snapshot_text"]}</td>'
            f'</tr></table></td></tr>')


def notable_section(missed, base):
    if not missed:
        return ""
    body = re.sub(r"</p>\s*<p[^>]*>", "<br><br>", missed["body"])
    body = re.sub(r"</?p[^>]*>", "", body).strip()
    badge = (f'<table role="presentation" align="right" cellpadding="0" cellspacing="0" border="0"><tr>'
             f'<td valign="bottom" style="padding-right:4px;"><img src="{base}/email-v3/arrow-notable.png" width="40" height="36" alt="" style="display:block;width:40px;height:36px;border:0;"></td>'
             f'<td style="background:{NAVY};border-bottom:3px solid {BRASS};padding:7px 14px;font-family:{SANS};font-weight:600;font-size:12px;'
             f'letter-spacing:0.14em;text-transform:uppercase;color:{BRASS_HI};white-space:nowrap;">A story you may have missed</td></tr></table>')
    return (f'<tr><td style="background:{IVORY};padding:32px 40px 30px;border-top:1px solid {LINE};border-bottom:1px solid {LINE};" class="v3-pad">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:2px solid {NAVY};margin:0 0 20px;"><tr>'
            f'<td valign="bottom" style="padding:0 0 10px;">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="background:#FFFFFF;border:1px solid {LINE};box-shadow:0 4px 14px rgba(11,31,58,0.16);"><tr>'
            f'<td style="padding:10px 0 10px 18px;">{icon("notable", "ink", 22, base)}</td>'
            f'<td style="padding:10px 18px 10px 10px;font-family:{SANS};font-weight:600;font-size:14px;letter-spacing:0.14em;text-transform:uppercase;color:{NAVY};">Notable</td>'
            f'</tr></table></td><td align="right" valign="bottom" style="padding:0 0 12px 12px;">{badge}</td></tr></table>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td width="82" valign="top" class="v3-tilecell" style="width:82px;padding-right:18px;">{story_tile("notable", base)}</td>'
            f'<td valign="top"><div style="font-family:{COND};font-weight:600;font-size:14px;letter-spacing:0.14em;text-transform:uppercase;color:{BRASS_TX};margin-bottom:6px;">Notable &middot; {escape(missed["source_title"])}</div>'
            f'<div style="font-family:{FRANK};font-weight:700;font-size:19px;line-height:1.3;color:{NAVY};margin-bottom:8px;">{missed["headline"]}</div>'
            f'<div style="font-family:{SANS};font-size:14.5px;line-height:1.6;color:{TEXT};margin-bottom:10px;">{body}</div>'
            f'<a href="{missed["source_url"]}" style="font-family:{SANS};font-size:13px;font-weight:600;color:{BRASS_TX} !important;text-decoration:none;"><span style="color:{BRASS_TX} !important;">Read at {escape(missed["source_title"])} &rarr;</span></a>'
            f'</td></tr></table></td></tr>')


def confluence_card(name, positive, value_html, detail, kind_override=None):
    kind = _kind(positive)
    neg = kind == "neg"
    border, bg = (NEG_BG, NEG_CARD) if neg else (NAVY_LINE, NAVY_CARD)
    name_c = DK_SOFT if neg else DK_MUTED
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{bg};border:1px solid {border};"><tr>'
            f'<td style="padding:12px;" valign="top">'
            f'<div style="font-family:{SANS};font-size:10.5px;letter-spacing:0.06em;text-transform:uppercase;color:{name_c};">{name}</div>'
            f'<div style="font-family:{MONO};font-size:16px;color:{IVORY};margin-top:4px;">{value_html}</div>'
            f'<div style="font-family:{SANS};font-size:12px;color:{name_c};margin-top:2px;line-height:1.4;">{detail or "&nbsp;"}</div>'
            f'<div style="margin-top:8px;">{pill(kind)}</div></td></tr></table>')


def dashboard_panel(live, base):
    items = live["confluence_items"]
    pos, total = live["positive_count"], live["total_count"]
    unscored = [i for i in live["indicators"] if i.get("confluence_positive") is None]
    note = ""
    if unscored:
        names = ", ".join(_plain(ui.strip_emoji(i["card_label"])) for i in unscored)
        note = f"{len(unscored)} informational readings are shown below but not scored: {names}. "
    # grid: 4 across, the last odd ETF row full-width like the design
    cells = []
    etf_row = None
    for name, p, val in items:
        value, detail = ui.split_value(val)
        value = money(value)
        if "ETF" in name and etf_row is None and len(items) % 4 == 1:
            etf_row = (name, p, value, detail)
            continue
        cells.append(f'<td class="v3-cc" width="25%" valign="top" style="width:25%;padding:4px;">{confluence_card(name, p, value, detail)}</td>')
    rows = ""
    for i in range(0, len(cells), 4):
        chunk = cells[i:i + 4]
        rows += '<tr class="v3-ccrow">' + "".join(chunk) + "<td></td>" * (4 - len(chunk)) + "</tr>"
    if etf_row:
        name, p, value, detail = etf_row
        kind = _kind(p)
        rows += (f'<tr><td colspan="4" style="padding:4px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
                 f'style="background:{NAVY_CARD};border:1px solid {NAVY_LINE};"><tr><td style="padding:12px;" valign="middle">'
                 f'<div style="font-family:{SANS};font-size:10.5px;letter-spacing:0.06em;text-transform:uppercase;color:{DK_MUTED};">{name}</div>'
                 f'<div style="font-family:{SANS};font-size:12px;color:{DK_MUTED};margin-top:4px;">{detail}</div></td>'
                 f'<td align="center" valign="middle" style="font-family:{MONO};font-size:16px;color:{IVORY};">{value}</td>'
                 f'<td align="right" valign="middle" style="padding:12px;">{pill(kind)}</td></tr></table></td></tr>')
    # What Changed (genuine moves only)
    real = live.get("real_change_items") or []
    if real:
        ch = ""
        for dot, headline, detail in real:
            col = POS_HI if "128994" in dot else (NEG_HI if "128308" in dot else IVORY)
            ch += (f'<tr><td style="padding:14px 0;border-bottom:1px solid {NAVY_LINE};font-family:{SANS};font-size:15px;color:{DK_TEXT};">{headline}</td>'
                   f'<td align="right" style="padding:14px 0;border-bottom:1px solid {NAVY_LINE};font-family:{MONO};font-size:14px;color:{col};">{detail}</td></tr>')
    else:
        ch = (f'<tr><td style="padding:14px 0;border-bottom:1px solid {NAVY_LINE};font-family:{SANS};font-size:15px;color:{DK_TEXT};">'
              f'No indicator has moved enough to flag since yesterday.</td></tr>')
    return (f'<tr><td style="background:{NAVY};padding:38px 40px 34px;color:{IVORY};" class="v3-pad">'
            f'{dark_title("confluence", "Signal Confluence", base, f"Updated {live["date_abbrev"]}")}'
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 16px;"><tr>'
            f'<td valign="bottom" style="font-family:{FRANK};font-weight:700;font-size:56px;line-height:1;color:{IVORY};">{pos}<span style="font-size:30px;color:{DK_MUTED};font-weight:600;">/{total}</span></td>'
            f'<td valign="bottom" style="padding:0 0 6px 14px;font-family:{SANS};font-size:14px;line-height:1.5;color:{DK_TEXT};">signals positive. {live["interpretation"]}</td></tr></table>'
            f'<div style="margin:0 -4px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table></div>'
            f'<div style="margin-top:12px;font-family:{SANS};font-size:12px;line-height:1.5;color:{DK_MUTED};">{note}Capital Flow Score is a Crypto Playback composite of price and sector breadth weighted against sentiment. '
            f'It is not institutional transaction data. <a href="{SITE_URL}" style="color:{BRASS_HI} !important;"><span style="color:{BRASS_HI} !important;">Full methodology</span></a></div>'
            f'{dark_title("changed", "What Changed", base, "vs. ~24 hours ago", "34px 0 6px 0")}'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{ch}</table>'
            f'<div style="padding-top:12px;font-family:{SANS};font-size:13px;line-height:1.5;color:{DK_MUTED};">Each indicator is compared with its own reading from about 24 hours earlier. ETF flow compares to the prior trading day.</div>'
            f'</td></tr>')


def read_section(read, tag, base):
    if not read:
        return ""
    title = "This Week's Playback Read" if tag == "Weekly" else "Today's Playback Read"
    c = read["counts"]

    def tile(label, n, color):
        return (f'<td width="33%" align="center" style="width:33%;padding:0 5px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
                f'style="background:{NAVY};border-bottom:3px solid {BRASS};"><tr><td align="center" style="padding:14px 6px 12px;">'
                f'<div style="font-family:{FRANK};font-weight:700;font-size:40px;line-height:1.1;color:{color};">{n}</div>'
                f'<div style="font-family:{SANS};font-weight:600;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:{IVORY};">{label}</div></td></tr></table></td>')
    return (f'<tr><td style="background:{IVORY};padding:34px 40px 36px;border-top:1px solid {LINE};border-bottom:1px solid {LINE};" class="v3-pad">'
            f'{section_title("pulse", title, base, f"From the Playback Lab &middot; {read["total"]} readings", 18)}'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'{tile("Supportive", c["Supportive"], POS_HI)}{tile("Neutral", c["Neutral"], "#D5CFBF")}{tile("Caution", c["Caution"], NEG_HI)}</tr></table>'
            f'<div style="font-family:{SANS};font-size:15.5px;line-height:1.6;color:{TEXT};margin:18px 0 18px;">{read["summary"]}</div>'
            f'<a href="{SITE_URL}playback-lab.html" style="display:inline-block;background:{NAVY};border-bottom:3px solid {BRASS};padding:13px 26px;'
            f'font-family:{COND};font-size:16px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:{BRASS_HI} !important;text-decoration:none;">'
            f'<span style="color:{BRASS_HI} !important;">View in the Playback Lab &rarr;</span></a></td></tr>')


def story_row(headline, body, source_title, source_url, base, first=False):
    label, ic = categorize(_plain(headline), _plain(body))
    paras = re.findall(r"<p[^>]*>(.*?)</p>", body, re.S) or [body]
    summary = paras[0].strip()
    why = " ".join(p.strip() for p in paras[1:]).strip()
    why_html = (f'<div style="font-family:{SANS};font-size:14.5px;line-height:1.6;color:{TEXT};margin-bottom:10px;">'
                f'<strong style="color:{NAVY};">Why it matters:</strong> {why}</div>') if why else ""
    return (f'<tr><td style="padding:22px 0;border-top:1px solid {LINE};">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td width="82" valign="top" class="v3-tilecell" style="width:82px;padding-right:18px;">{story_tile(ic, base)}</td>'
            f'<td valign="top"><div style="font-family:{COND};font-weight:600;font-size:14px;letter-spacing:0.14em;text-transform:uppercase;color:{BRASS_TX};margin-bottom:6px;">{label} &middot; {escape(source_title)}</div>'
            f'<div style="font-family:{FRANK};font-weight:700;font-size:19px;line-height:1.3;letter-spacing:-0.01em;color:{NAVY};margin-bottom:8px;">{headline}</div>'
            f'<div style="font-family:{SANS};font-size:14.5px;line-height:1.6;color:{TEXT};margin-bottom:8px;">{summary}</div>{why_html}'
            f'<a href="{source_url}" style="font-family:{SANS};font-size:13px;font-weight:600;color:{BRASS_TX} !important;text-decoration:none;"><span style="color:{BRASS_TX} !important;">Read at {escape(source_title)} &rarr;</span></a>'
            f'</td></tr></table></td></tr>')


def news_section(intro, stories, base):
    rows = "".join(story_row(s["headline"], s["body"], s["source_title"], s["source_url"], base) for s in stories)
    return (f'<tr><td style="padding:38px 40px 12px;" class="v3-pad">{section_title("news", "The Top News Stories", base)}'
            f'<div style="font-family:{FRANK};font-weight:600;font-size:22px;line-height:1.45;color:{IVORY};background:{NAVY_LEDE};padding:22px 26px;margin:0 0 22px;'
            f'box-shadow:0 6px 18px rgba(11,31,58,0.28);">{_plain(intro)}</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table></td></tr>')


def indicators_section(live, base):
    cards = []
    for ind in live["indicators"]:
        value, detail = ui.split_value(ind["confluence_display"])
        value = money(value)
        kind = _kind(ind.get("confluence_positive"))
        link = SITE_URL + ind["page"]
        cards.append(
            f'<td class="v3-ac" width="50%" valign="top" style="width:50%;padding:5px;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{NAVY_CARD};border:1px solid {NAVY_LINE};"><tr><td style="padding:16px;" valign="top">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td width="26" valign="middle">{icon(ind["id"], "gold", 18, base)}</td>'
            f'<td valign="middle" style="font-family:{FRANK};font-weight:700;font-size:14px;letter-spacing:0.04em;text-transform:uppercase;color:{IVORY};">{ui.strip_emoji(ind["card_label"])}</td></tr></table>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;"><tr>'
            f'<td style="font-family:{MONO};font-size:20px;color:{IVORY};">{value}</td><td align="right">{pill(kind)}</td></tr></table>'
            f'<div style="font-family:{SANS};font-size:13px;color:{DK_TEXT};margin-top:8px;">{detail or "&nbsp;"}</div>'
            f'<div style="font-family:{SANS};font-size:12.5px;line-height:1.5;color:{DK_MUTED};margin-top:8px;">{ind["explainer_text"]}</div>'
            f'<div style="margin-top:10px;"><a href="{link}" style="font-family:{SANS};font-size:12px;font-weight:600;color:{BRASS_HI} !important;text-decoration:none;">'
            f'<span style="color:{BRASS_HI} !important;">View full breakdown &rarr;</span></a></div></td></tr></table></td>')
    rows = ""
    for i in range(0, len(cards), 2):
        pair = cards[i:i + 2]
        rows += '<tr class="v3-acrow">' + "".join(pair) + ("<td></td>" if len(pair) < 2 else "") + "</tr>"
    return (f'<tr><td style="background:{IVORY};padding:34px 40px 26px;border-top:4px solid {BRASS};border-bottom:1px solid {LINE};" class="v3-pad">'
            f'{section_title("alerts", "Alerts &amp; Indicators", base, f"Updated {live["date_abbrev"]}", 14)}'
            f'<div style="font-family:{SANS};font-size:14.5px;line-height:1.6;color:{TEXT};">Each card links to its full methodology and history on the site.</div></td></tr>'
            f'<tr><td style="background:{NAVY};padding:28px 40px 34px;" class="v3-pad"><div style="margin:0 -5px;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table></div></td></tr>')


def cta_section():
    return (f'<tr><td align="center" style="padding:34px 40px 38px;" class="v3-pad">'
            f'<div style="font-family:{FRANK};font-weight:700;font-size:22px;color:{NAVY};margin-bottom:14px;">Explore the full indicator dashboard</div>'
            f'<a href="{SITE_URL}" style="display:inline-block;background:{NAVY};border-bottom:3px solid {BRASS};padding:14px 32px;font-family:{COND};font-size:16px;'
            f'font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:{IVORY} !important;text-decoration:none;"><span style="color:{IVORY} !important;">View on cryptoplayback.com</span></a>'
            f'<div style="margin-top:16px;font-family:{SANS};font-size:13.5px;color:{MUTED};">Forwarded this issue? '
            f'<a href="{SITE_URL}#subscribe" style="font-weight:600;color:{BRASS_TX} !important;"><span style="color:{BRASS_TX} !important;">Subscribe free</span></a></div></td></tr>')


def footer_section(live, prices_stamp, base, year):
    sources = (f'<strong style="color:{IVORY};">Sources and timestamps.</strong> Prices: CoinGecko, as of {prices_stamp}. '
               f'Indicators: Crypto Playback composite methodology, updated {live["date_abbrev"]}. News: as linked in each story.')
    disclaimer = (f'<strong style="color:{IVORY};">THE CRYPTO PLAYBACK IS NOT FINANCIAL ADVICE.</strong> The material in this newsletter has no regard to any specific investment objectives, '
                  'financial situation, or particular needs of any reader. It is published solely for informational purposes and is not to be construed as a solicitation, nor does it '
                  'constitute advice, investment or otherwise. References to third parties are based on information obtained from sources believed to be reliable but not guaranteed as '
                  'being accurate. Readers should not regard it as a substitute for the exercise of their own judgment. Our comments are an expression of opinion. While we believe our '
                  'statements to be true, they always depend on the reliability of our own credible sources. We recommend that you consult with a licensed, qualified investment advisor '
                  'before making any investment decisions.')
    unsub = "{{ unsubscribe_url }}"
    return (f'<tr><td style="background:{NAVY};border-top:4px solid {BRASS};padding:30px 40px 26px;" class="v3-pad">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;"><tr>'
            f'<td valign="middle"><a href="{SITE_URL}" style="text-decoration:none;"><img src="{base}/email-v3-footer-badge.png" width="52" height="52" alt="" style="display:block;width:52px;height:52px;border:0;"></a></td>'
            f'<td valign="middle" style="padding-left:12px;"><a href="{SITE_URL}" style="text-decoration:none;"><img src="{base}/email-v3-footer-logo.png" width="190" height="20" alt="The Crypto Playback" style="display:block;width:190px;height:auto;border:0;"></a></td></tr></table>'
            f'<div style="font-family:{SANS};font-size:13.5px;line-height:1.65;color:{DK_SOFT};padding-bottom:16px;border-bottom:1px solid {NAVY_LINE};">{sources}</div>'
            f'<div style="font-family:{SANS};font-size:12.5px;line-height:1.65;color:{DK_SOFT};padding-top:16px;">{disclaimer}</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:18px;"><tr>'
            f'<td style="font-family:{SANS};font-size:12.5px;color:{DK_SOFT};">&copy; {year} The Crypto Playback &middot; <span style="white-space:nowrap;">info&#8203;@cryptoplayback.com</span></td>'
            f'<td align="right" style="font-family:{SANS};font-size:12.5px;"><a href="{unsub}" style="color:{BRASS_HI} !important;"><span style="color:{BRASS_HI} !important;">Unsubscribe</span></a></td>'
            f'</tr></table></td></tr>')


def compact(html):
    """Moves every inline style that repeats 3+ times into a shared class in the <style> block. Same look, far fewer bytes
    (Gmail cuts off messages over ~102 KB)."""
    from collections import Counter
    tag_re = re.compile(r"<(?!/|!)([a-zA-Z0-9]+)((?:\s[^<>]*?)?)(/?)>")
    style_re = re.compile(r"\sstyle=\"([^\"]*)\"")
    counts = Counter(m.group(1) for t in tag_re.finditer(html) for m in [style_re.search(t.group(2))] if m and len(m.group(1)) >= 40)
    names = {st: f"c{i}" for i, (st, n) in enumerate(counts.most_common()) if n >= 3}
    if not names:
        return html, ""

    def swap(m):
        attrs = m.group(2)
        sm = style_re.search(attrs)
        if not sm or sm.group(1) not in names:
            return m.group(0)
        cls = names[sm.group(1)]
        attrs = style_re.sub("", attrs, count=1)
        cm = re.search(r"\sclass=\"([^\"]*)\"", attrs)
        if cm:
            attrs = attrs.replace(cm.group(0), f' class="{cm.group(1)} {cls}"')
        else:
            attrs += f' class="{cls}"'
        return f"<{m.group(1)}{attrs}{m.group(3)}>"
    out = tag_re.sub(swap, html)
    css = "".join(f".{c}{{{st}}}" for st, c in names.items())
    return out, css


# ------------------------------------------------------------------ the email

CSS = f"""
a[x-apple-data-detectors] {{ color:inherit !important; text-decoration:none !important; font-size:inherit !important; font-family:inherit !important; font-weight:inherit !important; line-height:inherit !important; }}
@media only screen and (max-width: 620px) {{
  .v3-wrap {{ width:100% !important; }}
  .v3-pad {{ padding-left:18px !important; padding-right:18px !important; }}
  .v3-price {{ font-size:15px !important; }}
  .v3-stack {{ display:block !important; width:100% !important; box-sizing:border-box !important; text-align:center !important; padding:14px 18px !important; }}
  .v3-ccrow {{ display:block !important; }}
  .v3-cc {{ display:inline-block !important; width:50% !important; box-sizing:border-box !important; }}
  .v3-acrow {{ display:block !important; }}
  .v3-ac {{ display:block !important; width:100% !important; box-sizing:border-box !important; padding:5px 0 !important; }}
  .v3-tilecell {{ width:56px !important; padding-right:12px !important; }}
  .v3-tile, .v3-tile td {{ width:52px !important; height:52px !important; }}
}}
"""


def render(*, issue_title, intro, stories, ticker_prices, tag, date_display, date_abbrev, issue_number, live,
           missed_story=None, read=None, header_url, gauge_url, slug, year, base=ASSET_BASE, indicators_last=True):
    weekly = tag == "Weekly"
    kicker = "Weekly Issue" if weekly else "Daily Issue"
    view_url = f"{SITE_URL}posts/{slug}.html"
    stamp = f"6:00 AM CT, {date_display}"
    caption = f"Top six by market cap. Prices as of {stamp}."
    alt = f"The Crypto Playback. Daily research and news on Bitcoin and digital assets. {date_display}."
    parts = [
        top_bar(kicker, issue_number, view_url), header_row(header_url, alt), price_strip(ticker_prices, caption),
        bottom_line_section(live, intro, base), snapshot_section(live, gauge_url, base), notable_section(missed_story, base),
        dashboard_panel(live, base), read_section(read, tag, base),
    ]
    if indicators_last:
        parts += [news_section(intro, stories, base), indicators_section(live, base)]
    else:
        parts += [indicators_section(live, base), news_section(intro, stories, base)]
    parts += [cta_section(), footer_section(live, stamp, base, year)]
    body = "\n".join(p for p in parts if p)
    body, shared_css = compact(body)
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600&family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;500;600&family=Libre+Franklin:wght@600;700&display=swap" rel="stylesheet">
<style>{shared_css}{CSS}</style>
</head>
<body style="margin:0;padding:0;background:{PAGE};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{PAGE};"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" class="v3-wrap" width="672" cellpadding="0" cellspacing="0" border="0" style="width:672px;max-width:100%;background:#FFFFFF;border:1px solid {CARD_LINE};">
{body}
</table>
</td></tr></table>
</body>
</html>"""
