# The Crypto Playback: Daily Newsletter (v2 design)

## Files
- `index.html`: the finished design. **Source of truth.** Inline styles, 720px wide.
- `assets/TCP_Header_1_2.png`: header (mascot, wordmark with the Bitcoin B, tagline, date, candlesticks). The date is baked into the image.
- `assets/TCP_newsletter_footer.png`: footer (branding, sources, disclaimer, copyright, links). Also an image.
- `reference-render.pdf`: how it should look. Match it.

## Layout
- Page: 720px wide, background `#E9E4D6`, 24px padding.
- Card: 672px wide, white, 1px border `#D9D3C3`. Section side padding is 40px.

## Colors
| Role | Hex |
|---|---|
| Navy (header, dark panels, buttons) | `#0B1F3A` |
| Navy, top bar | `#07162B` |
| Navy, dark cards | `#12294A` |
| Navy, lede box (lighter) | `#16305A` |
| Navy borders on dark | `#2C4263` |
| Brass, rules and underlines | `#B8934A` |
| Brass, on dark | `#D4B063` |
| Brass, text on light | `#8A6A1F` |
| Ivory (bands, boxes) | `#F7F4EC` |
| Page background | `#E9E4D6` |
| Light borders | `#E2DDD0` |
| Body text | `#1F2937` |
| Muted text | `#5B6472` |
| Muted text on dark | `#9FB0C8`, `#C9D2E0`, `#E4E9F1` |
| Positive | `#1E7A4C` (pill bg), `#145C39` (text), `#8FD0AC` (on dark) |
| Negative | `#B3372F` (pill bg), `#F2A29B` (on dark), card bg `#2B1C2A` |
| Neutral pill | `#4A5F82` |

## Fonts (Google Fonts)
- **IBM Plex Sans** 400/500/600: body; section titles (600, 14px, uppercase, letter-spacing .14em).
- **IBM Plex Mono** 500: prices, indicator values.
- **Libre Franklin** 600/700: story headlines (19px), lede (22px/600), big numerals (01/02/03, 70, 11/12), indicator card titles (14px uppercase), CTA heading (22px).
- **Barlow Condensed** 500/600: story kickers (14px, uppercase, .14em, `#8A6A1F`), top bar, CTA button text.

## Section order (top to bottom)
1. Top bar (navy): "Daily Issue · No. N" and "View in browser"
2. Header image
3. Top 6 Market strip (ivory): 3x2 grid, centered. Ticker symbol 14px, price 17px, change 12px
4. The Bottom Line: 3 numbered bullets
5. Market Snapshot (light ivory box): sentiment gauge (SVG), score, summary sentence
6. Notable: navy badge "A story you may have missed" with curved SVG arrow, then one story
7. Dark panel: Signal Confluence (X/12 plus a 4-column grid of 12 indicator cards plus ETF row), then What Changed
8. Alerts & Indicators: ivory header band, then a dark block with 14 cards in 2 columns (icon, title, value, status pill, detail, description, link)
9. The Top News Stories: lede in a lighter-navy shadow box, then 4 stories
10. Sponsor slot (placeholder, dashed brass border)
11. Market Structure & Policy: 4 stories
12. Week Ahead (placeholders)
13. CTA (heading plus button)
14. Footer image

## Components
- **Section title box** (Bottom Line, Market Snapshot, Notable, Alerts & Indicators): white box, 1px `#E2DDD0` border, `box-shadow: 0 4px 14px rgba(11,31,58,.16)`, icon + 14px title, sitting on a 2px navy rule.
- **Story**: 64px navy icon tile with a 3px brass bottom border and a brass line icon; kicker, headline, summary, "Why it matters:" line, "Read at X →" link.
- **Status pills**: "Positive", "Negative", "Neutral", 10.5px bold. Never rely on color alone.
- **Arrow** on the Notable badge: inline SVG, curved path out of the badge's left side, arrowhead pointing down at the story.

## Dynamic data (needs to come from a data source per issue)
- Issue number and date. The date is in the header image, so use a dateless header plus a live date line, or generate a header per day.
- Prices and % change for the top 6.
- 12 signal values, statuses and timestamp. Alerts & Indicators values (14).
- What Changed rows (indicator, previous, current).
- Stories: kicker, headline, summary, why-it-matters, source name and link.
- Notable story, Week Ahead rows, sponsor slot.
- Every value must come from one data run with one timestamp.

## Open placeholders in the design
- `[$134.4M: confirm against dashboard]`, `[queue size: confirm ...]`, `[amount: confirm $2M vs. $8M]`: figures that conflicted in the source issue.
- Week Ahead rows and the sponsor slot.

## Production notes (important)
- This HTML uses flexbox, grid, `clip-path`, box-shadow and inline SVG. Many email clients (Outlook especially) do not support these. For sending, convert to a table-based, email-safe layout (for example with MJML or React Email) and match this design visually.
- Images are blocked by default in many email clients. Add real alt text. The header and footer are single images, so also provide a text fallback.
- The footer image contains the Unsubscribe and Manage subscription text, so those links are not clickable. A sent email needs real, working unsubscribe links (required). Overlay live text links or use a footer without those baked in.
- Gauge, arrow and icons are inline SVG. Email clients often strip SVG, so export them as PNGs for email.

## Starter prompt for Claude Code
> Open `index.html` and `reference-render.pdf`. Recreate this newsletter as a template that renders from a JSON data file (fields listed in "Dynamic data"). Keep the visual design identical to `index.html` (same colors, fonts, spacing, section order). Then produce an email-safe version (table-based, inline CSS, PNG fallbacks for SVG). Do not change copy, colors or fonts unless I ask.
