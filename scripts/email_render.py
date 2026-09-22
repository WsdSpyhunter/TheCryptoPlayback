"""
email_render.py — shared HTML rendering for the EMAIL version of a post
(masthead through footer). Used by both generate_daily.py and
generate_weekly.py so the two never drift apart on design.

Built entirely from flex divs, NOT tables. Tables are what caused the
catastrophic column-collapse bug in Buttondown's rendering pipeline —
this design deliberately avoids that whole category of risk.
"""
import os
from datetime import datetime

from build_site import ROOT
from buttondown_client import upload_image

# Real, public URLs — these images live in the site's own assets/ folder,
# so they resolve correctly inside an actual email sent to real inboxes
# (unlike design-tool preview URLs, which only work inside that tool).
ASSET_BASE = "https://cryptoplayback.com/assets"


def upload_gauge_image(gauge_path):
    """A hosted URL, NOT a base64 data URI — Buttondown's dashboard silently
    rewrites an entire draft's body into its lossy Fancy-mode markup the
    moment a base64 image is opened in the editor (it re-uploads the image
    to its own CDN and converts everything else as a side effect); confirmed
    by direct testing against the live API.

    Uploaded straight to Buttondown's own image hosting rather than linked
    from cryptoplayback.com/assets/ — the gauge is generated fresh per-post
    and the site's copy of it only goes live once the content PR is merged,
    but the draft needs to render correctly for review before that merge
    ever happens."""
    return upload_image(os.path.join(ROOT, gauge_path))


def masthead_email_html():
    # A background-image div, NOT an <img> tag. Buttondown's dashboard treats a
    # standalone <img> as a "hero image" media object with its own reserved
    # caption slot (visible as an "Add caption" prompt in the editor) — that
    # slot's space shows as a gap below the masthead in the actual rendered
    # email, regardless of width/height attributes on the <img> itself (tried
    # and confirmed against the live account). A div with a CSS background
    # isn't recognized as that kind of media object, so it doesn't get one.
    return (
        f"<div role='img' aria-label='The Crypto Playback' "
        f"style='width:100%;max-width:640px;aspect-ratio:2170/506;"
        f"background-image:url(\"{ASSET_BASE}/header-a.png\");"
        f"background-size:cover;background-position:center;display:block;'></div>"
    )


def ticker_bar_email_html(prices, date_abbrev):
    """Matches the approved design exactly: Top 5 Market tab with the arrow
    pointing into a single evenly-spaced row of all 5 prices, caption under
    the tab, a separate news-date pill, and a share/subscribe row."""

    def chip(c):
        arrow_color = "#8FBF5C" if c["change_24h"] >= 0 else "#E8837A"
        return (f'<span style="color:#FBF9F5; font-family:Arial,sans-serif; font-size:12px; white-space:nowrap;">'
                f'{c["symbol"]} ${c["price"]:,.2f} <span style="color:{arrow_color};">({c["change_24h"]:+.1f}%)</span></span>')

    prices_html = f'<div style="display:flex; flex-wrap:wrap; align-items:center; gap:16px;">{"".join(chip(c) for c in prices)}</div>'

    return f"""<div style="background:#171512; padding:20px 20px;">
  <div style="display:flex; align-items:center;">
    <div style="flex-shrink:0; display:flex; flex-direction:column;">
      <div style="display:flex; align-items:center;">
        <span style="display:inline-block;background:#DE9547;color:#171512;font-family:Arial,sans-serif;font-weight:bold;font-size:14px;padding:10px 12px;white-space:nowrap;">Top 5 Market</span>
        <span style="display:inline-block;width:0;height:0;border-top:19px solid transparent;border-bottom:19px solid transparent;border-left:14px solid #DE9547;"></span>
      </div>
      <span style="color:#FBF9F5;opacity:0.6;font-size:10px;margin-top:8px;line-height:1.3;">prices as of 6AM (cst)<br>on printed date</span>
    </div>
    <div style="flex:1; padding-top:6px; margin-left:24px;">
      {prices_html}
    </div>
  </div>
</div>
<div style="background:#3a3835; padding:10px 20px; text-align:center;">
  <span style="font-family:Arial,sans-serif; font-size:15px; color:#FBF9F5;">TOP NEWS: <em style="color:#F2C94C;">{date_abbrev}</em></span>
</div>
<div style="background:#171512; padding:12px 20px; display:flex; align-items:center; justify-content:center; gap:14px;">
  <span style="font-family:Georgia,serif; font-style:italic; font-size:12px; color:#FBF9F5; opacity:0.75;">Enjoying this? Share it with a friend &rarr;</span>
  <span style="font-family:Arial,sans-serif; font-size:16px; font-weight:bold; color:#FBF9F5;">SUBSCRIBE HERE</span>
  <a href="#" style="display:inline-flex;align-items:center;justify-content:center;width:27px;height:27px;border-radius:50%;background:#B5702E;color:#FBF9F5;text-align:center;font-size:13px;text-decoration:none;">&#9993;</a>
  <a href="https://x.com/cryptoplayback" style="display:inline-flex;align-items:center;justify-content:center;width:27px;height:27px;border-radius:50%;background:#4A90D9;color:#FBF9F5;text-align:center;font-size:13px;text-decoration:none;">X</a>
</div>"""


