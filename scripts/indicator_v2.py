"""Version 2 indicator pages (markup only): one page per live indicator.

build_site.render_indicator_pages() passes each registry entry plus its history rows here. The
text, numbers and history come from the same registry as before; only the presentation changed.
"""
import json
import re
from datetime import datetime
from html import escape

from partials import page, SITE_URL
import v2_ui as ui
from home_v2 import LAB_LINKS, indicator_footer_links

LAB_NAMES = {"pressure": "Institutional Positioning", "unwind": "Crowded Unwind Risk", "stables": "Stablecoin Flows"}


def _plain(s):
    t = re.sub(r"<[^>]+>", "", s or "")
    for a, b in (("&amp;", "&"), ("&ndash;", "-"), ("&mdash;", "-"), ("&middot;", "·"), ("&rarr;", "→"), ("&#39;", "'"), ("&nbsp;", " ")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def render(ind, history_rows, refresh_note, all_inds):
    title = ind["page_title"]
    plain_title = _plain(title)
    sections = ind["page_sections"]
    cards = "".join(f'<article class="v2-ind-card"><h2>{h}</h2>{body}</article>' for h, body in sections)
    if history_rows:
        rows = "".join(f'<div class="v2-ind-row"><span class="v2-ind-date">{r["date_display"]}</span>'
                       f'<span class="v2-ind-hv">{ind["history_formatter"](r)}</span></div>' for r in history_rows)
    else:
        rows = '<p class="v2-ind-empty">No history yet. Check back after the next refresh.</p>'
    history = (f'<section class="v2-ind-history" aria-labelledby="hist-h"><h2 id="hist-h">Recent readings</h2>'
               f'<div class="v2-ind-rows">{rows}</div><p class="v2-ind-note">{refresh_note}</p></section>')
    lab = LAB_LINKS.get(ind["id"])
    lab_html = (f'<a class="v2-ind-lab" href="playback-lab.html#{lab}"><span>Go deeper</span><strong>See the {LAB_NAMES[lab]} reading in the Playback Lab</strong>'
                f'<em>&rarr;</em></a>') if lab else ""
    chips = "".join(f'<a href="{o["page"]}">{ui.strip_emoji(o["card_label"])}</a>' for o in all_inds if o["id"] != ind["id"])
    related = (f'<section class="v2-ind-related" aria-labelledby="rel-h"><h2 id="rel-h">More live indicators</h2><div class="v2-ind-chips">{chips}</div></section>')
    first = _plain(sections[0][1]) if sections else ""
    desc = f"{plain_title}: {first}" if first else f"{plain_title}, a live crypto market indicator from The Crypto Playback."
    if len(desc) > 158:
        desc = desc[:155].rsplit(" ", 1)[0] + "..."
    hero = f"""<section class="v2-ind-hero" aria-labelledby="ind-h">
  <div class="v2-wrap">
    <nav class="v2-crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a><span aria-hidden="true">›</span><a href="index.html#alerts">Indicators</a><span aria-hidden="true">›</span><span aria-current="page">{title}</span></nav>
    <div class="v2-kicker v2-kicker-brass v2-ind-kicker">Live indicator · refreshed automatically</div>
    <h1 class="v2-ind-title" id="ind-h"><span class="v2-ind-icon" aria-hidden="true">{ui.icon(ind['id'], 40)}</span>{title}</h1>
    <div class="v2-ind-value">{ind['page_hero_html']}</div>
    <p class="v2-ind-updated">Last updated {ind['last_updated_display']}</p>
  </div>
</section>"""
    body = f"""{hero}
<section class="v2-section v2-ind-body">
  <div class="v2-wrap">
    <div class="v2-ind-grid">{cards}</div>
    {lab_html}
    {history}
    {related}
    <p class="v2-ind-sub"><a class="v2-btn v2-btn-navy" href="index.html#subscribe">Get the daily playback free</a></p>
  </div>
</section>"""
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
        {"@type": "ListItem", "position": 2, "name": "Indicators", "item": f"{SITE_URL}/#alerts"},
        {"@type": "ListItem", "position": 3, "name": plain_title, "item": f"{SITE_URL}/{ind['page']}"}]}
    return page("", f"{plain_title}: Live Crypto Indicator | The Crypto Playback", body, datetime.now().year, theme="v2",
                description=desc, path=ind["page"], indicator_links=indicator_footer_links(all_inds), jsonld=json.dumps(crumbs, separators=(",", ":")))
