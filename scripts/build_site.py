"""
build_site.py

Renders every page of the site (index, archive, and individual post pages)
from data/posts_index.json + the per-post JSON files in data/posts/.

This script is pure rendering — it does NOT call any AI or fetch any data.
generate_daily.py and generate_weekly.py call into this after they've
produced a new post's content.
"""
import json
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


def render_post_html(post, root_prefix):
    """post: dict with title, date, tag, ticker_html, stories (list of
    {headline, body, source_title, source_url, image_url})"""
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