def sentiment_to_email_html(fng, mover, gauge_src):
    """Single combined box (Fear & Greed + Biggest Mover on one line,
    separated by a divider) inside a light-grey band — matches the approved
    design."""
    fng_color = "#E24C4C" if fng["value"] <= 45 else ("#256B32" if fng["value"] >= 55 else "#8A7F5C")
    mover_up = mover["change_24h"] >= 0
    mover_color = "#256B32" if mover_up else "#E24C4C"
    mover_sign = "+" if mover_up else ""
    icon_path = (
        '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>' if mover_up
        else '<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>'
    )
    return f"""<div style="background:#F1EEE7; padding:12px 12px;">
  <div style="background:rgba(255,255,255,0.06); border:1.5px solid #3A362F; border-radius:6px; padding:10px 10px; display:flex; align-items:center; justify-content:center; flex-wrap:nowrap; white-space:nowrap;">
    <span style="white-space:nowrap; flex-shrink:0;">
      <img src="{gauge_src}" width="36" height="23" style="vertical-align:middle; display:inline;" alt="Fear and Greed gauge">
      <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:10px; color:#975F25; vertical-align:middle; margin-left:4px;">FEAR &amp; GREED</span>
      <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:17px; color:{fng_color}; vertical-align:middle; margin-left:3px;">{fng['value']}</span>
      <span style="font-size:11px; color:{fng_color}; vertical-align:middle;">{fng['classification']}</span>
    </span>
    <span style="display:inline-block; flex-shrink:0; width:1.5px; height:24px; background:#3A362F; vertical-align:middle; margin:0 10px;"></span>
    <span style="white-space:nowrap; flex-shrink:0;">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{mover_color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;">{icon_path}</svg>
      <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:10px; color:#975F25; vertical-align:middle; margin-left:4px;">BIGGEST MOVER</span>
      <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:17px; color:{mover_color}; vertical-align:middle; margin-left:3px;">{mover['symbol']}</span>
      <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:13px; color:{mover_color}; vertical-align:middle;">{mover_sign}{mover['change_24h']:.1f}%</span>
    </span>
  </div>
</div>"""


def release_row_email_html(date_display, issue_number):
    return f"""<div style="margin:20px 20px 0; padding:10px 16px; background:#F1EEE7; border-radius:4px; box-shadow:0 2px 5px rgba(23,21,18,0.18); display:flex; justify-content:space-between;">
  <span style="font-family:Arial,sans-serif; font-size:12px; color:#666666;">Release date: {date_display}</span>
  <span style="font-family:Arial,sans-serif; font-size:12px; color:#666666;">Issue #{issue_number}</span>
</div>"""


def issue_title_block_email_html(tag, title):
    label = "DAILY ISSUE" if tag == "Daily" else "WEEKLY ISSUE"
    # !important on the h1 margin: Buttondown's renderer applies its own default
    # vertical rhythm to heading tags specifically, overriding a plain inline
    # margin — this fights that back to keep the title tight to the callout
    # below it instead of leaving a large gap.
    return f"""<div style="padding:16px 20px 4px;">
<span style="display:inline-block;font-family:Arial,sans-serif;font-weight:bold;font-size:11px;letter-spacing:0.04em;color:#FBF9F5;background:#268CCA;padding:4px 10px;border-radius:3px;">{label}</span>
<h1 style="font-family:Arial,sans-serif;font-weight:bold;font-size:26px;color:#171512;margin:8px 0 0 !important;line-height:1.15;">{title}</h1>
</div>"""


