# Cloud automation (GitHub Actions) — setup + operation

The daily scan and weekly refresh now run in **GitHub Actions**, so the system
fires every trading night whether or not your laptop is on. Two workflows live
at the repo root under `.github/workflows/`:

- **`daily.yml`** — 18:35 IST (13:05 UTC), Mon–Fri. Prices → tag → diff →
  alerts → journal → paper book → outcomes → dashboard → (Telegram) → commits
  the forward record back → publishes the dashboard to GitHub Pages.
- **`weekly.yml`** — Sun 10:00 IST (04:30 UTC). universe → prices → focus →
  fundamentals → shortlist → (AI committee) → commit.

Both also have a **"Run workflow"** button (Actions tab) for on-demand runs.

---

## One-time setup (do these in order)

### 1. First run — prime the cache
Actions → **Daily scan (cloud)** → **Run workflow**. The first run finds an
empty cache and does a FULL price backfill (~15–25 min, one time). It will
report a baseline with **no alerts** (there's no prior state to diff against —
expected). Every later run is incremental (~7–10 min) and diffs against the
committed `state/tags_state.json`.

### 2. Enable GitHub Pages (to view the dashboard remotely)
Repo **Settings → Pages → Build and deployment → Source = GitHub Actions**.
After the next daily run, the dashboard is live at
`https://kartikeyaav.github.io/Golden-Stock/`. (Until enabled, the
`publish-dashboard` job fails harmlessly — the scan job still succeeds and the
dashboard is also attached to each run as a downloadable artifact.)

### 3. Add secrets (optional but recommended) — Settings → Secrets and variables → Actions
**Status: all three set as of 2026-07-18 — Telegram delivery verified end-to-end.**

| Secret | Enables | Without it | Set? |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | alerts pushed to your phone | alerts only in `daily_alerts.md` / Pages | ✅ |
| `ANTHROPIC_API_KEY` | nightly AI analyst dives (daily.yml only) | that step skips cleanly | ✅ |

**AI split (2026-07-19, credit discipline):** the **weekly committee no longer
runs in the cloud** — weekly.yml always passes `--no-ai`. The user runs it
locally on subscription auth (free at the margin, no credit-exhaustion risk):

```bash
python scripts/ai_picks.py      # committee on the laptop (subscription /login)
git add ai_picks.json ai_picks.md && git commit -m "weekly committee picks" && git push
```

The cloud weekly never rewrites ai_picks.json under `--no-ai`, so the pushed
picks persist and every subsequent dashboard build (daily + weekly) uses them.
The nightly analyst (2 dives max, cents/night, only on alert nights) stays on
the API key in daily.yml; if credits run dry it degrades cleanly and the
health check surfaces it.

The AI layers are pay-per-use with the API key (a few cents/day) — the right
model for an unattended job (your Claude subscription login can't work headless
in the cloud).

### 4. Disable the laptop scheduled tasks (IMPORTANT — avoid double runs)
Two runners both writing the journal and pushing = merge conflicts. Once the
cloud run is verified, disable the local tasks (PowerShell):
```
Disable-ScheduledTask -TaskName MultibaggerDailyScan
Disable-ScheduledTask -TaskName MultibaggerWeeklyRefresh
```
Re-enable them only if you ever want the laptop to be the runner again. To pull
the cloud's commits to your laptop for local viewing: `git pull`.

---

## How state persists (the design)

- **Price + fundamentals caches** (75 MB) → `actions/cache`, keyed per run with
  a rolling restore. A rare cache miss just triggers a one-night full backfill.
- **The forward record** (journal, `tags_state.json` diff-baseline, alerts,
  `news_radar.json` since-window baseline, positions; the weekly also commits
  `shortlist_details.json` — the drawer's full 8-dim data) → committed back to
  the repo each run. Small, durable, survives cache eviction, and doubles as
  the offsite backup.
- **The dashboard** → GitHub Pages (no git-history bloat) + a run artifact.

## Known risks to watch on the first runs
- **Yahoo rate-limiting from datacenter IPs.** GitHub runners share IP ranges
  Yahoo sometimes throttles. Per-symbol failures are non-fatal and listed in
  the log; if MANY fail, the health check shouts "only X% tagged". If this
  bites, the fix is a longer `--pause` or a fetch retry — tell me the log.
- **screener.in scraping (weekly)** may be blocked from cloud IPs similarly.
- Cron can be delayed minutes during GitHub peak load — fine for a post-close job.
