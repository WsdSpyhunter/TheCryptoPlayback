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
CONTENT_WIDTH = 900

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


def preheader_email_html():
    """A small text banner above the masthead image. Not decorative filler —
    on Apple Mail with device Dark Mode on, the `color-scheme: light` meta
    tag (needed to stop the ticker's white text from being dimmed) triggers
    a native white gap before the first large image, regardless of what
    precedes it or how that image is sized (confirmed by testing both).
    Since the gap can't be removed from our side, this turns the space in
    front of it into an intentional, branded line instead of dead space."""
    return (
        f'<div style="background:{BLACK}; padding:14px 20px; text-align:center;">'
        f'<span style="font-family:Georgia,serif; font-weight:bold; font-size:16px; '
        f'letter-spacing:0.15em; color:#FBF9F5;">THE CRYPTO '
        f'<span style="color:{GOLD};">PLAYBACK</span></span></div>'
    )


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
    """Matches the approved design exactly: Top 6 Market tab with the arrow
    pointing into a single evenly-spaced row of all 6 prices, caption under
    the tab, a separate news-date pill, and a share/subscribe row.

    Built with tables, not flexbox. Real inboxes silently ignore flex-wrap
    and the `gap` property (confirmed in live Gmail/Apple Mail testing — the
    price grid collapsed onto one unspaced line), so every alignment here is
    done with table cells and padding instead, which every major email
    client renders identically."""

    def chip(c, size=14):
        arrow_color = "#8FBF5C" if c["change_24h"] >= 0 else "#E8837A"
        return (f'<span style="color:#FBF9F5; font-family:Arial,sans-serif; font-size:{size}px; white-space:nowrap;">'
                f'{c["symbol"]} ${c["price"]:,.2f} <span style="color:{arrow_color};">({c["change_24h"]:+.1f}%)</span></span>')

    # Both price rows as <tr>s of ONE table, not two separate <table>s. Two
    # separate tables never truly share column widths — even with matching
    # width hints, each computes its own layout independently, so the
    # shorter row (XRP/SOL) came out narrower than the row above it
    # (BTC/ETH/BNB) and the columns didn't line up. One shared table forces
    # both rows onto the same column grid.
    col_widths = [190, 180, 180]

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

    tab_html = (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td style="background:{PLAYBACK_P_GOLD};color:#FBF9F5;font-family:Arial,sans-serif;font-weight:bold;font-size:14px;padding:10px 12px;white-space:nowrap;">Top 6 Market</td>'
        f'</tr></table>'
    )

    # Mobile: a centered pill instead of the left-aligned tab+arrow - the
    # arrow was pointing at a price row that no longer sits beside it once
    # the grid stacks underneath instead, so a plain centered badge (same
    # gold/brass fill, same shape family as the XRP move pill) reads better
    # above a stacked layout. Pure styling around a static label - doesn't
    # touch or depend on the price data, so changing prices/dates daily or
    # weekly can't affect it.
    tab_html_mobile = (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="display:inline-table;"><tr>'
        f'<td style="background:{PLAYBACK_P_GOLD};color:#FBF9F5;font-family:Arial,sans-serif;font-weight:bold;font-size:14px;padding:10px 26px;border-radius:20px;white-space:nowrap;">Top 6 Market</td>'
        f'</tr></table>'
    )

    # Mobile can't fit 3 nowrap price chips across a phone-width row (this was
    # already borderline on desktop's much wider column) - a 2-per-row grid
    # (three full pairs) gives each chip roughly half the row instead of a
    # third, which fits comfortably at a normal, readable size.
    def mobile_price_cell(c, pad):
        return f'<td width="50%" style="padding:{pad};">{chip(c, size=15)}</td>'

    mobile_rows = [prices[0:2], prices[2:4], prices[4:6]]
    mobile_prices_html = "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"table-layout:fixed;\">"
    for i, pair in enumerate(mobile_rows):
        pad_bottom = "0" if i == len(mobile_rows) - 1 else "14px"
        cells = "".join(
            mobile_price_cell(c, f"0 8px {pad_bottom} 0" if j == 0 else f"0 0 {pad_bottom} 8px")
            for j, c in enumerate(pair)
        )
        if len(pair) < 2:
            cells += '<td width="50%"></td>'
        mobile_prices_html += f"<tr>{cells}</tr>"
    mobile_prices_html += "</table>"

    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="tbar-desktop" style="background:{BLACK}; display:table;">
  <tr>
    <td style="padding:28px 20px 18px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
        <td valign="top">
          {tab_html}
          <div style="color:#FBF9F5;font-weight:bold;font-family:Arial,sans-serif;font-size:12px;margin-top:8px;line-height:1.3;white-space:nowrap;">prices as of 6AM&nbsp;(cst)<br>on printed date</div>
        </td>
        <td style="width:44px; font-size:0; line-height:0;">&nbsp;</td>
        <td valign="middle">{prices_html}</td>
      </tr></table>
    </td>
  </tr>