def top_story_to_email_html(intro):
    return f"""<div style="margin:8px 20px 0; display:flex; background:#F1EEE7; border-radius:4px; overflow:hidden;">
  <span style="flex-shrink:0; width:38px; background:#F2C94C; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; font-family:Arial,sans-serif; font-weight:bold; font-size:10px; padding:4px 2px;"><span style="white-space:nowrap;">TOP</span><span style="white-space:nowrap;">STORY</span></span>
  <p style="flex:1; min-width:0; padding:14px 20px 14px 16px; font-family:Georgia,serif; font-style:italic; font-size:18px; margin:0;">{intro}</p>
</div>"""


def footer_email_html():
    year = datetime.now().year
    # Background-image div, same reasoning as the masthead — a standalone <img>
    # here gets Buttondown's "hero image" caption-slot treatment too.
    disclaimer_html = (
        f"<div role='img' aria-label='Legal disclaimer: The Crypto Playback is not financial advice.' "
        f"style='width:100%;max-width:640px;aspect-ratio:2040/242;"
        f"background-image:url(\"{ASSET_BASE}/disclaimer.png\");"
        f"background-size:cover;background-position:center;display:block;margin-top:24px;'></div>"
    )
    return f"""{disclaimer_html}
<div style="background:#975F25; padding:14px 20px; display:flex; justify-content:space-between; align-items:flex-end;">
  <span style="color:#FBF9F5;font-family:Arial,sans-serif;font-size:12px;">&copy; {year} The Crypto Playback &middot; info@cryptoplayback.com</span>
  <div style="display:flex; align-items:flex-end; gap:8px;">
    <img src='{ASSET_BASE}/mascot-icon.png' width='54' height='50' style='width:54px;height:50px;display:block;' alt=''>
    <img src='{ASSET_BASE}/logo-white.png' width='90' height='43' style='width:90px;height:auto;display:block;'>
  </div>
</div>
<p style="text-align:center;font-family:Arial,sans-serif;font-size:11px;color:#666666;padding:10px 0;margin:0;background:#FBF9F5;">
  <a href="{{{{ unsubscribe_url }}}}" style="color:#666666;">Unsubscribe from The Crypto Playback</a>
</p>"""


def stories_to_plain_email_html(issue_title, intro, stories, ticker_prices, fng, mover, tag, date_display, date_abbrev, issue_number, gauge_src):
    """Full HTML rendering for the email body — masthead through footer,
    matching the approved design exactly. `stories` can be a single-item
    list (daily) or several (weekly)."""
    parts = [
        masthead_email_html(),
        ticker_bar_email_html(ticker_prices, date_abbrev),
        sentiment_to_email_html(fng, mover, gauge_src),
        release_row_email_html(date_display, issue_number),
        issue_title_block_email_html(tag, issue_title),
        top_story_to_email_html(intro),
    ]
    for s in stories:
        img_html = f"<p><img src='{s['image_url']}' style='max-width:100%;'></p>" if s.get("image_url") else ""
        parts.append(f"<h3 style='font-family:Arial,Helvetica,sans-serif;font-weight:bold;font-size:20px;color:#171512;margin:0 0 10px;'>{s['headline']}</h3>{img_html}{s['body']}"
                      f"<p><a href='{s['source_url']}' style='color:#B5702E;font-weight:bold;text-decoration:none;'>Read more at {s['source_title']} &rarr;</a></p>"
                      f"<hr style='margin:16px 0; border:none; border-top:1px solid #DDD9CE;'>")
    parts.append(footer_email_html())
    body_html = "\n".join(parts[1:])  # everything except the masthead image
    wrapped = f"<div style='font-family:Arial,Helvetica,sans-serif;color:#171512;font-size:15px;line-height:1.5;'>{body_html}</div>"
    return parts[0] + "\n" + wrapped
