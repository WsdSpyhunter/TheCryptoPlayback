"""Run once (or whenever you want to edit About/Resources copy) to regenerate
the two static pages. Unlike index/archive/posts, these are NOT touched by
the daily/weekly automation — edit this file and rerun it by hand."""
import os
from datetime import datetime
from partials import page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ABOUT_BODY = """<div class="page-content">
  <h1>About The Crypto Playback</h1>
  <p>The Crypto Playback is your trusted source for efficient Bitcoin and crypto news and data.</p>
  <p>The website and newsletter both offer a quick scan of the top headlines plus deep, high-value data. All in one place, on a single page, free for subscribers.</p>
  <p>No more spending your day scrolling Crypto Twitter or hunting across multiple sites for the information you need.</p>
  <p>One stop. One look. A quick Crypto Playback and you&rsquo;re fully informed on the fastest-moving industry on the planet.</p>
  <p>Nothing here is financial advice. See the note at the bottom of every page for the full disclosure.</p>
  <h1 style="margin-top:2em;">Contact</h1>
  <p>Questions, tips, or feedback: <a href="mailto:info@cryptoplayback.com">info@cryptoplayback.com</a></p>
</div>"""

RESOURCES_BODY = """<div class="page-content">
  <h1>Resources</h1>
  <p>A short list of places to go deeper. (Edit this page any time in
  <code>scripts/build_static_pages.py</code> — it's the one page the
  automation never touches.)</p>
  <h3>Learn the basics</h3>
  <ul>
    <li>The Basics of Bitcoin — by W.S. Davis</li>
  </ul>
  <h3>Glossary</h3>
  <ul>
    <li><strong>Cold storage</strong> — keeping crypto offline, away from internet-connected wallets.</li>
    <li><strong>DCA (dollar-cost averaging)</strong> — buying a fixed dollar amount on a regular schedule, regardless of price.</li>
    <li><strong>Market cap</strong> — price per coin &times; total coins in circulation.</li>
  </ul>
</div>"""


def build():
    year = datetime.now().year
    with open(os.path.join(ROOT, "about.html"), "w") as f:
        f.write(page("", "About — The Crypto Playback", ABOUT_BODY, year))
    with open(os.path.join(ROOT, "resources.html"), "w") as f:
        f.write(page("", "Resources — The Crypto Playback", RESOURCES_BODY, year))
    print("Built about.html and resources.html")


if __name__ == "__main__":
    build()