</table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="tbar-mobile" style="background:{BLACK}; display:none;">
  <tr><td style="padding:24px 20px 4px; text-align:center;">
    {tab_html_mobile}
    <div style="color:#FBF9F5;font-weight:bold;font-family:Arial,sans-serif;font-size:12px;margin-top:10px;line-height:1.3;">prices as of 6AM (cst) on printed date</div>
  </td></tr>
  <tr><td style="padding:14px 20px 18px;">{mobile_prices_html}</td></tr>
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
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="subscribe-desktop" style="background:{BLACK}; display:table;"><tr>
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
</tr></table>
<div class="subscribe-mobile" style="background:{BLACK}; padding:14px 20px; text-align:center; display:none;">
    <div style="font-family:Georgia,serif; font-style:italic; font-size:12px; color:#FBF9F5; opacity:0.75;">Enjoying this? Share it with a friend &rarr;</div>
    <div style="margin-top:10px;">
      <span style="font-family:Arial,sans-serif; font-size:16px; font-weight:bold; color:#FBF9F5; vertical-align:middle;">SUBSCRIBE HERE</span>
      &nbsp;&nbsp;
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="display:inline-table; vertical-align:middle;"><tr>
        <td width="30" height="30" align="center" valign="middle" style="background:{PLAYBACK_P_GOLD}; border-radius:50%;"><a href="#" style="text-decoration:none;"><img src="{ASSET_BASE}/mail-icon-glyph.png" width="17" height="12" alt="" style="display:block; border:0;"></a></td>
      </tr></table>
      &nbsp;
      <a href="https://x.com/cryptoplayback" style="display:inline-block; vertical-align:middle; width:27px; height:27px; line-height:27px; border-radius:50%; background:#4A90D9; color:#FBF9F5; text-align:center; font-size:13px; text-decoration:none;">X</a>
    </div>
</div>"""


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
    desktop_box = f"""<div class="fng-desktop" style="background:#F1EEE7; padding:18px 18px; border:6px solid {PLAYBACK_P_GOLD}; display:block;">
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

    # Mobile: keeps the same side-by-side, two-halves-with-a-divider shape
    # (per explicit instruction not to stack Fear & Greed under Biggest
    # Mover) but each half becomes two stacked lines internally - icon+label
    # on one line, value+detail on the next - so there's enough width per
    # half to use meaningfully larger text/icon than a single nowrap row
    # could ever fit on a phone screen.
    mobile_box = f"""<div class="fng-mobile" style="background:#F1EEE7; padding:22px 16px; border:3px solid {PLAYBACK_P_GOLD}; display:none;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:rgba(255,255,255,0.06); border:1.5px solid {GOLD}; border-radius:6px;">
    <tr>
      <td width="50%" style="padding:18px 10px 18px 14px;" align="left" valign="top">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="padding-right:8px;" valign="middle"><img src="{gauge_src}" width="58" height="37" style="display:block;" alt="Fear and Greed gauge"></td>
          <td valign="middle" style="font-family:Arial,sans-serif; font-weight:bold; font-size:14px; color:#7D502D; line-height:1.2;">FEAR &amp; GREED INDEX</td>
        </tr></table>
        <div style="margin-top:10px; white-space:nowrap;">
          <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:28px; color:{fng_color};">{fng['value']}</span>
          <span style="font-size:14px; color:{fng_color};"> {fng['classification']}</span>
        </div>
      </td>
      <td width="1" style="padding:0 10px;" valign="middle"><div style="width:1.5px; height:64px; background:{GOLD}; font-size:0; line-height:0;">&nbsp;</div></td>
      <td width="50%" style="padding:18px 14px 18px 10px;" align="center" valign="top">
        <div style="font-family:Arial,sans-serif; font-weight:bold; font-size:14px; color:#7D502D; text-align:center;">BIGGEST MOVER</div>
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:10px auto 0; background:rgba(201,151,79,0.14); border:1px solid rgba(201,151,79,0.45); border-radius:20px;"><tr>
          <td style="padding:5px 14px; white-space:nowrap;">
            <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:22px; color:{mover_color};">{mover['symbol']}</span>
            <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:22px; color:{mover_color}; margin-left:6px;">{mover_sign}{mover['change_24h']:.1f}%</span>
          </td>
        </tr></table>
      </td>
    </tr>
  </table>
</div>"""

    return desktop_box + mobile_box


