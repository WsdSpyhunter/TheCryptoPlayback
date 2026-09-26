"""
build_site.py

Renders every page of the site (index, archive, and individual post pages)
from data/posts_index.json + the per-post JSON files in data/posts/.

This script is pure rendering — it does NOT call any AI or fetch any data.
generate_daily.py and generate_weekly.py call into this after they've
produced a new post's content.
"""
import json
import math
import os
from datetime import datetime, timezone
from PIL import Image, ImageDraw
from partials import page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
POSTS_DATA_DIR = os.path.join(DATA_DIR, "posts")
POSTS_HTML_DIR = os.path.join(ROOT, "posts")
GAUGES_DIR = os.path.join(ROOT, "assets", "gauges")
INDEX_FILE = os.path.join(DATA_DIR, "posts_index.json")

os.makedirs(POSTS_DATA_DIR, exist_ok=True)
os.makedirs(POSTS_HTML_DIR, exist_ok=True)
os.makedirs(GAUGES_DIR, exist_ok=True)

# House style for dates shown as "TOP NEWS: SEPT. 21, 2026" — shared by the
# website and the email so the two can never drift apart on this again.
MONTH_ABBREV = {
    1: "JAN.", 2: "FEB.", 3: "MAR.", 4: "APR.", 5: "MAY.", 6: "JUN.",
    7: "JUL.", 8: "AUG.", 9: "SEPT.", 10: "OCT.", 11: "NOV.", 12: "DEC.",
}


def format_date_abbrev(dt):
    return f"{MONTH_ABBREV[dt.month]} {dt.day}, {dt.year}"


def load_index():
    if not os.path.exists(INDEX_FILE):
        return []
    with open(INDEX_FILE) as f:
        return json.load(f)


