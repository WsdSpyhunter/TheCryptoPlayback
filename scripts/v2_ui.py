"""Version 2 UI building blocks: icons, status pills, gauge, title boxes.

Markup helpers only - no data fetching. The visual language comes from the
v2 newsletter design (navy / brass / ivory); the matching styles live in
assets/v2.css. build_site.render_index() assembles these into the homepage.
"""
import math
import re
from html import escape

# Line icons (48x48 grid, 3px stroke) from the v2 newsletter design. The
# first fourteen are the design's own; breadth/narrative are new, drawn in
# the same style.
ICON_PATHS = {
    "fear_greed": '<path d="M6 34a18 18 0 0 1 36 0"/><path d="M24 34l9-12"/>',
    "biggest_mover": '<path d="M8 36l10-12 8 6 14-18"/><path d="M30 12h10v10"/>',
    "risk_radar": '<path d="M24 8L42 40H6z"/><path d="M24 20v10M24 35v1"/>',
    "capital_flow": '<path d="M8 24h32"/><path d="M30 14l10 10-10 10"/>',
    "top_sectors": '<rect x="8" y="8" width="13" height="13" rx="2"/><rect x="27" y="8" width="13" height="13" rx="2"/><rect x="8" y="27" width="13" height="13" rx="2"/><rect x="27" y="27" width="13" height="13" rx="2"/>',
    "dominance_rotation": '<path d="M38 20a14 14 0 0 0-26-4"/><path d="M10 28a14 14 0 0 0 26 4"/><path d="M12 8v8h8M36 40v-8h-8"/>',
    "leverage_heat": '<path d="M24 6c2 8 10 12 10 22a10 10 0 0 1-20 0c0-6 4-8 4-14 4 2 6 6 6 10"/>',
    "stablecoin_liquidity": '<circle cx="24" cy="24" r="16"/><path d="M24 15v18"/><path d="M29 20h-7a3 3 0 0 0 0 6h4a3 3 0 0 1 0 6h-8"/>',
    "defi_pulse": '<path d="M24 8l16 8-16 8-16-8z"/><path d="M8 24l16 8 16-8"/><path d="M8 32l16 8 16-8"/>',
    "network_health": '<rect x="14" y="14" width="20" height="20" rx="2"/><path d="M20 8v6M28 8v6M20 34v6M28 34v6M8 20h6M8 28h6M34 20h6M34 28h6"/>',
    "liquidations": '<path d="M26 6L12 26h10l-2 16 16-22H26z"/>',
    "whale_activity": '<path d="M6 26c6-8 12-8 18 0s12 8 18 0"/><path d="M6 36c6-8 12-8 18 0s12 8 18 0"/><path d="M6 16c6-8 12-8 18 0s12 8 18 0"/>',
    "macro_risk": '<circle cx="24" cy="24" r="16"/><path d="M8 24h32"/><path d="M24 8c-8 9-8 23 0 32M24 8c8 9 8 23 0 32"/>',
    "etf_flow": '<rect x="9" y="26" width="6" height="12"/><rect x="19" y="18" width="6" height="20"/><rect x="29" y="10" width="6" height="28"/><path d="M6 41h36"/>',
    "market_breadth": '<path d="M8 12h32M8 24h24M8 36h14"/>',
    "narrative_momentum": '<path d="M8 10h32v22H20l-8 8v-8H8z"/>',
    # section / title icons
    "bottom_line": '<path d="M16 12h26M16 24h26M16 36h26"/><circle cx="7" cy="12" r="1.5"/><circle cx="7" cy="24" r="1.5"/><circle cx="7" cy="36" r="1.5"/>',
    "snapshot": '<path d="M6 34a18 18 0 0 1 36 0"/><path d="M24 34l9-12"/><circle cx="24" cy="34" r="2"/>',
    "notable": '<circle cx="24" cy="24" r="17"/><circle cx="24" cy="24" r="8"/><path d="M24 24L37 11"/>',
    "confluence": '<rect x="8" y="8" width="13" height="13" rx="2"/><rect x="27" y="8" width="13" height="13" rx="2"/><rect x="8" y="27" width="13" height="13" rx="2"/><rect x="27" y="27" width="13" height="13" rx="2"/>',
    "changed": '<path d="M8 18h30l-7-7M40 30H10l7 7"/>',
    "alerts": '<path d="M10 34V22a14 14 0 0 1 28 0v12l3 4H7z"/><path d="M20 43h8"/>',
    "news": '<rect x="8" y="8" width="32" height="32" rx="2"/><path d="M14 16h12M14 22h20M14 28h20M14 34h12"/>',
    "structure": '<path d="M6 18L24 8l18 10"/><path d="M12 22v14M20 22v14M28 22v14M36 22v14"/><path d="M6 41h36"/>',
    "calendar": '<rect x="7" y="10" width="34" height="30" rx="2"/><path d="M7 19h34M16 6v8M32 6v8"/>',
    "book": '<path d="M8 10h14a4 4 0 0 1 4 4v26a3 3 0 0 0-3-3H8z"/><path d="M40 10H26"/><path d="M40 10v27H27"/>',
    "mail": '<rect x="6" y="10" width="36" height="28" rx="2"/><path d="M6 14l18 14 18-14"/>',
    "arrow": '<path d="M8 24h32"/><path d="M30 14l10 10-10 10"/>',
}

