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

---

## What happens when a run fails (added 2026-09-12)

Before this date, nothing did. Every step that reports — the dashboard build,
the Telegram digest, the commit of the forward record — runs AFTER the work
inside the same job, so a crashed scan skipped its own announcers. 18 runs
failed across four sessions and the first word came from the watchdog 39 hours
later. The repair has four parts:

| When | What tells you |
|---|---|
| A job fails | `scripts/notify_failure.py` under `if: failure()` — names the failed step and the last error line, with a link to the run |
| Three failures on the same commit in 20h | The daily guard stops replaying it and sends one message saying retries are paused (plain curl — that job has no interpreter by design) |
| A scan ran but fetched no prices | `daily_scan` exits 1 below 50% coverage, so it is a red run, not a quiet evening |
| Nothing ran at all | `scan_watchdog.py`, twice a night, judged on the SESSION and its coverage rather than on when the scan last ran |

`state/tags_state.json` carries `session` and `price_coverage` for exactly this
reason: "a scan ran" and "that scan saw prices" are different facts, and only
the first used to be readable.

## Cadence

| Workflow | Slots | Guard |
|---|---|---|
| daily | six, 10:20–22:05 UTC Mon–Fri | session + coverage in the committed state; pauses after 3 same-commit failures |
| weekly | 04:30 and 10:30 UTC Sunday | skips if `shortlist_ranked.csv` was committed in the last 20h |
| penny | 05:00 and 11:00 UTC every 3rd day | skips if `state/penny_meta.json` was committed in the last 20h |
| watchdog | 01:30 and 03:00 UTC Tue–Sat | none — it is the thing that watches |

GitHub's scheduler is best effort: measured delays here run 1h48–4h05, and it
dropped the daily cron entirely on 2026-08-31. The slots are early on purpose
(a 10:20 slot delivered four hours late still lands at 19:50 IST) and the
guards make the extra ones free. If the delivery hour ever matters more than
this, the fix is an external cron calling `workflow_dispatch`, which starts
within seconds — it needs a fine-grained token with Actions: write, scoped to
this repo, kept at the scheduler (cron-job.org, a Cloudflare Worker, anything).

## Moving the AI layers into the cloud

Both AI layers run on the laptop's Claude subscription today. `claude
setup-token` issues a long-lived subscription token, which makes them runnable
headlessly — the reason they were kept local in July no longer holds, and the
laptop is the system's last single point of failure (it sleeps, its login
expires, its CLI self-updates, and it is a SECOND writer to this repo).

1. Run `claude setup-token` locally and copy the token.
2. Repo -> Settings -> Secrets and variables -> Actions -> New secret,
   named **`CLAUDE_CODE_OAUTH_TOKEN`**. The gated steps in `daily.yml` and
   `weekly.yml` start running; nothing else changes.
3. When a cloud run has produced a verdict, set `ai_runner.json` to
   `{"runner": "cloud"}` and commit it, then disable the laptop tasks:

```powershell
Disable-ScheduledTask -TaskName MultibaggerNightlyAnalystEvening
Disable-ScheduledTask -TaskName MultibaggerWeeklyCommittee
```

Both wrappers already stand down on the marker alone, so the order is safe
either way; the marker is what prevents two writers, and two writers on one
branch is what wedged the tree for five days on 09-07.

No API credits are involved at any point — this is the same subscription the
laptop uses, and the same usage limits.
