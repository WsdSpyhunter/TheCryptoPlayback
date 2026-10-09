# Newsletter redesign: LOCKED design (2026-10-09)

The owner's finished newsletter redesign (navy / brass / ivory, 720px) is saved in `docs/newsletter-v3-design/`:

- `index.html`: the design, **source of truth** (inline styles; flexbox/grid, so it is NOT email-safe as is)
- `README.md`: tokens, fonts, section order, components, dynamic-data list, production notes
- `reference-render.pdf` and `The_Crypto_Playback_Newsletter v3.pdf`: how it should look (same render)
- `assets/TCP_Header_1_2.png` (date is baked in) and `assets/TCP_newsletter_footer.png` (unsubscribe text is baked in)

Rules: match it exactly; do not change copy, colors or fonts unless the owner asks. The owner's originals also remain in `~/Downloads/crypto-playback-newsletter zip/` (plus larger transparent mascot/title artwork).

## Status
The live email is still the older Oct 3 layout (tag `newsletter-v2.2`, black/copper). The rebuild from this design is in progress on branch `newsletter-v3-design`: email-safe (tables, inline CSS, PNG icons), data-driven from the live data, dateless/per-issue header, real unsubscribe links, then the Playback Read block ("Today's" / "This Week's Playback Read:" + "View in the Playback Lab").

## Known differences the data forces
- Signal Confluence counts only indicators with a positive/negative reading (13 today); Alerts & Indicators lists all 16 cards, so 3 informational ones (Altcoin Rotation, Whale Activity, Market Breadth) are not scored.
- New content the generator does not produce yet: Bottom Line bullets, per-story category, "Why it matters", Top News vs Market Structure split, Week Ahead rows, sponsor slot.