_EMOJI_ENTITY = re.compile(r"&#\d+;")


def icon(key, size=22, cls="v2-icon"):
    paths = ICON_PATHS.get(key, ICON_PATHS["news"])
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" '
            f'stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true" focusable="false">{paths}</svg>')


def strip_emoji(label_html):
    """Registry card labels carry a leading emoji as numeric entities
    ("&#9888;&#65039; Risk Radar"); v2 uses line icons instead."""
    return _EMOJI_ENTITY.sub("", label_html).strip()


def pill(state):
    """Status pill. True -> Positive, False -> Negative, None -> Neutral.
    Words, not just color, so it never relies on color alone."""
    if state is True:
        return '<span class="v2-pill v2-pill-pos">Positive</span>'
    if state is False:
        return '<span class="v2-pill v2-pill-neg">Negative</span>'
    return '<span class="v2-pill v2-pill-neu">Neutral</span>'


def title_box(icon_key, title, meta_html="", tag="h2", dark=False):
    """The design's section title: white box with a soft shadow sitting on a
    2px navy rule, meta text pushed to the far right."""
    meta = f'<span class="v2-title-meta">{meta_html}</span>' if meta_html else ""
    cls = "v2-titlebar v2-titlebar-dark" if dark else "v2-titlebar"
    return (f'<div class="{cls}"><div class="v2-titlebox">{icon(icon_key)}'
            f'<{tag} class="v2-titletext">{title}</{tag}></div>{meta}</div>')


# --- Sentiment gauge (inline SVG, replaces the old pre-rendered PNG) -------

_GAUGE_SEGMENTS = ["#8E2B25", "#C98079", "#C9C2B0", "#6FA98A", "#1E7A4C"]


def _polar(cx, cy, r, deg):
    rad = math.radians(180 - deg)
    return cx + r * math.cos(rad), cy - r * math.sin(rad)


def gauge_svg(value, label):
    """Semicircle 0-100 gauge, five colored bands and a needle. Same geometry
    as the newsletter design (200x122, radius 80)."""
    value = max(0, min(100, int(value)))
    cx, cy, r = 100, 100, 80
    arcs = ""
    for i, color in enumerate(_GAUGE_SEGMENTS):
        x1, y1 = _polar(cx, cy, r, i * 36)
        x2, y2 = _polar(cx, cy, r, (i + 1) * 36)
        arcs += (f'<path d="M{x1:.1f} {y1:.1f} A{r} {r} 0 0 1 {x2:.1f} {y2:.1f}" '
                 f'fill="none" stroke="{color}" stroke-width="12"/>')
    nx, ny = _polar(cx, cy, 62, value * 1.8)
    return (f'<svg class="v2-gauge" viewBox="0 0 200 122" role="img" '
            f'aria-label="Sentiment gauge showing {value}, {escape(label)}">{arcs}'
            f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#0B1F3A" stroke-width="3" stroke-linecap="round"/>'
            f'<circle cx="{cx}" cy="{cy}" r="6" fill="#0B1F3A"/>'
            f'<text x="20" y="118" text-anchor="middle" font-size="10" fill="#5B6472">0</text>'
            f'<text x="180" y="118" text-anchor="middle" font-size="10" fill="#5B6472">100</text></svg>')


