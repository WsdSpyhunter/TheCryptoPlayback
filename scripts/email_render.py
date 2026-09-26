"""
email_render.py — shared HTML rendering for the EMAIL version of a post
(masthead through footer). Used by both generate_daily.py and
generate_weekly.py so the two never drift apart on design.

Built on tables for anything requiring side-by-side alignment, not flexbox.
An earlier flex-based version rendered perfectly in a real browser but broke
in real inboxes (Gmail web/app, Apple Mail) — flex-wrap and the `gap`
property were silently ignored, and `position:relative;left:Npx` nudges
caused elements to render outside their containing box entirely. Tables are
the one layout mechanism nearly every email client (including Outlook)
renders identically, which is why "bulletproof" email HTML is table-based
by convention. (A prior iteration of this file avoided tables specifically
because of a column-collapse bug — but that bug was in Buttondown's own
draft-rendering pipeline, not tables in general; it doesn't apply here.)
"""
import os
from datetime import datetime

from build_site import ROOT
from buttondown_client import upload_image

# Real, public URLs — these images live in the site's own assets/ folder,
# so they resolve correctly inside an actual email sent to real inboxes
# (unlike design-tool preview URLs, which only work inside that tool).
ASSET_BASE = "https://cryptoplayback.com/assets"

# The one width every section is capped at, so nothing (masthead, ticker,
# stories, footer) can end up wider than any other section. Previously only
# the masthead/disclaimer images had an explicit max-width — everything else
# just filled whatever container Buttondown's own template happened to give
# it, which only looked consistent by coincidence.
CONTENT_WIDTH = 740

# Sampled directly from the masthead artwork (black background, gold wordmark)
# so the surrounding chrome matches it exactly rather than an eyeballed guess.
BLACK = "#000000"
GOLD = "#C9974F"
# The exact color of the "P" in "PLAYBACK" — a deeper, more muted bronze than
# the general GOLD sample above, used only where explicitly requested.
PLAYBACK_P_GOLD = "#936038"


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
    # A real <img>, not a CSS background-image div. The background-image
    # approach was a Buttondown-specific workaround (their dashboard treated a
    # standalone <img> as a "hero image" with a reserved caption slot) — but
    # real inboxes (Gmail web, Gmail/Apple Mail apps) don't reliably render
    # CSS background-image on a div at all, which is why the masthead showed
    # up as a blank black rectangle in live testing. A plain <img> is the
    # universally-supported way to show an image in email.
    return (
        f'<img src="{ASSET_BASE}/header-a.png" alt="The Crypto Playback" '
        f'width="{CONTENT_WIDTH}" style="width:100%;max-width:{CONTENT_WIDTH}px;'
        f'height:auto;display:block;margin:10px auto 0;border:0;">'
    )