def release_row_email_html(date_display, issue_number, tag):
    label = "DAILY ISSUE" if tag == "Daily" else "WEEKLY ISSUE"
    return f"""<div style="margin:20px 20px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#F1EEE7; border-radius:4px; box-shadow:0 2px 5px rgba(23,21,18,0.18);">
  <tr>
    <td style="padding:10px 16px; font-family:Arial,sans-serif; font-size:14px; color:{PLAYBACK_P_GOLD};" valign="middle">Release date: {date_display}</td>
    <td style="padding:10px 16px; text-align:right; white-space:nowrap;" valign="middle">
      <span style="display:inline-block;font-family:Arial,sans-serif;font-weight:bold;font-size:11px;letter-spacing:0.04em;color:#FBF9F5;background:#268CCA;padding:4px 10px;border-radius:3px;">{label}</span>
      <span style="font-family:Arial,sans-serif; font-size:14px; color:{PLAYBACK_P_GOLD}; margin-left:20px;">Issue #{issue_number}</span>
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
<span class="notable-tab" style="display:inline-block; font-family:Arial,sans-serif; font-weight:bold; font-size:48px; line-height:1.15; letter-spacing:0.14em; color:{GOLD}; background:#171512; padding:10px 38px; border-radius:8px 8px 0 0;">NOTA<img class="notable-b" src="{ASSET_BASE}/email-notable-b.png" height="45" alt="B" style="height:45px; width:auto; vertical-align:-5px; margin:0 4px; border:0;">LE</span>
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
    <td class="ts-label-cell" width="112" style="background:#268CCA; border-radius:6px 0 0 6px;" align="center" valign="middle">
      <img class="ts-label" src="{ASSET_BASE}/top-story-label-2x.png" width="88" alt="TOP STORY" style="display:block; width:88px; height:auto; border:0;">
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
    <img src="{ASSET_BASE}/mascot-icon.png" width="44" height="55" style="width:44px;height:55px;display:inline-block;vertical-align:bottom;border:0;" alt="The Crypto Playback">
    <img src="{ASSET_BASE}/logo-white.png" width="90" height="43" style="width:90px;height:auto;display:inline-block;vertical-align:bottom;margin-left:8px;border:0;">
  </td>
</tr></table>
<p style="text-align:center;font-family:Arial,sans-serif;font-size:11px;color:#666666;padding:10px 0;margin:0;background:#FBF9F5;">
  <a href="{{{{ unsubscribe_url }}}}" style="color:#666666;">Unsubscribe from The Crypto Playback</a>
</p>"""


