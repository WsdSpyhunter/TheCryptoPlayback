# The Crypto Playback — Version 1 (final)

**Frozen on 2026-10-07.** This is the complete website + newsletter exactly as built
through Version 1, preserved before the planned redesign. Anything tagged or branched
as `version-1-final` / `version-1` must never be edited, moved, or deleted.

| Where | Name |
|---|---|
| Git tag (the permanent marker) | `version-1-final` |
| Git branch (browsable copy) | `version-1` |
| GitHub Release (downloadable zip) | "Version 1 (final)" |

> The older tags `v1`, `checkpoint-1`, `tcp-v1`, `tcp-v2`, `site-v1`, `newsletter-v1`
> are **earlier partial milestones**, not this snapshot. In particular `newsletter-v1`
> is the *original* email design (before Market Snapshot / Signal Confluence) and `v1`
> is the Sept 30 indicators checkpoint. `version-1-final` supersedes them all.

## What Version 1 contains

### Website (cryptoplayback.com, GitHub Pages + Cloudflare)
- Homepage: Top 6 Market ticker, Market Snapshot (bull/bear), Signal Confluence,
  What Changed, Alerts & Indicators (16 live cards), Top News Stories teasers,
  Subscribe (live Buttondown form), Decode The Dashboard.
- 16 indicator pages, an Archive, About, Resources (banded sections), issue pages.
- Live data refreshes automatically (every 15 min, plus ETF flow and market breadth 4x/day).
- The "Biggest Mover (24H)" ranks the top 10 coins by market cap (ticker stays top 6).

### Newsletter (Buttondown)
- Email design "v2.2": masthead, ticker, release row, Market Snapshot, Signal
  Confluence, NEWS HIGHLIGHTS / Top Story, Here's A Story You Missed, NOTABLE title,
  stories, footer. Clickable header/sections; phone-tested in Gmail + Apple Mail.
- Daily Mon–Fri and Weekly on Saturday, 6:30 AM Central, fully automatic.
- You get a `[PREVIEW]` email; pressing **Publish** in Buttondown is the only manual step.
  The website posts the issue within ~10 minutes of publishing (not before).
- Safeguards: blocked-word handling (`scripts/blocked_terms.py`), story-image checking
  (`scripts/story_images.py`), malformed-AI-output retry, duplicate-proof scheduling guard.

### Automation (`.github/workflows/`)
| Workflow | When |
|---|---|
| `daily.yml` | Mon–Fri 6:30 AM Central (3 UTC starts + guard) |
| `weekly.yml` | Saturday 6:30 AM Central (3 UTC starts + guard) |
| `publish-approved.yml` | every 10 min — posts a published issue to the site |
| `refresh-indicators.yml` | every 15 min |
| `refresh-etf-flow.yml`, `refresh-market-breadth.yml` | 4x/day each |
| `email-test.yml`, `rebuild-draft.yml` | manual only |

## What is NOT in the repository (keep these safe separately)
- **GitHub repo secrets** (names only, values live in GitHub): `ANTHROPIC_API_KEY`,
  `BUTTONDOWN_API_KEY`, `COINGECKO_API_KEY`, `SOSOVALUE_API_KEY`.
- **Buttondown settings** — Settings → Design → Email: Template **Modern**, author name
  TheCryptoPlayback, accent color #0069ff, Header/Footer/Custom CSS add-ons off,
  "Inline CSS variables" on. Newsletter username: `cryptoplayback`.
  Sending allowed to the review address scottdrealty@gmail.com.
- **Cloudflare / DNS** configuration for cryptoplayback.com (the repo only has `CNAME`).
- Subscriber list and sent emails (they live in Buttondown).

## How to get Version 1 back

Look at it without changing anything:
```bash
git fetch --tags
git worktree add ../tcp-version-1 version-1-final
cd ../tcp-version-1 && python3 -m http.server 8000     # open http://localhost:8000
```

Put the live site/automation back to Version 1 (replaces current files, keeps history):
```bash
git checkout main && git pull
git checkout version-1-final -- .
git commit -m "Restore Version 1" && git push
```

Download it: GitHub → Releases → "Version 1 (final)" → Source code (zip).

## Rules for the redesign
Do the new design on its own branch (e.g. `version-2-dev`) and merge to `main` only
when ready — `main` is what the live site and the daily newsletter run from.