def ticker_bar_email_html(prices, date_abbrev):
    """Matches the approved design exactly: Top 5 Market tab with the arrow
    pointing into a single evenly-spaced row of all 5 prices, caption under
    the tab, a separate news-date pill, and a share/subscribe row.

    Built with tables, not flexbox. Real inboxes silently ignore flex-wrap
    and the `gap` property (confirmed in live Gmail/Apple Mail testing — the
    price grid collapsed onto one unspaced line), so every alignment here is
    done with table cells and padding instead, which every major email
    client renders identically."""

    def chip(c):
        arrow_color = "#8FBF5C" if c["change_24h"] >= 0 else "#E8837A"
        return (f'<span style="color:#FBF9F5; font-family:Arial,sans-serif; font-size:14px; white-space:nowrap;">'
                f'{c["symbol"]} ${c["price"]:,.2f} <span style="color:{arrow_color};">({c["change_24h"]:+.1f}%)</span></span>')

    # Both price rows as <tr>s of ONE table, not two separate <table>s. Two
    # separate tables never truly share column widths — even with matching
    # width hints, each computes its own layout independently, so the
    # shorter row (XRP/SOL) came out narrower than the row above it
    # (BTC/ETH/BNB) and the columns didn't line up. One shared table forces
    # both rows onto the same column grid.
    col_widths = [190, 180, 0]

    def price_row(chips, padding_bottom=0):
        cells = "".join(
            f'<td style="padding:0 20px {padding_bottom}px 0; width:{col_widths[i]}px;">{chip(c)}</td>'
            for i, c in enumerate(chips)
        )
        if len(chips) < len(col_widths):
            cells += f'<td style="width:{col_widths[len(chips)]}px;"></td>'
        return f"<tr>{cells}</tr>"

    prices_html = (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
        f'{price_row(prices[:3], padding_bottom=9)}{price_row(prices[3:])}</table>'
    )

    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BLACK};">
  <tr>
    <td style="padding:28px 20px 18px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
        <td valign="top">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
            <td style="background:{PLAYBACK_P_GOLD};color:#FBF9F5;font-family:Arial,sans-serif;font-weight:bold;font-size:14px;padding:10px 12px;white-space:nowrap;">Top 5 Market</td>
            <td style="width:0; padding:0; line-height:0; font-size:0;">
              <div style="width:0;height:0;border-top:19px solid transparent;border-bottom:19px solid transparent;border-left:14px solid {PLAYBACK_P_GOLD};">&nbsp;</div>
            </td>
          </tr></table>
          <div style="color:#FBF9F5;font-weight:bold;font-family:Arial,sans-serif;font-size:12px;margin-top:8px;line-height:1.3;">prices as of 6AM (cst)<br>on printed date</div>
        </td>
        <td style="width:44px; font-size:0; line-height:0;">&nbsp;</td>
        <td valign="middle">{prices_html}</td>
      </tr></table>
    </td>
  </tr>
</table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BLACK};"><tr>
  <td style="padding:2px 20px 8px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="padding:0; font-size:0; line-height:0;"><div style="height:1px; background:{GOLD}; font-size:0; line-height:0;">&nbsp;</div></td>
      <td style="width:24px; text-align:center; color:{GOLD}; font-size:11px;">&#9670;</td>
      <td style="padding:0; font-size:0; line-height:0;"><div style="height:1px; background:{GOLD}; font-size:0; line-height:0;">&nbsp;</div></td>
    </tr></table>
  </td>
</tr></table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BLACK};"><tr>
  <td style="padding:10px 20px; text-align:center; font-family:Arial,sans-serif; font-size:15px; color:#FBF9F5;">TOP NEWS: <em style="color:{PLAYBACK_P_GOLD};">{date_abbrev}</em></td>
</tr></table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BLACK};"><tr>
  <td style="padding:12px 20px; text-align:center; white-space:nowrap;">
    <span style="font-family:Georgia,serif; font-style:italic; font-size:12px; color:#FBF9F5; opacity:0.75;">Enjoying this? Share it with a friend &rarr;</span>
    &nbsp;&nbsp;
    <span style="font-family:Arial,sans-serif; font-size:16px; font-weight:bold; color:#FBF9F5;">SUBSCRIBE HERE</span>
    &nbsp;&nbsp;
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="display:inline-table; vertical-align:middle;"><tr>
      <td width="30" height="30" align="center" valign="middle" style="background:{PLAYBACK_P_GOLD}; border-radius:50%;"><a href="#" style="text-decoration:none;"><img src="{ASSET_BASE}/mail-icon-glyph.png" width="17" height="12" alt="" style="display:block; border:0;"></a></td>
    </tr></table>
    &nbsp;
    <a href="https://x.com/cryptoplayback" style="display:inline-block; vertical-align:middle; width:27px; height:27px; line-height:27px; border-radius:50%; background:#4A90D9; color:#FBF9F5; text-align:center; font-size:13px; text-decoration:none;">X</a>
  </td>