def stories_to_plain_email_html_v1(issue_title, intro, stories, ticker_prices, fng, mover, tag, date_display, date_abbrev, issue_number, gauge_src):
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
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<style>
@media only screen and (max-width: 600px) {{
  .tbar-desktop {{ display:none !important; }}
  .tbar-mobile {{ display:block !important; }}
  .fng-desktop {{ display:none !important; }}
  .fng-mobile {{ display:block !important; }}
  .subscribe-desktop {{ display:none !important; }}
  .subscribe-mobile {{ display:block !important; }}
}}
</style>
</head>
<body style="margin:0; padding:0; background:#FBF9F5;">
{preheader_email_html()}
{parts[0]}
{wrapped}
</body>
</html>"""
    return html_doc


# =====================================================================
# Newsletter Version 2 — new sections + assembler
# =====================================================================
# Website-style full-bleed bands (Market Snapshot, Signal Confluence,
# Here's A Story You Missed) between the ticker and the stories. Same
# table-based, inline-styled approach as everything above. Gradients always
# carry a solid `background-color` fallback first, because older desktop
# Outlook ignores `background-image: linear-gradient(...)` entirely.
V2_PAPER = "#FBF9F5"
V2_INK = "#171512"
V2_SNAP_BAND = "#9C9892"
V2_SNAP_CARD = "#EDE9E2"
V2_DARK_BAND = "#121212"
V2_DARK_CARD = "#1B1B1B"
V2_GREEN = "#8FBF5C"
V2_RED = "#E24C4C"
V2_GOLD_GRAD = ("#B68047", "linear-gradient(135deg, #D9A857, #936038)")
V2_GREEN_GRAD = ("#76A04A", "linear-gradient(135deg, #8FBF5C, #5D7C3C)")


def _cap_email_html(inner):
    return (f"<div style='max-width:{CONTENT_WIDTH}px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;"
            f"color:{V2_INK};font-size:15px;line-height:1.5;'>{inner}</div>")


def _oval_email_html(label, grad, size=13, pad="10px 26px", css_class=""):
    solid, image = grad
    cls = f' class="{css_class}"' if css_class else ""
    return (f'<span{cls} style="display:inline-block; font-family:Arial,sans-serif; font-weight:bold; font-size:{size}px; '
            f'letter-spacing:0.1em; text-transform:uppercase; color:#ffffff; background-color:{solid}; '
            f'background-image:{image}; padding:{pad}; border-radius:30px; '
            f'box-shadow:0 4px 14px rgba(0,0,0,0.25);">{label}</span>')


def news_highlights_header_email_html():
    """Bordered divider that announces the news section is starting."""
    return f"""<div style="padding:30px 20px 12px; text-align:center;">
  <table role="presentation" align="center" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto; border:3px solid {V2_INK}; background-color:#2E2E2E;">
    <tr><td style="padding:5px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid {GOLD};">
        <tr><td class="news-hl" align="center" style="padding:16px 12px; font-family:Arial,Helvetica,sans-serif; font-weight:bold; font-size:26px; letter-spacing:6px; color:#FFFFFF;">NEWS HIGHLIGHTS</td></tr>
      </table>
    </td></tr>
  </table>
