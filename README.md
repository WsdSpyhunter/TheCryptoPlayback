# The Crypto Playback — setup

Everything's built. Here's what's left, all done through GitHub's website —
no terminal, no coding.

## 1. Create the repo
- Go to github.com → **New repository**
- Name it `cryptoplayback` (or anything you like)
- Set it to **Public** (required for free GitHub Pages hosting)
- Don't check any of the "initialize with" boxes
- Create it

## 2. Upload these files
- Unzip the folder you downloaded from this chat
- On your new repo's page, click **"uploading an existing file"**
- Drag in `assets`, `data`, `posts`, `scripts` (the folders), plus `CNAME`,
  `README.md`, `requirements.txt`, and the `.html` files
- ⚠️ **The `.github` folder needs a separate step** — folders starting with a
  dot are easy for browsers to silently skip during drag-and-drop, and this
  one holds the actual daily/weekly schedules, so don't skip it:
  - After committing the first batch, click **Add file → Create new file**
  - In the filename box, type `.github/workflows/daily.yml` (typing the
    slashes creates the folders automatically)
  - Open `daily.yml` from your unzipped folder in a text editor, copy
    everything, paste it into GitHub's editor → **Commit changes**
  - Repeat once more for `.github/workflows/weekly.yml`
- Scroll down, click **Commit changes** on the first batch if you haven't already

## 3. Turn on GitHub Pages
- Repo → **Settings** → **Pages** (left sidebar)
- Under "Build and deployment": Source = **Deploy from a branch**, Branch =
  **main**, folder = **/ (root)** → **Save**
- Still on that page, under "Custom domain," type `cryptoplayback.com` → **Save**
- Wait for the green "DNS check successful" message (can take a few minutes
  to a few hours)
- Once it appears, check **Enforce HTTPS**

## 4. Add your API keys as Secrets
Repo → **Settings** → **Secrets and variables** → **Actions** → **New
repository secret**, one at a time:

| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic console key |
| `COINGECKO_API_KEY` | your CoinGecko demo key |
| `BUTTONDOWN_API_KEY` | your Buttondown key |

(These stay private to GitHub Actions — never visible in the repo itself.)

## 5. Test it manually before waiting for the schedule
- Repo → **Actions** tab → click **Daily Playback** on the left → **Run
  workflow** button → **Run workflow**
- Wait ~30 seconds, refresh — you should see a new **Pull Request** open
  with today's post
- Open it, read the diff, click **Merge pull request** — the site updates
  automatically within a minute or two
- Do the same for **Weekly Playback** to test that path too (it'll also
  create a Buttondown draft — check buttondown.com/emails/drafts for it)

## How it runs from here
- Daily post: fires automatically every morning (~6am CST)
- Weekly post: fires automatically every Friday morning
- Each one opens a PR — **GitHub emails you automatically** the moment
  that happens (that email/notification IS the "review it" step)
- Merge the PR to publish it live on the site
- For the weekly one, also go to Buttondown and hit **Send** on the
  matching draft when you're ready

## What each file does
- `scripts/fetch_prices.py` — pulls top 5 coin prices from CoinGecko
- `scripts/fetch_news.py` — pulls headlines from crypto RSS feeds (no key needed)
- `scripts/generate_issue.py` — shared logic both of the below call into: ask Claude for 4-10 stories, publish the post, create the Buttondown draft
- `scripts/generate_daily.py` — Sonnet picks 4-10 of the day's most significant stories
- `scripts/generate_weekly.py` — Sonnet picks 4-10 of the week's most significant stories
- `scripts/build_site.py` — turns a post into HTML and updates the homepage/archive
- `scripts/build_static_pages.py` — rebuilds About/Resources (run by hand if you edit copy there)
- `.github/workflows/*.yml` — the schedules that run the above automatically

## Editing About/Resources copy later
Open `scripts/build_static_pages.py`, edit the text inside `ABOUT_BODY` or
`RESOURCES_BODY`, then either run it locally or just come back and ask for
help re-running it — it's the one part the daily/weekly automation never
touches.