def save_index(entries):
    with open(INDEX_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def compute_biggest_mover(prices):
    """Returns the price dict (symbol, change_24h, ...) with the largest absolute move."""
    return max(prices, key=lambda c: abs(c["change_24h"]))


def save_gauge_image(value, slug):
    """Draws the Fear & Greed gauge as a real PNG and saves it to
    assets/gauges/<slug>.png. This ONE file is used by both the website and
    the email — no separate hand-coded copies to drift apart.

    Modern flat-design dial: a thin muted track, a smooth color gradient arc
    (rendered as many small slices rather than hard-edged bands) with rounded
    end caps, and a slim charcoal needle with a two-tone hub — rendered at 4x
    and downsampled for anti-aliased, crisp edges instead of the old chunky,
    jagged 5-band look. Returns the path fragment relative to the site root."""
    scale = 4
    w, h = 200 * scale, 120 * scale
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, int(h * 0.87)
    r_outer = int(w * 0.40)
    thickness = int(w * 0.05)
    bbox = [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer]

    # Muted background track for the full sweep.
    draw.arc(bbox, start=180, end=360, fill=(224, 219, 208, 255), width=thickness)

    # Smooth red -> orange -> yellow -> green -> dark-green gradient, drawn
    # as many thin overlapping slices instead of 5 hard-edged bands.
    anchors = [
        (0.00, (226, 76, 76)), (0.25, (235, 122, 60)), (0.50, (242, 201, 76)),
        (0.75, (143, 191, 92)), (1.00, (37, 107, 50)),
    ]

    def lerp_color(t):
        for (t0, c0), (t1, c1) in zip(anchors, anchors[1:]):
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0)
                return tuple(int(c0[i] + (c1[i] - c0[i]) * f) for i in range(3))
        return anchors[-1][1]

    steps = 180
    for i in range(steps):
        t_mid = (i + 0.5) / steps
        a0 = 180 + (i / steps) * 180
        a1 = 180 + ((i + 1) / steps) * 180 + 0.6  # tiny overlap avoids seams
        draw.arc(bbox, start=a0, end=a1, fill=lerp_color(t_mid) + (255,), width=thickness)

    # Rounded end caps so the arc reads as a smooth pill, not a hard cutoff.
    cap_r = thickness / 2
    for ang, color in ((180, anchors[0][1]), (360, anchors[-1][1])):
        rad = math.radians(ang)
        px = cx + (r_outer - thickness / 2) * math.cos(rad)
        py = cy + (r_outer - thickness / 2) * math.sin(rad)
        draw.ellipse([px - cap_r, py - cap_r, px + cap_r, py + cap_r], fill=color + (255,))

    # Slim charcoal needle with a two-tone brass/charcoal hub.
    angle_deg = 180 + (value / 100) * 180
    angle_rad = math.radians(angle_deg)
    needle_len = r_outer - thickness * 1.4
    nx = cx + needle_len * math.cos(angle_rad)
    ny = cy + needle_len * math.sin(angle_rad)
    draw.line([(cx, cy), (nx, ny)], fill="#171512", width=max(2, w // 90))
    tip_r = max(2, w // 130)
    draw.ellipse([nx - tip_r, ny - tip_r, nx + tip_r, ny + tip_r], fill="#171512")
    hub_r = max(4, w // 32)
    draw.ellipse([cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r], fill="#171512")
    hub_inner_r = hub_r * 0.45
    draw.ellipse([cx - hub_inner_r, cy - hub_inner_r, cx + hub_inner_r, cy + hub_inner_r], fill="#C9974F")

    # The dial (cy near the bottom of the canvas) leaves a much bigger empty
    # margin above it than below — fine for the drawing itself, but it means
    # the visible arc isn't vertically centered in its own frame, so an
    # email/site table cell centering the *image box* still shows the arc
    # sitting low. Recenter the drawn content within the same canvas size
    # (a shift, not a resize) so the visible gauge lines up with vertically
    # centered neighbors like the mover arrow icon.
    content_bbox = img.getbbox()
    if content_bbox:
        top_margin, bottom_margin = content_bbox[1], h - content_bbox[3]
        shift = (top_margin - bottom_margin) // 2
        if shift:
            centered = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            centered.paste(img, (0, -shift), img)
            img = centered

    img = img.resize((200, 120), Image.LANCZOS)
    out_path = os.path.join(GAUGES_DIR, f"{slug}.png")
    img.save(out_path)
    return f"assets/gauges/{slug}.png"


def _fng_color(value):
    if value <= 45:
        return "#E24C4C"
    if value >= 55:
        return "#256B32"
    return "#8A7F5C"


def render_masthead():
    return '<img class="post-masthead" src="{root}assets/header-a.png" alt="The Crypto Playback">'


def render_ticker_bar(prices, date_abbrev):
    """The full 'Header B' bar: Top 5 Market tab (arrow pointing into a
    centered, evenly-spaced price grid, caption underneath the tab), the
    TOP NEWS date pill, and a subscribe/share row. Matches the approved
    email design exactly — same visual language, website's own CSS classes."""
    row1 = prices[:3]
    row2 = prices[3:]

    def chip(c):
        arrow_color = "#8FBF5C" if c["change_24h"] >= 0 else "#E8837A"
        return (f'<span class="price-chip">{c["symbol"]} ${c["price"]:,.2f} '
                f'<span style="color:{arrow_color};">({c["change_24h"]:+.1f}%)</span></span>')

    prices_html = (
        f'<div class="price-row">{"".join(chip(c) for c in row1)}</div>'
        f'<div class="price-row" style="margin-top:9px;">{"".join(chip(c) for c in row2)}</div>'
    )

    return f"""<div class="ticker-bar">
    <div class="ticker-top5-col">
      <div class="ticker-tab-wrap">
        <span class="ticker-tab">Top 5 Market</span>
        <span class="ticker-arrow"></span>
      </div>
      <span class="ticker-caption">prices as of 6AM (cst)<br>on printed date</span>
    </div>
    <div class="ticker-prices">{prices_html}</div>
  </div>
  <div class="ticker-news-pill">
    <span>TOP NEWS: <em style="color:#F2C94C;">{date_abbrev}</em></span>
  </div>
  <div class="ticker-subscribe-row">
    <span class="ticker-share-prompt">Enjoying this? Share it with a friend &rarr;</span>
    <span class="ticker-subscribe-text">SUBSCRIBE HERE</span>
    <a class="ticker-icon" href="#" style="background:#B5702E;" aria-label="Email">&#9993;</a>
    <a class="ticker-icon" href="https://x.com/cryptoplayback" style="background:#4A90D9;" aria-label="X">X</a>
  </div>"""


def render_sentiment_combined(fng, mover, tag):
    """The single combined box (Fear & Greed + Biggest Mover on one line,
    separated by a divider) inside a light-grey band. Needs gauge_path and
    root_prefix filled in by the caller since the gauge image path depends
    on where the page lives on the site."""
    fng_color = _fng_color(fng["value"])
    mover_up = mover["change_24h"] >= 0
    mover_color = "#256B32" if mover_up else "#E24C4C"
    mover_sign = "+" if mover_up else ""
    mover_label = "BIGGEST MOVER TODAY" if tag == "Daily" else "BIGGEST MOVER OF THE WEEK"
    icon_path = (
        '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>' if mover_up
        else '<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>'
    )

    return f"""<div class="sentiment-band">
    <div class="sentiment-box" style="border-color:#3A362F;">
      <img class="sentiment-gauge" src="{{gauge_src}}" alt="Fear and Greed gauge">
      <span class="sentiment-label" style="color:#975F25;">FEAR &amp; GREED</span>
      <span class="sentiment-value" style="color:{fng_color};">{fng['value']}</span>
      <span class="sentiment-word" style="color:{fng_color};">{fng['classification']}</span>
      <span class="sentiment-divider"></span>
      <svg class="sentiment-mover-icon" viewBox="0 0 24 24" fill="none" stroke="{mover_color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">{icon_path}</svg>
      <span class="sentiment-label" style="color:#975F25;">{mover_label}</span>
      <span class="sentiment-value" style="color:{mover_color};">{mover['symbol']}</span>
      <span class="sentiment-word-bold" style="color:{mover_color};">{mover_sign}{mover['change_24h']:.1f}%</span>
    </div>
  </div>"""


def render_issue_pill(tag):
    label = "DAILY ISSUE" if tag == "Daily" else "WEEKLY ISSUE"
    return f'<span class="issue-pill">{label}</span>'


def render_top_story_box(intro):
    return f"""<div class="top-story">
    <span class="top-story-tab">TOP STORY</span>
    <p class="top-story-text">{intro}</p>
  </div>"""


def render_post_html(post, root_prefix):
    """post: dict with title, date, tag, ticker_html, sentiment_html, issue_pill_html,
    top_story_html, stories (list of {headline, body, source_title, source_url, image_url})"""
    stories_html = ""
    for s in post["stories"]:
        img_html = ""
        if s.get("image_url"):
            img_html = f'<img class="story-image" src="{s["image_url"]}" alt="" loading="lazy">'
        stories_html += f"""<div class="story">
      <h3>{s['headline']}</h3>
      {img_html}
      {s['body']}
      <a class="source-link" href="{s['source_url']}" target="_blank" rel="noopener">Read more at {s['source_title']} &rarr;</a>
    </div>"""

    masthead_html = render_masthead().replace("{root}", root_prefix)
    sentiment_html = post.get('sentiment_html', '').replace("{gauge_src}", f"{root_prefix}{post.get('gauge_path', '')}")

    body = f"""<article class="post">
    {masthead_html}
    {post.get('ticker_html', '')}
    {sentiment_html}
    <div class="release-row">
      <span class="release-date">{post['date_display']}</span>
      <span class="release-issue">Issue #{post.get('issue_number', 1)}</span>
    </div>
    <div class="title-block">
      {post.get('issue_pill_html', '')}
      <h1>{post['title']}</h1>
    </div>
    {post.get('top_story_html', '')}
    {stories_html}
  </article>"""
    return page(root_prefix, f"{post['title']} — The Crypto Playback", body, datetime.now().year)


def render_index(entries):
    if not entries:
        latest_block = "<p>First post coming soon.</p>"
    else:
        latest = entries[0]
        latest_block = f"""<span class="eyebrow-tag">{latest['tag']}</span>
    <h2>{latest['title']}</h2>
    <div class="date">{latest['date_display']}</div>
    <p class="excerpt">{latest['excerpt']}</p>
    <a class="read-more" href="posts/{latest['slug']}.html">Read the full playback &rarr;</a>"""

    hero = """<section class="hero">
    <div class="wrap">
      <span class="script">The</span>
      <img class="mascot" src="assets/mascot.png" alt="The Crypto Playback mascot">
      <p class="tagline">A trusted source for efficient Bitcoin and crypto news updates.</p>
    </div>
  </section>"""

    latest_section = f'<section class="latest">{latest_block}</section>'
    body = hero + latest_section
    return page("", "The Crypto Playback", body, datetime.now().year)


def render_archive(entries):
    items = ""
    for e in entries:
        items += f"""<a class="archive-item" href="posts/{e['slug']}.html" data-tag="{e['tag']}">
      <span class="tag">{e['tag']}</span>
      <h3>{e['title']}</h3>
      <span class="date">{e['date_display']}</span>
    </a>"""

    body = f"""<div class="archive-list">
    <h1>Archive</h1>
    <div class="archive-filters">
      <button class="active" data-filter="all">All</button>
      <button data-filter="Daily">Daily</button>
      <button data-filter="Weekly">Weekly</button>
    </div>
    <div id="archive-items">{items}</div>
  </div>
  <script>
    document.querySelectorAll('.archive-filters button').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.archive-filters button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const f = btn.dataset.filter;
        document.querySelectorAll('.archive-item').forEach(item => {{
          item.style.display = (f === 'all' || item.dataset.tag === f) ? 'block' : 'none';
        }});
      }});
    }});
  </script>"""
    return page("", "Archive — The Crypto Playback", body, datetime.now().year)


def add_post_and_rebuild(post):
    """post: dict as passed to render_post_html, plus 'excerpt' and 'slug'.
    Writes the post's HTML page, updates the index, and rebuilds index.html + archive.html."""
    with open(os.path.join(POSTS_DATA_DIR, f"{post['slug']}.json"), "w") as f:
        json.dump(post, f, indent=2)

    post_html = render_post_html(post, "../")
    with open(os.path.join(POSTS_HTML_DIR, f"{post['slug']}.html"), "w") as f:
        f.write(post_html)

    entries = load_index()
    entries.insert(0, {
        "slug": post["slug"],
        "title": post["title"],
        "date_display": post["date_display"],
        "tag": post["tag"],
        "excerpt": post["excerpt"],
    })
    save_index(entries)

    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(render_index(entries))
    with open(os.path.join(ROOT, "archive.html"), "w") as f:
        f.write(render_archive(entries))


if __name__ == "__main__":
    entries = load_index()
    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(render_index(entries))
    with open(os.path.join(ROOT, "archive.html"), "w") as f:
        f.write(render_archive(entries))
    print(f"Rebuilt index.html and archive.html from {len(entries)} existing post(s).")
