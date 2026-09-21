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
from partials import page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
POSTS_DATA_DIR = os.path.join(DATA_DIR, "posts")
POSTS_HTML_DIR = os.path.join(ROOT, "posts")
INDEX_FILE = os.path.join(DATA_DIR, "posts_index.json")

os.makedirs(POSTS_DATA_DIR, exist_ok=True)
os.makedirs(POSTS_HTML_DIR, exist_ok=True)


def load_index():
    if not os.path.exists(INDEX_FILE):
        return []
    with open(INDEX_FILE) as f:
        return json.load(f)


def save_index(entries):
    with open(INDEX_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def render_ticker(prices):
    """prices: list of {symbol, name, price, change_24h}"""
    coins = ""
    for c in prices:
        arrow = "+" if c["change_24h"] >= 0 else ""
        coins += (
            f'<div class="coin"><span class="sym">{c["symbol"]}</span>'
            f'<span>${c["price"]:,.2f}</span>'
            f'<span>({arrow}{c["change_24h"]:.1f}%)</span></div>'
        )
    updated = datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC")
    return f"""<div class="ticker"><div class="wrap">{coins}
    <span class="updated">Updated {updated}</span></div></div>"""


def compute_biggest_mover(prices):
    """Returns the price dict (symbol, change_24h, ...) with the largest absolute move."""
    return max(prices, key=lambda c: abs(c["change_24h"]))


def _fng_needle_point(value, cx=50, cy=52, length=30):
    """Angle sweeps from 180deg (value=0) to 0deg (value=100) across the gauge's semicircle."""
    angle_deg = 180 - (value / 100 * 180)
    angle_rad = math.radians(angle_deg)
    x = cx + length * math.cos(angle_rad)
    y = cy - length * math.sin(angle_rad)
    return round(x, 1), round(y, 1)


def _fng_color(value):
    if value <= 45:
        return "#E24C4C"  # red — Fear / Extreme Fear
    if value >= 55:
        return "#256B32"  # green — Greed / Extreme Greed
    return "#8A7F5C"  # neutral tan


def render_sentiment_bar(fng, mover, tag):
    """fng: {'value': int, 'classification': str}
    mover: a price dict (symbol, change_24h, ...) — the biggest mover
    tag: 'Daily' or 'Weekly' — controls the mover box's label wording"""
    nx, ny = _fng_needle_point(fng["value"])
    fng_color = _fng_color(fng["value"])
    mover_up = mover["change_24h"] >= 0
    mover_color = "#256B32" if mover_up else "#E24C4C"
    mover_sign = "+" if mover_up else ""
    mover_label = "BIGGEST MOVER TODAY" if tag == "Daily" else "BIGGEST MOVER OF THE WEEK"
    icon_path = (
        '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>' if mover_up
        else '<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>'
    )

    return f"""<div class="sentiment-bar">
    <div class="stat-box" style="border-color:{fng_color};">
      <svg width="46" height="30" viewBox="0 0 100 60">
        <defs>
          <linearGradient id="fngGrad" x1="12" y1="52" x2="88" y2="52" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#E24C4C"/>
            <stop offset="50%" stop-color="#F2C94C"/>
            <stop offset="100%" stop-color="#256B32"/>
          </linearGradient>
        </defs>
        <path d="M12,52 A38,38 0 0 1 88,52" fill="none" stroke="url(#fngGrad)" stroke-width="9" stroke-linecap="round"/>
        <circle cx="50" cy="52" r="3.5" fill="#FBF9F5"/>
        <line x1="50" y1="52" x2="{nx}" y2="{ny}" stroke="#FBF9F5" stroke-width="3" stroke-linecap="round"/>
      </svg>
      <div class="stat-text">
        <span class="stat-label">FEAR &amp; GREED</span><br>
        <span class="stat-value" style="color:{fng_color};">{fng['value']}</span>
        <span class="stat-word" style="color:{fng_color};">&nbsp;{fng['classification']}</span>
      </div>
    </div>
    <div class="stat-box" style="border-color:#3A362F;">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{mover_color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">{icon_path}</svg>
      <div class="stat-text">
        <span class="stat-label">{mover_label}</span><br>
        <span class="stat-value" style="color:{mover_color};">{mover['symbol']}</span>
        <span class="stat-word-bold" style="color:{mover_color};">&nbsp;{mover_sign}{mover['change_24h']:.1f}%</span>
      </div>
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

    body = f"""<article class="post">
    <span class="date">{post['date_display']} &middot; {post['tag']}</span>
    <h1>{post['title']}</h1>
    {post.get('ticker_html', '')}
    {post.get('sentiment_html', '')}
    <div class="release-row">
      <span class="release-date">{post['date_display']}</span>
      <span class="release-issue">Issue #{post.get('issue_number', 1)}</span>
    </div>
    <div class="title-block">
      {post.get('issue_pill_html', '')}
      {post.get('top_story_html', '')}
    </div>
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