</div>"""


def market_snapshot_email_html(overview):
    """Gray full-bleed band: bull / Market Snapshot card / bear. The mascot
    that doesn't match the market's lean carries a pre-rendered red X (a PNG,
    since email can't overlay one element on another reliably); the mascots
    hide on phones, where the card needs the full width."""
    lean = overview["market_lean"]
    bull_img = "email-bull-x.png" if lean == "bearish" else "email-bull.png"
    bear_img = "email-bear-x.png" if lean == "bullish" else "email-bear.png"
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{V2_SNAP_BAND};">
  <tr><td class="band-pad" style="padding:34px 12px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:1100px; width:100%; margin:0 auto; table-layout:fixed;">
      <tr>
        <td class="snap-side" width="190" valign="middle" align="left" style="width:190px;"><img src="{ASSET_BASE}/{bull_img}" width="180" alt="Bull" style="display:block; width:180px; height:auto; border:0;"></td>
        <td valign="middle" style="padding:0 16px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{V2_SNAP_CARD}; border-radius:20px; box-shadow:0 10px 34px rgba(23,21,18,0.12);">
            <tr><td class="snap-card" style="padding:26px 44px; text-align:center;">
              {_oval_email_html("Market Snapshot", V2_GREEN_GRAD, 26, "16px 42px", "snap-badge")}
              <div style="font-family:Arial,sans-serif; font-size:13.5px; color:#575550; margin:16px 0 14px;">Updated {overview["updated"]} &middot; Based on {overview["total_count"]} market indicators</div>
              <p class="snap-text" style="font-family:Arial,sans-serif; font-size:19.5px; font-weight:bold; line-height:1.55; color:{V2_INK}; margin:0; text-align:center;">{overview["snapshot_text"]}</p>
            </td></tr>
          </table>
        </td>
        <td class="snap-side" width="190" valign="middle" align="right" style="width:190px;"><img src="{ASSET_BASE}/{bear_img}" width="180" alt="Bear" style="display:block; width:180px; height:auto; border:0;"></td>
      </tr>
    </table>
  </td></tr>
</table>"""


def signal_confluence_email_html(overview):
    """Black full-bleed band: score box + every indicator, 4 across (2 across
    on phones), then the one-line interpretation."""
    def cell(name, pos, value):
        dot = V2_GREEN if pos else V2_RED
        return (f'<td class="conf-cell" valign="top" style="padding:9px 28px; font-family:Arial,sans-serif; line-height:1.35; text-align:left;">'
                f'<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{dot};margin-right:7px;vertical-align:middle;">&nbsp;</span>'
                f'<span class="conf-name" style="font-weight:bold; font-size:18px; color:{V2_PAPER}; vertical-align:middle;">{name}</span><br>'
                f'<span class="conf-val" style="color:#9D9C99; padding-left:19px; font-size:15px;">{value}</span></td>')
    items = overview["confluence_items"]
    grid = ""
    for i in range(0, len(items), 4):
        chunk = items[i:i + 4]
        cells = "".join(cell(*it) for it in chunk) + "<td></td>" * (4 - len(chunk))
        grid += f'<tr class="conf-row">{cells}</tr>'
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{V2_DARK_BAND};">
  <tr><td class="band-pad" style="padding:42px 12px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:1100px; margin:0 auto; background:{V2_DARK_CARD}; border:1px solid rgba(255,255,255,0.08); border-radius:18px;">
      <tr><td class="conf-card" style="padding:30px 32px; text-align:center;">
        {_oval_email_html("Signal Confluence", V2_GOLD_GRAD, 17)}
        <div style="font-family:Arial,sans-serif; font-size:14.5px; color:#8A8A88; margin:12px 0 20px;">Updated {overview["updated"]}</div>
        <div style="margin:0 0 56px;"><div style="display:inline-block; background:#262626; border:2px solid {GOLD}; border-radius:14px; padding:14px 44px 16px; box-shadow:0 10px 26px rgba(0,0,0,0.65), 0 2px 6px rgba(0,0,0,0.5);">
          <div><span style="font-family:Arial,sans-serif; font-weight:bold; font-size:43px; color:{V2_PAPER};">{overview["positive_count"]}<span style="font-size:24px; color:#8A8A88; font-weight:normal;">/{overview["total_count"]}</span></span></div>
          <div style="font-family:Arial,sans-serif; font-size:18px; color:#A1A09E;">signals positive</div>
        </div></div>
        <table class="conf-table" role="presentation" align="center" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;">{grid}</table>
        <div style="font-family:Arial,sans-serif; font-size:16px; color:#A1A09E; margin-top:56px;">{overview["interpretation"]}</div>
      </td></tr>
    </table>
  </td></tr>
</table>"""


def story_you_missed_email_html(missed):
    """Gray band + dark card with the spy badge. `missed` is a dict with
    headline, body (plain text or <p> HTML), source_title, source_url."""
    # Plain text in a div, never a <p>: the mail platform styles <p> with its
    # own dark text color, which made this unreadable on the dark card.
    import re as _re
    body = _re.sub(r"</p>\s*<p[^>]*>", "<br><br>", missed["body"])
    body = _re.sub(r"</?p[^>]*>", "", body).strip()
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{V2_SNAP_BAND};">
  <tr><td class="band-pad" style="padding:34px 12px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:800px; margin:0 auto; background:{V2_DARK_CARD}; border:1px solid rgba(255,255,255,0.08); border-radius:18px; box-shadow:0 10px 34px rgba(23,21,18,0.18);">
      <tr><td class="missed-card" style="padding:30px 32px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
          <td class="missed-icon-cell" width="25%" align="left" valign="middle"><img class="missed-icon" src="{ASSET_BASE}/email-spy-badge.png" width="72" height="72" alt="" style="display:block; width:72px; height:72px; border:0;"></td>
          <td align="center" valign="middle">{_oval_email_html("Here's A Story You Missed", V2_GOLD_GRAD, 17, css_class="missed-badge")}</td>
          <td class="missed-spacer" width="25%">&nbsp;</td>
        </tr></table>
        <div style="font-family:Arial,Helvetica,sans-serif; font-weight:bold; font-size:20px; line-height:1.35; color:{V2_PAPER}; margin:20px 0 10px;">{missed["headline"]}</div>
        <div style="font-family:Arial,Helvetica,sans-serif; font-size:16px; line-height:1.55; color:#BCBBB8; margin-bottom:12px;">{body}</div>
        <a href="{missed["source_url"]}" style="font-family:Arial,sans-serif; font-weight:bold; font-size:14px; color:#D9A857; text-decoration:none;"><span style="color:#D9A857;">Read more at {missed["source_title"]} &rarr;</span></a>
      </td></tr>
    </table>
  </td></tr>
</table>"""


def story_blocks_email_html(stories):
    """The issue's stories: centered headline + image, 16px body, brass rule."""
    out = ""
    for s in stories:
        img_html = (f"<p style='text-align:center;'><img src='{s['image_url']}' style='max-width:100%; display:block; margin:0 auto;'></p>"
                    if s.get("image_url") else "")
        out += (
            f"<div style='margin:0 20px;'>"
            f"<h3 style='font-family:Arial,Helvetica,sans-serif;font-weight:bold;font-size:20px;color:{V2_INK};margin:0 0 10px;text-align:center;'>{s['headline']}</h3>"
            f"{img_html}<div style='font-size:16px;'>{s['body']}</div>"
            f"<p><a href='{s['source_url']}' style='color:{GOLD};font-weight:bold;text-decoration:none;'><span style='color:{GOLD};'>Read more at {s['source_title']} &rarr;</span></a></p>"
            f"<div style='height:1px; background:{PLAYBACK_P_GOLD}; margin:16px 0;'></div>"
            f"</div>"
        )
    return out


def stories_to_plain_email_html(issue_title, intro, stories, ticker_prices, tag, date_display, date_abbrev,
                                issue_number, overview, missed_story=None):
    """Newsletter Version 2 — full HTML for the email body. Order: masthead,
    ticker, release row, Market Snapshot, Signal Confluence, NEWS HIGHLIGHTS,
    Top Story, Here's A Story You Missed (when there is one), NOTABLE title,
    the stories, footer. The old Fear & Greed / Biggest Mover box is gone
    (both live in Signal Confluence now)."""
    segments = [
        _cap_email_html(ticker_bar_email_html(ticker_prices, date_abbrev)),
        _cap_email_html(release_row_email_html(date_display, issue_number, tag) + "<div style='height:20px;'></div>"),
        market_snapshot_email_html(overview),
        signal_confluence_email_html(overview),
        _cap_email_html(news_highlights_header_email_html() + top_story_to_email_html(intro)),
    ]
    if missed_story:
        segments.append(story_you_missed_email_html(missed_story))
    segments.append(_cap_email_html(issue_title_block_email_html(issue_title)))
    segments.append(_cap_email_html("<div style='padding-top:40px;'>" + story_blocks_email_html(stories) + "</div>" + footer_email_html()))
    body_html = "\n".join(segments)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<style>
@media only screen and (max-width: 600px) {{
  .tbar-desktop {{ display:none !important; }}
  .tbar-mobile {{ display:block !important; }}
  .fng-desktop {{ display:none !important; }}
  .fng-mobile {{ display:block !important; }}
  .subscribe-desktop {{ display:none !important; }}
  .subscribe-mobile {{ display:block !important; }}
  .snap-side {{ display:none !important; }}
  .snap-card {{ padding:22px 18px !important; }}
  .snap-badge {{ font-size:18px !important; padding:12px 24px !important; }}
  .snap-text {{ font-size:16px !important; }}
  .conf-card {{ padding:24px 12px !important; }}
  .conf-table {{ width:100% !important; }}
  .conf-row {{ display:block !important; }}
  .conf-cell {{ display:inline-block !important; width:50% !important; box-sizing:border-box !important; padding:9px 8px !important; }}
  .conf-name {{ font-size:15px !important; }}
  .conf-val {{ font-size:13px !important; padding-left:0 !important; display:block; margin-left:16px; }}
  .missed-card {{ padding:24px 18px !important; }}
  .missed-badge {{ font-size:13px !important; padding:9px 16px !important; }}
  .missed-icon-cell {{ width:52px !important; }}
  .missed-icon {{ width:44px !important; height:44px !important; }}
  .missed-spacer {{ display:none !important; }}
  .news-hl {{ font-size:18px !important; letter-spacing:3px !important; }}
  .notable-tab {{ font-size:28px !important; padding:8px 20px !important; }}
  .notable-b {{ height:26px !important; vertical-align:-3px !important; }}
  .ts-label-cell {{ width:64px !important; }}
  .ts-label {{ width:52px !important; }}
}}
</style>
</head>
<body style="margin:0; padding:0; background:{V2_PAPER};">
{preheader_email_html()}
{masthead_email_html()}
{body_html}
</body>
</html>"""
