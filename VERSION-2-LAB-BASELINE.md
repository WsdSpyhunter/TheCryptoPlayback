# The Crypto Playback Lab: baseline (locked)

**Locked 2026-10-08** on branch `version-2-dev`, tag `version-2-lab-baseline`.
The approved Playback Lab page (`playback-lab.html`, menu "Playback Lab"). Do not restyle or re-threshold it
without the owner's request. The homepage stays locked separately at `version-2-homepage-baseline`.

## What is locked
- Page: `scripts/pro_page.py` (hero with centered ivory tagline box, The PlayBack Read, The PlayBack Summary strip, seven sections, methodology) and the Lab styles at the end of `assets/v2.css`.
- Seven readings (`scripts/pro/`): Institutional Positioning, Basis-Trade Crowding, Regulatory & ETF-Pipeline, Miner Stress, Net Liquidity & Macro, Crowded Unwind Risk (Hyperliquid), Stablecoin Flows. Revenue/TVL Quality stays offline.
- The Playback Read (`scripts/pro/read.py`): a tally, no blended score; thresholds documented in the file and on the page; Regulatory does not vote. Daily record in `data/pro/read_history.json` begins 2026-10-08.
- Methodology: `docs/INSTITUTIONAL-INDICATORS.md`; licensing notes: `docs/DATA-LICENSE-REVIEW.md`.

## Not part of this baseline / still open
Net Liquidity and the Read are not yet verified on a GitHub runner; weekly newsletter line (needs owner approval); homepage links to the Lab (homepage is locked); paused Version 2 rollout in `TODO.md`; merge to `main` only on the owner's go-ahead (the 2-hourly Lab refresh only runs from the default branch).
Rollback: `git checkout version-2-lab-baseline`.