</tr></table>"""


def sentiment_to_email_html(fng, mover, gauge_src):
    """Single combined box (Fear & Greed + Biggest Mover on one line,
    separated by a divider) inside a light-grey band — matches the approved
    design.

    Built with a table row, not a flex row. `position:relative;left:Npx` was
    being used to fine-tune spacing between elements — real inboxes ignore
    CSS `position` entirely, which is exactly why the XRP pill rendered
    outside the bordered box in live testing (the browser preview honored
    the offset, real inboxes didn't, so the box's own width calculation and
    the pill's rendered position stopped matching). Every one of those nudges
    is reproduced here as ordinary table-cell padding instead, which has no
    such gap between "renders in a browser" and "renders in an inbox"."""
    fng_color = "#E24C4C" if fng["value"] <= 45 else ("#256B32" if fng["value"] >= 55 else "#8A7F5C")
    mover_up = mover["change_24h"] >= 0
    mover_color = "#256B32" if mover_up else "#E24C4C"
    mover_sign = "+" if mover_up else ""
    # Two independent halves (each pinned to its own edge of the box), not one
    # auto-centered row. A single centered row couples both sides together —
    # any change to make the Fear & Greed side sit further left also drags
    # the Biggest Mover side left by the same amount, which is exactly what
    # kept moving the "already correct" pill when only the left side needed
    # to change. Splitting into two 50%-wide, edge-anchored halves lets the
    # left side move on its own without touching the right side's position.
    return f"""<div style="background:#F1EEE7; padding:18px 18px; border:3px solid {PLAYBACK_P_GOLD};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:rgba(255,255,255,0.06); border:1.5px solid {GOLD}; border-radius:6px;">
    <tr>
      <td width="50%" style="padding:16px 8px 16px 16px;" align="left" valign="middle">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="padding-right:9px;" valign="middle"><img src="{gauge_src}" width="46" height="29" style="display:block;" alt="Fear and Greed gauge"></td>
          <td style="padding-right:22px;" valign="middle">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
              <tr><td align="center" style="font-family:Arial,sans-serif; font-weight:bold; font-size:14px; color:#7D502D; line-height:1.15; white-space:nowrap;">FEAR &amp; GREED</td></tr>
              <tr><td align="center" style="font-family:Arial,sans-serif; font-weight:bold; font-size:14px; letter-spacing:0.04em; color:#7D502D; line-height:1.15;">INDEX</td></tr>
            </table>
          </td>
          <td style="padding-right:4px; white-space:nowrap;" valign="middle"><span style="font-family:Arial,sans-serif; font-weight:bold; font-size:25px; color:{fng_color};">{fng['value']}</span></td>
          <td style="white-space:nowrap;" valign="middle"><span style="font-size:14px; color:{fng_color};">{fng['classification']}</span></td>
        </tr></table>
      </td>
      <td width="1" style="padding:0 15px;" valign="middle"><div style="width:1.5px; height:36px; background:{GOLD}; font-size:0; line-height:0;">&nbsp;</div></td>
      <td width="50%" style="padding:16px 16px 16px 8px;" align="left" valign="middle">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="padding-right:20px; white-space:nowrap;" valign="middle"><span style="font-family:Arial,sans-serif; font-weight:bold; font-size:14px; line-height:14px; color:#7D502D;">BIGGEST MOVER</span></td>
          <td valign="middle">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="background:rgba(201,151,79,0.14); border:1px solid rgba(201,151,79,0.45); border-radius:20px;"><tr>
              <td style="padding:4px 14px; white-space:nowrap;">
                <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:21px; color:{mover_color};">{mover['symbol']}</span>
                <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:21px; color:{mover_color}; margin-left:6px;">{mover_sign}{mover['change_24h']:.1f}%</span>
              </td>
            </tr></table>
          </td>
        </tr></table>
      </td>
    </tr>
  </table>
</div>"""


def release_row_email_html(date_display, issue_number, tag):
    label = "DAILY ISSUE" if tag == "Daily" else "WEEKLY ISSUE"
    return f"""<div style="margin:20px 20px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#F1EEE7; border-radius:4px; box-shadow:0 2px 5px rgba(23,21,18,0.18);">
  <tr>
    <td style="padding:10px 16px; font-family:Arial,sans-serif; font-size:12px; color:#666666;" valign="middle">Release date: {date_display}</td>
    <td style="padding:10px 16px; text-align:right; white-space:nowrap;" valign="middle">
      <span style="display:inline-block;font-family:Arial,sans-serif;font-weight:bold;font-size:11px;letter-spacing:0.04em;color:#FBF9F5;background:#268CCA;padding:4px 10px;border-radius:3px;">{label}</span>
      <span style="font-family:Arial,sans-serif; font-size:12px; color:#666666; margin-left:20px;">Issue #{issue_number}</span>
    </td>
  </tr>
</table>
</div>"""


def issue_title_block_email_html(title):
    # !important on the h1 margin: Buttondown's renderer applies its own default
    # vertical rhythm to heading tags specifically, overriding a plain inline
    # margin — this fights that back to keep the title tight to the release
    # row above it instead of leaving a large gap.
    return f"""<div style="margin:20px 20px 4px; text-align:center;">
<span style="display:inline-block; font-family:Arial,sans-serif; font-weight:bold; font-size:12px; letter-spacing:0.14em; color:{GOLD}; background:#171512; padding:8px 22px; border-radius:8px 8px 0 0;">SNAPSHOT</span>
<div style="background:#F1EEE7; border:2px solid {PLAYBACK_P_GOLD}; border-radius:0 8px 8px 8px; padding:4px; margin-top:-1px; box-shadow:0 4px 10px rgba(23,21,18,0.2);">
  <div style="border:1px solid {GOLD}; border-radius:4px; padding:18px 22px;">
    <h1 style="font-family:Arial,sans-serif;font-weight:bold;font-style:italic;font-size:26px;color:#171512;margin:0 !important;line-height:1.15;">{title}</h1>
  </div>
</div>
</div>"""


def top_story_to_email_html(intro):
    # Table-based, not flex — `align-items:center` was silently ignored by
    # real inboxes, so the tilted "TOP STORY" label sat at the top of the box
    # instead of centered. `valign="middle"` on a table cell is the one
    # vertical-centering technique that's reliable across clients.
    #
    # The tilted label itself is a pre-rendered PNG, not CSS `transform`.
    # Live testing showed `transform` renders in Apple Mail but is stripped
    # by Gmail — a real image's pixels are identical everywhere, since there's
    # no CSS for the client to selectively support.
    return f"""<div style="margin:20px 20px 32px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#F1EEE7; border-radius:8px; border:2px solid #268CCA; box-shadow:0 4px 10px rgba(23,21,18,0.2);">
  <tr>
    <td width="56" style="background:#268CCA; border-radius:6px 0 0 6px;" align="center" valign="middle">
      <img src="{ASSET_BASE}/top-story-label.png" width="44" alt="TOP STORY" style="display:block; width:44px; height:auto; border:0;">
    </td>
    <td style="padding:24px 28px 24px 24px; font-family:Arial,Helvetica,sans-serif; font-weight:600; font-size:24px; line-height:1.4; color:#171512;" valign="middle">{intro}</td>
  </tr>
</table>
</div>"""


def footer_email_html():
    year = datetime.now().year
    # A real <img>, same reasoning as the masthead — see the note there.
    disclaimer_html = (
        f'<img src="{ASSET_BASE}/disclaimer.png" alt="Legal disclaimer: The Crypto Playback is not financial advice." '
        f'width="{CONTENT_WIDTH}" style="width:100%;max-width:{CONTENT_WIDTH}px;'
        f'height:auto;display:block;margin-top:24px;border:0;">'
    )
    return f"""{disclaimer_html}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BLACK};"><tr>
  <td style="padding:14px 20px; color:#FBF9F5;font-family:Arial,sans-serif;font-size:12px;" valign="bottom">&copy; {year} The Crypto Playback &middot; info@cryptoplayback.com</td>
  <td style="padding:14px 20px; text-align:right; white-space:nowrap;" valign="bottom">
    <img src='{ASSET_BASE}/mascot-icon.png' width='54' height='50' style='width:54px;height:50px;display:inline-block;vertical-align:bottom;border:0;' alt=''>
    <img src='{ASSET_BASE}/logo-white.png' width='90' height='43' style='width:90px;height:auto;display:inline-block;vertical-align:bottom;margin-left:8px;border:0;'>
  </td>