# --- Hero decoration ---------------------------------------------------------

def candlesticks_svg():
    """Faint outlined candlesticks behind the hero, as in the newsletter header."""
    bars = [(40, 150, 90, 40), (110, 120, 70, 120), (180, 80, 110, 60), (250, 130, 60, 150),
            (320, 60, 130, 90), (390, 100, 90, 40), (460, 40, 120, 70), (530, 70, 80, 130)]
    out = ""
    for x, wick_top, body_h, body_y in bars:
        out += (f'<line x1="{x+12}" y1="{body_y-24}" x2="{x+12}" y2="{body_y+body_h+30}"/>'
                f'<rect x="{x}" y="{body_y}" width="24" height="{body_h}"/>')
    return (f'<svg class="v2-hero-candles" viewBox="0 0 580 300" fill="none" stroke="currentColor" '
            f'stroke-width="2" aria-hidden="true" focusable="false">{out}</svg>')


# --- Live ticker (same CoinGecko polling as v1, class-based colors) ----------

LIVE_TICKER_SCRIPT = """<script>
(function () {
  var coins = Array.prototype.slice.call(document.querySelectorAll('.v2-coin[data-coingecko-id]'))
    .filter(function (el) { return el.getAttribute('data-coingecko-id'); });
  if (!coins.length) return;
  var ids = coins.map(function (el) { return el.getAttribute('data-coingecko-id'); }).join(',');
  var asof = document.getElementById('pulse-asof');
  function poll() {
    fetch('https://api.coingecko.com/api/v3/simple/price?ids=' + encodeURIComponent(ids) +
          '&vs_currencies=usd&include_24hr_change=true')
      .then(function (r) { if (!r.ok) throw new Error('CoinGecko ' + r.status); return r.json(); })
      .then(function (data) {
        coins.forEach(function (el) {
          var quote = data[el.getAttribute('data-coingecko-id')];
          if (!quote || typeof quote.usd !== 'number') return;
          var priceEl = el.querySelector('.v2-coin-price');
          var changeEl = el.querySelector('.v2-coin-change');
          if (priceEl) priceEl.textContent = '$' + quote.usd.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
          if (changeEl && typeof quote.usd_24h_change === 'number') {
            var c = quote.usd_24h_change;
            changeEl.textContent = (c > 0.05 ? '\\u25B2 ' : c < -0.05 ? '\\u25BC ' : '\\u25AC ') + Math.abs(c).toFixed(1) + '%';
            changeEl.className = 'v2-coin-change ' + (c > 0.05 ? 'up' : c < -0.05 ? 'down' : 'flat');
          }
        });
        if (asof) {
          asof.textContent = 'Live prices via CoinGecko \\u00b7 last updated ' +
            new Date().toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit', second: '2-digit'});
        }
      })
      .catch(function (err) { console.warn('Live ticker update skipped:', err); });
  }
  poll();
  setInterval(poll, 60000);
})();
</script>"""


def split_value(display):
    """Break a registry confluence_display ("71 Greed", "$312.6B (+0.5%)",
    "13 transfers (Elevated)", "0/3 positive") into (value, detail) for the
    big-number-plus-small-text layout."""
    text = (display or "").strip()
    m = re.match(r"^(.*?)\s*\((.*)\)$", text)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"^([\d/.,%+\-$]+)\s+([A-Za-z].*)$", text)
    if m:
        return m.group(1), m.group(2)
    return text, ""