</tr></table>
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
        release_row_email_html(date_display, issue_number, tag),
        issue_title_block_email_html(issue_title),
        top_story_to_email_html(intro),
    ]
    for s in stories:
        # Every other section (release date, top story, issue headline) has a
        # 20px side inset — story content had none, so it bled to the true
        # edges while everything above it was inset, throwing off the whole
        # column's left/right alignment. Wrapping it in the same 20px margin
        # keeps one consistent content column edge-to-edge down the email,
        # and using a div instead of <hr> for the divider avoids Buttondown
        # rendering it as a short fixed-width "divider" UI element instead of
        # a full-width rule (same class of issue as the hero-image caption
        # slot — a semantic tag getting special block treatment).
        img_html = f"<p><img src='{s['image_url']}' style='max-width:100%; display:block;'></p>" if s.get("image_url") else ""
        parts.append(
            f"<div style='margin:0 20px;'>"
            f"<h3 style='font-family:Arial,Helvetica,sans-serif;font-weight:bold;font-size:20px;color:#171512;margin:0 0 10px;'>{s['headline']}</h3>{img_html}{s['body']}"
            f"<p><a href='{s['source_url']}' style='color:{GOLD};font-weight:bold;text-decoration:none;'>Read more at {s['source_title']} &rarr;</a></p>"
            f"<div style='height:1px; background:#DDD9CE; margin:16px 0;'></div>"
            f"</div>"
        )
    parts.append(footer_email_html())
    body_html = "\n".join(parts[1:])  # everything except the masthead image
    # Explicit max-width + centering here, matching the masthead/disclaimer's
    # own cap, so ticker/sentiment/stories/footer can't end up a different
    # width than those two images regardless of what width Buttondown's own
    # template happens to give unconstrained content.
    wrapped = (
        f"<div style='max-width:{CONTENT_WIDTH}px;margin:0 auto;"
        f"font-family:Arial,Helvetica,sans-serif;color:#171512;font-size:15px;line-height:1.5;'>{body_html}</div>"
    )
    # A full, minimal HTML document, not stray <meta> tags dropped in front
    # of the content. The color-scheme meta tags lock the email to light mode
    # (without them, iOS Mail's automatic dark mode selectively dims plain
    # white/off-white text — the ticker prices, the "prices as of..."
    # caption — while leaving gold/bordered elements alone; it's guessing
    # which colors need "fixing" and guessing wrong). Floating meta tags
    # with no <html>/<head>/<body> around them left the receiving side to
    # auto-wrap the content in its own default template, which is what
    # introduced a white gap above the masthead — an explicit body with no
    # margin closes that gap (background stays the story sections' own
    # implicit off-white, since those rely on inheriting it rather than
    # declaring it themselves — the masthead/ticker/footer's black is all
    # explicit on their own elements regardless of what's behind them).
    # Gmail strips full document structure and keeps only the inner content
    # regardless, so this has no effect there — the desktop/Gmail version
    # is unchanged.
    html_doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
</head>
<body style="margin:0; padding:0; background:#FBF9F5;">
{parts[0]}
{wrapped}
</body>
</html>"""
    return html_doc
