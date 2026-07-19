# HANDOFF — Golden-Stock Screener (read this first to continue)

**Last updated: 2026-07-13 (consolidation pass before a fresh chat).**
This is the single "where we are / what's next" doc. For strategy read
`../../PROJECT_BRIEF.md` (it lives at the git root `files/`, NOT in this
folder); for the evidence read `VALIDATION_REPORT.md`; for cloud ops read
`CLOUD.md`. Sections 3-3J below are a chronological work-log (kept for
context) — sections 0/1/2/4/5/6/7 are the CURRENT state, kept fresh.

---

## 0. One-paragraph summary

A decision-support system that finds Indian small/mid-cap "golden stocks",
explains why, sizes the trade, and keeps a forward track record. It runs
itself — now in the **cloud** (GitHub Actions, repo:
github.com/kartikeyaav/Golden-Stock), not dependent on the laptop being on:
a nightly scan fires transition alerts, an AI analyst deep-researches the top
buy candidates (with second-order ecosystem research — customers/suppliers/
competitors, not just company-named news), and a weekly job refreshes
everything + an AI investment committee picks 3-5 researched names (now
cross-fed the daily analyst's recent verdicts). Entries are 100% technical
(backtest-validated, never AI/fundamental-gated). The dashboard was fully
revamped (terminal aesthetic, Ctrl+K command palette, decision-first
Actionable panel with plain-English DO chips and filters) and its data flow
unified (screener/actionable/drawer used to show inconsistent coverage —
fixed). **The backtested read was corrected 2026-07-12: sizing was measured
off remaining cash, undersizing every late entry — equity-basis sizing is the
same rules, same entries, just honest measurement, and it roughly DOUBLES the
CAGR read** (see §3H). **The system is essentially complete and live, now
laptop-independent.** Cloud run verified, Telegram live, API key set (all
2026-07-18). What remains is mostly time (the forward journal must accumulate
before real capital scales).

---

## 1. Environment / how to run (IMPORTANT gotchas)

- **Python**: always use the full path — `C:/Users/karth/AppData/Local/Python/pythoncore-3.14-64/python.exe`.
  Bash `python` PATH is flaky; PowerShell tool also works.
- **Project root** (all commands run from here):
  `C:\Users\karth\OneDrive\Desktop\Karthikeya_claude\files\multibagger_screener\multibagger_screener`
- **Git repo** is at `files/` (parent), pushed to **github.com/kartikeyaav/Golden-Stock**
  (remote `origin`, branch `master`; push works non-interactively — credential
  is cached via Windows Git Credential Manager after the user's one manual login).
  Commits through `8746dc3`+ (see `git log`). `.gitignore` excludes caches,
  secrets, logs, test artifacts.
- **Cloud is the sole runner** (verified 2026-07-18): `.github/workflows/daily.yml`
  + `weekly.yml` on GitHub Actions — see `CLOUD.md` for full setup/ops. The
  Windows Task Scheduler jobs (`MultibaggerDailyScan`/`WeeklyRefresh`) are now
  **DISABLED** (they still exist, so re-enabling is a one-liner if the cloud
  ever needs a fallback) — running both was causing two runners to push the
  journal and produce merge conflicts / diverged history. Do NOT re-enable
  while the cloud runs.
- **AI scripts spawn `claude -p`**: they scrub `CLAUDE_CODE_*` + `ANTHROPIC_BASE_URL`
  from the env before spawning (else the host-injected auth poisons the child
  CLI -> "Invalid API key"). This is already coded; don't remove it.
- **Auth**: subscription `/login` works headless locally (with the scrub), but
  **cannot work in GitHub Actions** (no browser) — cloud AI steps need an
  `ANTHROPIC_API_KEY` repo secret instead; they skip cleanly if it's absent.
  `python scripts/ai_analyst.py --selftest` verifies local auth.

### Key commands
```
python scripts/daily_scan.py            # tag + diff + alerts + journal (usually scheduled)
python scripts/ai_analyst.py            # deep-dive top-3 buy alerts -> verdicts
python scripts/ai_picks.py              # weekly AI committee: 3-5 researched picks (Opus 4.7)
python scripts/weekly_refresh.py        # universe->prices->focus->fundamentals->shortlist->picks->dashboard
python scripts/weekly_refresh.py --no-ai  # same, skip the AI committee (no credits)
python scripts/build_dashboard.py       # regenerate dashboard.html
python scripts/dashboard_server.py      # serve dashboard + Run panel (localhost:8765)
python scripts/enrich.py SYMBOL         # on-demand full card for any stock
python scripts/sync_positions.py        # holdings vs positions drift check
python scripts/import_holdings.py FILE.csv --dry-run  # sync holdings from a Zerodha Console export, no Kite login
python scripts/backup_push.py           # commit+push the forward record to GitHub (non-fatal)
```
Open `dashboard.html` directly in a browser, or via `dashboard_server.py` for
the Run panel, or the published copy at `kartikeyaav.github.io/Golden-Stock/`
(once the user enables Pages — see CLOUD.md).

---

## 2. What's built and live (the whole system)

**Data spine** (all cached locally, engine reads cache only):
- Prices: Yahoo daily OHLCV 2019->now, 651 stocks, verified paisa-exact vs Zerodha/Kite MCP. `data_cache/`
- Fundamentals: screener.in public pages, all 651, ~12 quarters + 10y series. `fundamentals_cache/`
- Filings: NSE corporate-announcements RSS, archived daily. `announcements_archive.csv`

**Universe**: Nifty Smallcap 250 + Midcap 150 + Microcap 250 = 651 names. `universe.csv`.

**Pipeline** (nightly + weekly):
Universe -> liquidity filter -> RS-percentile focus list (~320, reporting-only)
-> mechanical stage tags (all 611 taggable, the FULL universe — evidence lock)
-> transition diff vs saved state -> alerts only on state changes -> per-alert:
8-dim conviction score + vetoes + two-lot plan + **entry-fidelity label**
(VALIDATED = exact backtested VCP-pivot+volume breakout / AWAITING TRIGGER =
base live, pivot not cleared / NO VCP BASE = trend read only — logged to
`journal/entry_signals.csv` for a future forward test, never a gate yet).
Plus the **News Radar** (§3K): each scan also classifies NSE filings arrived
since the last run and cross-references tonight's technical state (CONFLUENCE
= positive news on an actionable chart) — news-first DISCOVERY, attention
only, never entries.

**8-dimension conviction score** (coverage-honest, 0-100):
rs_and_stage 20 (LIVE, validated) · earnings_inflection 20 · theme 15 ·
smart_money 12 · financial_strength 10 · catalyst 10 · governance 8+veto ·
valuation_sanity 5. Fundamentals are point-in-time (`scoring/pit_fundamentals.py`);
news dims are keyword+trust+sentiment filtered ("news-based v0").

**Entry / risk (mechanical, validated, NEVER AI-driven)**: TWO validated
technical entry classes — (a) VCP breakout (8-pt trend template + VCP +
volume over pivot), (b) EPISODIC PIVOT (gap >=8% on >=3x volume, adopted
2026-07-19, §3L) -> two-lot structure (trading lot partial@2.5R + 50-DMA
trail; core lot exits on weekly close < 30-week MA); stop = 2.5xATR for
VCP entries / gap-day low for EP entries, skip if >12% wide; regime sizing
(risk x0.5 when universe breadth <50% above 200-DMA — adopted 2026-07-19,
NIFTY/150-DMA as fallback).
**Sizing basis corrected 2026-07-12** (§3H): fixed-fractional on EQUITY, not
remaining cash — same rules, just honest measurement. Live plans were never
affected (they already size off `RISK.capital`); update that config value to
your real account equity periodically for true fixed-fractional behavior.

**Vetoes** (hard, cap score at 25): promoter pledge >10%, leverage+froth,
governance red flags. Data-based; AI cannot override.

**AI layers** (context/curation only, journaled, unvalidated-so-on-probation):
- Daily analyst (`ai_analyst.py`, **claude-sonnet-5**): researches top-3
  conviction buy alerts, writes VERDICT/CONVICTION/SIZE. Can only be MORE
  conservative (take/halve/skip), never override vetoes or resize up. Now does
  **second-order ecosystem research** (customers/end-markets, suppliers/input
  prices, competitors, value-chain regulation — with a named transmission
  channel, not generic sector talk) since the keyword scan only sees news
  naming the company itself. Writes a heartbeat to `state/analyst_health.json`
  (ok/failed/idle) so a silent auth failure gets surfaced by the next scan.
- Weekly committee (`ai_picks.py`, **claude-opus-4-7 + MAX_THINKING_TOKENS=24000**):
  reads the scored shortlist, selects optimum 3-5, deep-researches, writes
  theses. Same second-order research requirement. Briefing now includes the
  **last 14 days of daily-analyst verdicts** as cross-layer context (overlap =
  confirmation; rejecting a daily BUY must be explained in one line).

**Dashboard** (`dashboard.html`, single self-contained SPA — revamped 2026-07-12,
§3H/terminal aesthetic + command palette): tabs = Overview / AI Picks /
Screener (full 611-name universe with a "Focus only" chip, cap-tier + tag
filters) / Positions / Journal / Validation. **Ctrl+K (or `/`) opens a fuzzy
search palette** across all 611 stocks -> arrow-nav -> Enter opens the drawer.
Overview leads with the **Actionable panel** (the only tab you act from):
headline verdict line, every row a plain-English DO chip (BUY SETUP / WATCH /
WEAK / WAIT / IGNORE / DO NOT BUY), filter chips (do-kind isolate-on-click +
conviction floor), resolved signals collapsed. Click any stock anywhere ->
drawer with candlestick chart + why-this-score + plan + news + fundamental
trend charts (drawer data now covers every alerted name, not just the weekly
shortlist — §3F). KPI strip shows ideal/stressed pairs (see §3H for why).

**Ops**: **Cloud-first as of 2026-07-12** — GitHub Actions (`daily.yml` +
`weekly.yml`, see CLOUD.md) runs regardless of the laptop; dashboard publishes
to GitHub Pages. Windows Task Scheduler (`MultibaggerDailyScan` 18:35 IST,
`MultibaggerWeeklyRefresh` Sun 10:00) **DISABLED 2026-07-18** now that the
cloud is verified — they exist but do not fire (re-enabling races the cloud on
the journal push). Journal (`journal/`,
now including `entry_signals.csv` fidelity log), health checks (loud on stale
data/broken parser/degenerate tagger/per-holding staleness/analyst heartbeat),
position management (`positions.csv` vs plan), holdings drift check, nightly
`backup_push.py` commits the forward record to GitHub (offsite backup).

---

## 3. What's validated (evidence — see VALIDATION_REPORT.md)

- Baseline (technical-only, 2-lot, after costs), **CORRECTED sizing basis
  2026-07-12 (§3H — same entries/rules, equity- not cash-basis measurement)**:
  **+1.67R/trade**, payoff ~9.6:1, win ~30%, **CAGR 47.4% ideal / 32.5% under
  deployment stress** (next-open fills + gap-aware stops + full costs), maxDD
  -18.5% ideal / -20.7% stressed. The OLD read (+1.27R, 21.5% CAGR, -12.9% DD)
  was real but measured off remaining cash, which undersizes late entries —
  superseded, kept here only so old context isn't confusing. Survivor-biased
  => directional; churn measured ~9.2%/2y.
- **13+ configs tested, every fundamental/sector/news GATE on entries was
  REJECTED**, and separately every POSITION-SLOT expansion was rejected
  (price leads reported fundamentals; more slots admit weaker same-day
  breakouts). Entries stay technical-only, position cap stays 12, risk-per-trade
  stays 1.25% (higher saturates/breaches DD — §3H).
- **Adopted**: regime sizing (Pareto improvement), equity-basis sizing
  (measurement correction, not a strategy change). **Validated as alert-only**:
  anticipation tier with fundamentals (+0.41R, positive both cohorts).
- Design is evidence-locked (PROJECT_BRIEF.md section 2B, now 11 items).
  Changing it needs new pre-registered evidence.

---

## 3B. 2026-07-09 incident + hardening (context for the journal)

A manual `daily_scan.py` run at 12:34 (mid-market) tagged the universe on
PARTIAL intraday bars: 5 of its 17 alerts were phantoms that reversed by the
close (HEG, BERGEPAINT, BHARTIHEXA, SANDUMA, HFCL) and it missed 7 real ones.
Fixes, all live:

- **`data/cache.py` partial-bar guard**: `load_ohlcv` drops a bar dated today
  until 15:45 IST (`BAR_FINAL_IST`) — every consumer (scan, tagger, position
  manager, dashboard, outcomes) now only ever sees completed candles. Running
  the scan at ANY hour is now safe (an intraday run simply reads yesterday's
  close).
- **Journal integrity**: the 18 intraday rows were moved to
  `journal/quarantine_intraday_2026-07-09.csv` (preserved for audit, out of
  the forward-validation stats); state was restored from the 07-07 snapshot
  and the 16:39 post-close re-scan journaled the clean set (19 transitions
  covering Jul-8+9). MOSCHIP's breakeven flag (set intraday) was reverted and
  legitimately re-fired on the final close.
- **Task Scheduler**: both jobs previously had DisallowStartIfOnBatteries +
  no catch-up — that's why Jul-8 was silently skipped on this laptop. Now:
  run on battery, StartWhenAvailable catch-up (safe with the bar guard), 4h
  execution limit.
- **NSE feed**: the ~400KB RSS download can truncate mid-stream (lost a day's
  filings). `fetch_announcements` now retries 3x; the failed day was
  backfilled (+470 filings).
- **daily_job chain** now runs `journal_outcomes.py` before the dashboard
  build, so the Journal tab's forward-validation KPIs stay live.

## 3C. Paper book + clarity layer (2026-07-09 evening, user-requested)

User confusion driving this: alerts churn nightly by design, but nothing
showed what was STILL actionable vs faded, the Journal read as a raw stream,
and screener prices were stale (focus_list.csv is a WEEKLY snapshot — its
last_close was 4 days old; screener Price now reads the daily cache, and the
header shows "prices as of <date>").

- **`scripts/paper_trader.py` — the analyst's paper book.** Every analyst
  BUY verdict auto-becomes a paper position: filled at the NEXT session's
  open (stress-validated fill), stop = the alert's suggested stop, sized
  RISK.capital x 1.25% x regime, halved on HALF PLAN, 15% value cap, no
  pyramiding. Exits run through the SAME `position_manager.check_positions`
  as real positions (generalized: takes positions_path + optional
  ledger_path; fills booked to `journal/paper_ledger.csv`). State in
  `paper_positions.csv`; idempotent by symbol@verdict-timestamp; skips
  (gap-below-stop, no stop, already open) are ledgered so they never retry.
  In daily_job after the analyst. First fills 2026-07-09: SYRMA 16sh@1410.40,
  SHILPAMED 49sh@599.00, LAURUSLABS 31sh@1468.10 (all HALF; CHENNPETRO /
  IPCALAB / ACMESOLAR pending next open). THIS is the number that decides if
  the AI layer earns its keep (brief: journal must beat the machine alone).
- **Dashboard — Overview "Actionable now" panel**: buy signals from the last
  7 days marked against tonight's tag: ACTIONABLE (still CONFIRMED) / RAN
  AWAY (extended) / FADED / VETOED — the demarcation between one-night
  alerts and standing opportunities. Survives daily_alerts.md overwrites
  (reads the journal).
- **Dashboard — Journal tab**: added a buy-signal scorecard (one row per buy
  alert ever: alert price, stop, ret%, R-now, max-R, open/stopped status,
  plain-English explainer) above the raw event stream.
- **Dashboard — Positions tab**: Paper book section (net/realized/unrealized
  KPIs, open paper positions, pending fills, recent ledger) above the
  clearly-labeled "Real positions" section.

## 3D. Entry-fidelity labeling + event-risk context (2026-07-10)

Closed the one real divergence between the live system and its own evidence:
the backtested entry (+1.27R) is a **volume breakout over a VCP pivot**, but the
live scan alerted on the looser CONFIRMED tag (Stage 2 + trend template only),
which never checked VCP/breakout. Audit on 120 names: 15 CONFIRMED → 0 validated
entries, 4 awaiting-trigger, 11 no-VCP-base — most alerts were NOT the
backtested signal. Fixes (labeling only — nothing new gates what fires, per the
evidence lock):

- **`scoring/stage_tagger.py`**: `tag_stock` now computes the exact backtest
  trigger at the last bar (`detect_breakout` over the live VCP pivot) and
  returns `validated_entry` / `pivot_price` / `breakout_today` /
  `breakout_volume_ratio`.
- **`reports/watchlist_card.py`**: every CONFIRMED card leads with one of
  `VALIDATED ENTRY` (fresh breakout over pivot on ≥1.5x vol — act) /
  `CONFIRMED, AWAITING TRIGGER` (VCP base live, watch the pivot) /
  `CONFIRMED, NO VCP BASE` (trend read only, edge not established).
- **`scripts/daily_scan.py`**: buy-alert summary lines carry `[VALIDATED]` /
  `[AWAITING TRIGGER]` / `[NO VCP BASE]`; each buy/re-entry alert is logged to a
  NEW additive file **`journal/entry_signals.csv`** (own schema — signals_journal
  stays pristine) so we can later test whether validated-entry alerts outperform.
  No change to what fires or what gets paper-traded — the cohort has to earn a
  gate with forward evidence first.
- **Event-risk context**: `scoring/phase_c.enrich` now flags results /
  board-meeting NSE filings (`config.CATALYST.results_event_keywords`); the card
  shows `!! EVENT RISK [results/board mtg, <date>]` — binary event risk near a
  breakout (Minervini earnings-date discipline). Context only, never a gate.

Verified: both regression tests green; full scan runs clean (611 names, exit 0);
tagger/card/writer unit-smoke-tested. NOT committed yet.

## 3E. Run-from-UI (2026-07-10, user-requested)

`scripts/dashboard_server.py` (stdlib, binds 127.0.0.1:8765 default; launch.json
runs it on 8787) serves dashboard.html + a job API. The dashboard sidebar now
has a RUN panel that appears ONLY when served by this server (plain file:// open
= panel hidden, dashboard unchanged). Buttons:

- **Daily scan (no AI)** — daily_scan -> paper_trader -> journal_outcomes ->
  build_dashboard. Zero claude credits, no telegram (manual re-runs must not
  spam the phone; telegram stays with the scheduled job).
- **Scan + AI analyst** — adds ai_analyst.py (sonnet, self-capped 3 dives/day).
- **Weekly refresh (no AI)** — weekly_refresh.py **--no-ai** (new flag): full
  chain, AI committee (ai_picks/Opus) SKIPPED.

The AI committee is NOT runnable from the UI at all — credit guard is
server-side (no such job exists), not just a missing button. One job at a time
(HTTP 409 if busy); log streams into the panel (2s poll); on completion a
"Reload fresh data" button appears (job chains end with build_dashboard).
Panel hidden on mobile (<1000px). Start it with:
`python scripts/dashboard_server.py` then open http://127.0.0.1:8765.
Safe at any hour — the partial-bar cache guard (3B) makes intraday runs
harmless, and the chain is idempotent (StartWhenAvailable evidence, 3C).

## 3F. Dashboard data-flow unification (2026-07-11, user-caught)

User: "screener and actionable show different stocks; actionable names have no
score and empty drawers." Root cause: three different coverage sets — scan
alerts from the FULL universe (609), screener showed only the focus list (320),
and drawer details/charts existed only for the weekly shortlist (84). Fixes:

- **daily_scan.build_candidate now persists its full analysis**: every buy
  alert writes a drawer-schema detail blob (dims/plan/news/vetoes/score) to
  `state/alert_details.json` (30-day expiry, `save_alert_details`). The scan
  already computed all of it and was throwing the structured form away.
- **build_dashboard merges** shortlist_details + alert_details (alert wins),
  and detail OHLC/fundamentals now cover shortlist + positions + PAPER BOOK +
  every alerted name. The 47 in-window alerts were backfilled — all have
  full drawers now (incl. two vetoes the panel previously hid: INDUSINDBK,
  NAZARA at 25-capped).
- **Screener = full watched universe (611 rows)**, not just focus; non-focus
  rows carry tag/price/cap/score but no RS percentile (that's a focus-list
  artifact). New "Focus only" chip restores the old view.
- **Actionable panel**: Conv column always filled (journal value, shortlist
  fallback) + Trigger column (VALIDATED / AWAITING TRIGGER / NO VCP BASE from
  entry_signals.csv) — the 3D entry-fidelity work is now visible in the UI.
- Drawer header falls back to alert-time conviction when a name isn't in the
  weekly ranked file; chart placeholder text explains how data loads.

## 3G. Sizing matrix (2026-07-11, pre-registered — scripts/run_sizing_matrix.py)

Motivated by "21.5% CAGR feels low": utilization measurement showed avg open
risk 0.69%/position vs nominal 1.25% and the 12-slot cap binding 39% of days.
9-cell sweep risk{1.25,1.75,2.5} x slots{12,16,20}, same signals/window/costs.
VERDICTS (sizing_matrix_report.md): (1) slot expansion REJECTED — expectancy
falls monotonically (1.29R -> 1.15R -> 0.89R; the volume-ranked queue already
takes the best same-day breakouts, extra slots admit weaker ones) and CAGR
falls too. (2) risk%% saturates at the 15%% value cap: 1.75%% lifts corrected
CAGR 21.5 -> 23.4%% (MAR 1.67 -> 1.79, DD +0.2pp); 2.5%% adds nothing more.
Within survivor-bias noise -> user choice, DEFAULT KEPT at 1.25%%; revisit
after forward journal matures. (3) The 15%% value cap is the residual untested
lever (own pre-registered run + concentration-risk debate required). Bottom
line: both obvious throttles tested; system is capacity-limited by its own
discipline — more absolute return = more capital or accepting more DD.

## 3H. Actionable panel redesign + sizing matrix v2 (2026-07-12)

- **Actionable panel is now decision-first** (user: "if that's where I act, it
  must be intuitive"): headline verdict line ("N validated buy triggers — act
  today" / "No validated triggers — nothing requires action"), every row leads
  with a plain-English DO chip (BUY SETUP / WATCH / WEAK / WAIT / IGNORE /
  DO NOT BUY), rows sorted act-first (VALIDATED > AWAITING > WEAK, conv desc),
  resolved signals (ran away/faded/vetoed) collapsed under a <details> toggle.
- **Sizing matrix v2 — THE HEADLINE RESULT** (scripts/run_sizing_matrix2.py,
  pre-registered; full table + verdict in sizing_matrix2_report.md):
  the engine's cash-basis sizing was an artifact that undersized every late
  entry (~0.3% real risk at 73% deployment). Config B (equity-basis, all
  other rules IDENTICAL): window CAGR 22.5% -> **47.4%**, maxDD -12.9% ->
  -18.5%, MAR 1.75 -> 2.57, P2 chop cohort IMPROVED. Deployment stress
  (next-open fills + gap-aware stops + costs): **32.5% CAGR, -20.7% DD,
  +1.10R** — the honest planning number. Cap relaxation adds nothing (cap
  stays 15%); higher risk% rejected AGAIN (P2 negative + DD breach). ADOPTED
  as the canonical baseline read; KPI strip now shows ideal/stressed pairs.
  Live code needs NO change (live plans already size off RISK.capital, not
  remaining cash) — but for true fixed-fractional the user should update
  RISK.capital to actual account equity periodically. Engine default stays
  size_on="cash" so historical configs reproduce; matrices go equity-basis
  from here.

## 3I. Hardening pass (2026-07-12)

Audit-driven defensive fixes (all small, all pure-defense, tests green):
- **Split/bonus guard** (update_prices.py `_adjustment_detected`): Yahoo
  split-adjusts the whole series retroactively, so a split makes the 7-day
  incremental overlap disagree with cache by the split factor — beyond any
  circuit band. On >30% overlap deviation we refetch full history (consistent
  scale, merge keep=last overwrites the mis-scaled rows). Prevents phantom
  BROKEN alerts / wrong MAs+ATR the day any watched name splits. Unit-tested.
- **Fresh nightly RS percentile** (daily_scan): the 20-weight technical
  dimension was reading week-old focus_list percentile; now ranks tonight's
  live rs_blend across the whole watched universe. Live value overrides the
  weekly one in cards + journal.
- **Per-holding staleness** (daily_scan health): each held symbol checked
  individually (>5d stale or no data => loud alert) — the aggregate <80%
  check can't catch one frozen name you OWN (rename/suspension).
- **AI analyst heartbeat** (ai_analyst `write_health` -> state/analyst_health.json;
  daily_scan reads it): a run where ALL dives fail (auth/session) writes
  status=failed; the next scan shouts it. idle (no buy alerts) is not a
  failure. Closes the silent-analyst-starvation gap.
- **scripts/import_holdings.py**: update holdings.csv from a Zerodha Console
  export (Portfolio->Holdings->download) — NO daily Kite login. Robust header
  detection, prints add/update/gone diff, --dry-run. Does NOT touch
  positions.csv. This is the standing answer to the SEBI daily-session friction.

Still needs the USER (can't be done from here): RISK.capital update to real
equity for true fixed-fractional (#5). (Telegram BotFather token #11 — DONE
2026-07-18, secrets set, delivery verified end-to-end.)

## 3J. Cloud migration — GitHub Actions (2026-07-12)

The job now runs in the cloud so it fires 365 nights regardless of the laptop.
`.github/workflows/daily.yml` (18:35 IST / 13:05 UTC Mon-Fri) + `weekly.yml`
(Sun 10:00 IST / 04:30 UTC), both with a manual Run-workflow button. Full
setup + operations in **CLOUD.md**. Design: price/fundamentals caches (75 MB)
persist via actions/cache (rolling key); the forward record (journal,
tags_state.json diff-baseline, alerts, positions) is committed back to the repo
each run (durable + offsite backup); the dashboard publishes to GitHub Pages
(no git bloat) + a run artifact. Telegram sends only if its secrets are set —
degrades cleanly otherwise. **All three secrets (ANTHROPIC_API_KEY,
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) are set as of 2026-07-18; Telegram
delivery verified end-to-end. Alerts send every run (daily heartbeat — quiet
nights included, by user choice).**

**AI split (2026-07-19, credit discipline):** the **weekly committee is
LOCAL-ONLY** — weekly.yml always runs `--no-ai` (API credits can run dry
mid-cycle; the committee is the expensive call). It runs AUTOMATICALLY via
Task Scheduler task **`MultibaggerWeeklyCommittee`** (triggers: every logon
+2min, and Sun 11:00 IST) → `scripts/weekly_committee_local.py`, which
git-pulls, then runs `ai_picks.py` on subscription auth ONLY IF the cloud's
shortlist_ranked.csv commit is newer than ai_picks.json's generated stamp
(so daily boots are sub-second no-ops; one real run per weekly refresh),
then commits + pushes ai_picks.json/md. Log: `logs/committee_local.log`.
The cloud never rewrites the picks under `--no-ai`, so every dashboard
build uses the pushed ones. The **nightly analyst stays on the API key in
daily.yml** (max 2 dives, cents, alert nights only) and degrades cleanly
if credits die — the health check surfaces it.

USER STEPS (see CLOUD.md): (1) Actions -> Run workflow once to prime the cache
(first run = full backfill, baseline, no alerts — expected). (2) Settings ->
Pages -> Source = GitHub Actions. (3) add secrets (TELEGRAM_*, ANTHROPIC_API_KEY).
(4) ~~DISABLE the laptop tasks~~ **DONE 2026-07-18** — both scheduled tasks are
now Disabled; the cloud is the sole runner.

CANNOT be verified from this repo (no gh/API token here to read Action logs) —
the first live run is user-triggered; iterate from its logs. TOP RISK: Yahoo
(and screener.in) rate-limiting GitHub datacenter IPs — per-symbol failures are
non-fatal + logged; if many fail, health check shouts. Laptop tasks still
enabled + healthy (ran today) as the fallback until cloud is proven.

## 3K. Reliability + news-first + convergence overhaul (2026-07-18/19)

Two intense sessions triggered by user reports ("HFCL picked twice",
"8 questions unanswered", "conviction scores don't match between tabs").
Everything below is LIVE and verified end-to-end.

**Coverage gap (the "no info" dims) — root-caused + fixed:**
- The nightly scan read fundamentals from a cache only the weekly job
  filled, and only for CONFIRMED/ANTICIPATION names -> every cloud
  re-entry/extended alert scored fundamentals-blind (coverage 45%, 5 of 8
  dims empty). `daily_scan.build_candidate` now fetches screener.in LIVE
  for alerted names when the cache is absent/stale — with politeness
  guards (1.8s pause between fetches, 15/night budget; over-budget names
  score technical-only and heal at the weekly). `fetch_fundamentals.py`
  also covers the whole alerted pool (alert_details.json keys), not just
  the shortlist. Verified: screener.in works from GitHub Actions IPs.

**AI analyst was silently dead ~Jul 10-18 — revived + tripwired:**
- Buy lines gained an entry-fidelity label ("**KIND** [STATUS]: SYM")
  ~Jul 10; `extract_candidates()` still expected "**KIND**: SYM", matched
  NOTHING, and reported "no buy-type alerts" through real 9-alert nights.
  Same brittle regex dropped buy alerts from the dashboard Tonight panel.
  Both fixed (optional `[STATUS]` tolerated). Cascade: the paper book
  (fed by verdicts) was frozen too — self-heals at the next alert.
- **Format-drift tripwire**: if buy-type words appear in daily_alerts.md
  but the parser extracts zero candidates, analyst health writes "failed"
  (which the daily health gate already shouts about) instead of an
  indistinguishable-from-quiet "idle". Silence can no longer hide drift.
- Dashboard attaches only analyst verdicts <=10 days old, date shown
  inline (a Jul-9 BUY was decorating fresh alerts as if current).

**Sentiment v0.5 (news quality):**
- Multi-stock roundups/listicles ("Top Gainers & Losers: ... HFCL, ...")
  are detected (`_is_roundup`), forced neutral, EXCLUDED from
  catalyst/theme scoring, and marked on the card. Sentiment keywords now
  match word boundaries with suffix tolerance ("cuts" no longer matches
  "haircuts"; catches fell/tumbles/tanked/...), expanded pos/neg lexicons.

**AI split — credit discipline (weekly committee is LOCAL-ONLY):**
- See the Ops paragraph above (§3J block): weekly.yml always `--no-ai`;
  `scripts/weekly_committee_local.py` + Task Scheduler task
  `MultibaggerWeeklyCommittee` (every logon +2min, Sun 11:00 IST) runs
  the committee on subscription auth when the cloud's shortlist commit is
  newer than the picks — plus a **stranded-output guard** (real incident
  2026-07-19: wrapper died mid-run, orphaned child wrote picks with
  nobody to push them; the no-op branch now pushes fresh-but-dirty picks).
- Nightly analyst stays on the API key (max 2 dives, cents, alert nights).

**Cross-layer wiring (user directive: layers COLLABORATE, never race):**
- Committee already saw analyst verdicts (14d); the analyst now receives
  the standing committee pick's thesis/risks for the alerted name (or the
  current pick list if it isn't one) and must note agreement/divergence
  (`_cross_layer_context`). Both AI layers receive the NIFTY 150-DMA
  regime line. Do NOT build A-vs-B scoreboard features — the user
  explicitly rejected parallel-run designs; measurement happens through
  the forward journal of the one combined output.

**News Radar — news-FIRST discovery (`data/news_radar.py`):**
- Inverts the price-first flow for DISCOVERY only: every scan classifies
  NSE filings arrived since the last run (window = since-last-run state,
  4d cap; the raw feed is ~90% MF-NAV/compliance noise), maps them to
  universe symbols, and cross-references tonight's technical state.
- WHITELIST-only classification (silence is the default), word-boundary
  phrase patterns; three polarities: pos (order wins, expansion, M&A/JV,
  approvals, buyback, rating upgrades), neg (regulatory action, distress,
  pledge, management exits, downgrades), attn (fund raises — dilution is
  direction-ambiguous). Precision traps each handled explicitly + locked
  in a 24-case suite: SAST Reg-31(4) paperwork (matches "acquisition" via
  the regulation's own name AND is discloser-titled), ESOP/NCD
  allotments, NCLT merger-approvals (NOT distress), NCD suspension
  notices, record dates, surveillance notices. 12-day archive test: 164
  raw -> 73 clean hits (~6/day).
- **CONFLUENCE** = positive news on a CONFIRMED/ANTICIPATION chart (the
  radar's reason to exist); **URGENT** = negative news on a held name.
- Output: `state/news_radar.json` (committed by daily.yml) -> dashboard
  Overview panel (hidden when empty) + "## News radar" section in
  daily_alerts.md (-> Telegram). NEWS MOVES ATTENTION, NEVER ENTRIES.

**Convergence view (the "combined robust output"):**
- No new panel — the two existing decision surfaces got richer:
  Actionable's Analyst column became **"AI view"** chips (A: analyst
  verdict <=10d · C: committee "pick · HIGH" / "passed over" · N: radar
  hit); the drawer gained **"Convergence — what each layer says"** (
  Machine/Analyst/Committee/News full lines, honest empty-states,
  ALIGNED n/n pill when >=2 explicit AI voices agree, SPLIT on
  divergence — divergence is information, never averaged away).
- "passed over" vs "not in review set" is a real distinction: payload
  carries `reviewed` (ranked top-20 = the committee's weekly review set).

**Score coherence (SHILPAMED incoherence, user-caught):**
- alert_details ALWAYS overwrote weekly shortlist_details in the drawer
  merge -> a stale fundamentals-blind alert snapshot masked the richer
  weekly read (drawer header said 72 above five "no data" bars reading
  56.2). Merge is now COVERAGE-AWARE: the alert read wins only when at
  least as informed; otherwise weekly dims/score stay and only the
  alert's fresher news/plan/date ride along.
- `shortlist_details.json` gained schema parity (score/coverage/label/
  scored_at) and is now COMMITTED by weekly.yml (it previously existed
  only inside the cloud workspace — every local rebuild used stale data).
- Every conviction display declares its vintage: drawer header "read of
  <date>, coverage X%" (sourced from the RESOLVED detail = same read as
  the dims below), Screener column ° marker + weekly-vintage tooltip,
  "Why this score" header shows read date + coverage. Numbers may differ
  across tabs (different vintages) — but every number says what it is.

**UI (same sessions):** info "?" icons fixed (`.kpi>span` child selector
— descendant rule was stealing display:block), Overview nav alignment
(inline margin-top beat the mobile reset), sticky mobile nav, next-scan
indicator in the header, mobile table scroll-in-card, 640px tier,
re-alert grouping in the journal scorecard (↻ pill + muted), ° coverage
markers in actionable/scorecard.

## 3L. Strategy upgrade session (2026-07-19/20) — journal audit, two
## adopted improvements, landing page

**Forward-journal audit (first structural read, 9 days in):** integrity
PASS (0 dupes; missing-stop rows = risk-engine skips by design). Overall
+0.05R at avg 3.9 days elapsed — no expectancy conclusion possible — but
every STRUCTURAL cut points the right way: conviction bands monotonic
(<50: -0.06R -> 70+: +0.68R), entry-fidelity ordering as the mechanism
predicts (AWAITING +0.00R > NO-VCP -0.08R), RE-ENTRY > fresh BUY, analyst
cohort +0.34R vs +0.02R rest (paper book 6/6 green, +6.6%), 1 stop-out in
105 (clean -1.0R). Zero VALIDATED entries in 72 labeled alerts — within
expected frequency (~0.5-1/wk); becomes a finding if still zero by ~mid-Aug.
Full analysis: strategy_review_2026-07-19.md.

**Research pass** (Minervini progressive exposure, O'Neil market model /
FTD-distribution, Qullamaggie breakout management, Bonde episodic pivots)
-> four pre-registered proposals P1-P4; P1-P3 tested same session:

- **P1 BREADTH REGIME — ADOPTED** (sizing matrices v3 + v3b follow-up,
  §6D of VALIDATION_REPORT, brief §2B #12): risk x0.5 when % of universe
  above its own 200-DMA < 50%, replacing the NIFTY/150-DMA binary. Won
  CAGR 49.5% vs 47.7%, maxDD -14.8% vs -17.6%, MAR 3.35 vs 2.70, AND the
  registered chop-segment guards (P2-seg return +13.6% vs +9.4%, P2-seg
  DD -14.8% vs -17.6%). Two-step disclosure: v3's strict per-trade P2
  clause was missed by 0.027R (composition artifact); v3b registered the
  correct portfolio-level guards BEFORE running. Live: daily_scan computes
  breadth in its tag loop (costs nothing — every chart already loaded) ->
  `state/regime.json` (committed by daily.yml); `scoring/regime.py` reads
  the snapshot, NIFTY/150 fallback when missing/stale (fail-defensive);
  dashboard badge shows live breadth %. NOTE: the rule flipped the live
  regime from DEFENSIVE to NORMAL on adoption night (breadth 58.6% > 50%
  while NIFTY sat below its 150-DMA) — full-size plans again.
- **P2 PROGRESSIVE EXPOSURE — REJECTED** (same matrix): every variant
  (trade-feedback, equity-curve, combo) gives up 3.7-5.7pp CAGR. The
  regime series already does this job; equity-curve feedback double-counts.
- **P3 EPISODIC PIVOTS — ADOPTED as a live capital-bearing entry class**
  (EP matrix, §6E, brief §2B #13): gap >=8% on >=3x prior avg volume,
  close holds the gap, liquidity floors, >=60 bars (young IPOs qualify —
  closes the IREDA blind spot). Stop = gap-day LOW (floor 0.75xATR), same
  two-lot plan. Standalone +1.38R / P2 +0.76R (vs +0.31R for VCP — the
  diversification is the point); COMBINED MAR 2.70 -> 3.58 with LOWER DD.
  Live wiring: `detect_episodic_pivot` in scoring/technical_score.py;
  daily_scan fires kind=EPISODIC PIVOT (event alert, idempotent via state
  `ep_alerted` {sym: bar_date}, 10-day retention); compute_entry_plan
  takes `stop_price=` override; analyst regex + tripwire include the new
  kind; journal_outcomes + dashboard (gold EP chips, own DO tooltip,
  EP-aware status logic — young listings without stage tags are not
  "faded"). Verified end-to-end in an ISOLATED sandbox copy (real journal
  untouched): synthetic TITAGARH gap fired alert + card + both journal
  files + state guard; re-run fired zero duplicates.
- **P4 (fewer slots, {8,10}) — still open**, cheap one-run test, next
  matrix session.

**Landing page + UI scrub (user-requested):** `landing.html` — dark
terminal-aesthetic marketing page (animated scan terminal, ticker of real
system reads, pipeline steps, capability bento, honest evidence strip with
count-up numbers, reduced-motion support, self-contained/no CDN). Pages
now publishes landing as `index.html` and the dashboard at
`/dashboard.html` (daily.yml publish step — NOTE the dashboard URL moved
one path deeper; the old bookmark root now shows the landing page).
"Claude"/model-name references removed from all UI-facing strings
(dashboard buttons/tooltips/committee footer — `ai_picks.json`'s model
field is no longer rendered).

---

## 4. Live production state (as of 2026-07-19)

- **Everything runs in the cloud, verified**: daily cron fires Mon-Fri
  (GitHub delay ~1.5-2h past 13:05 UTC — fine for EOD), journal commits
  nightly, Pages publishes the dashboard, Telegram delivers every run
  (daily heartbeat, user choice). All three secrets set. Laptop Task
  Scheduler scan jobs DISABLED; the only local job is the weekly
  committee (`MultibaggerWeeklyCommittee`, subscription auth).
- **Latest committee picks (2026-07-19, local run on Sunday's fresh
  shortlist)**: CHENNPETRO(HIGH), LAURUSLABS(HIGH), NAVINFLUOR(MED),
  BELRISE(MED), RRKABEL(MED). NOTE: committee output is
  non-deterministic run-to-run (same shortlist, same model, different
  picks) — that's why every run is journaled (`ai_picks_journal.csv`);
  the forward journal judges, not any single run.
- **Forward journal**: ~105 buy signals tracked, expectancy +0.05R
  (tiny sample, 2 weeks — no conclusions yet).
- **First real alerts fired 2026-07-07 18:40**: ~10 transitions incl.
  BANDHANBNK/CARBORUNIV/KARURVYSYA (buys), ACUTAAS/ANANDRATHI/SYRMA/J&KBANK
  (re-entries), CDSL/CHOLAHLDNG/NBCC (anticipation).
- **First real analyst verdicts**: SYRMA, SHILPAMED, LAURUSLABS — all BUY
  (`journal/analyst_verdicts.csv`).
- **First committee run** (Opus 4.7): picked KEI(HIGH)/STLTECH/CHENNPETRO/
  EMCURE/MAHABANK across 5 sectors; externally benchmarked against
  independent analysts and corroborated (STLTECH froth-caution matched).
- **Holdings synced from Zerodha** (2026-07-12): user holds MOSCHIP (200 @
  208.485) and DIACABS (100 @ 224.62 — a stock the system itself alerted
  2026-07-10; seeded stop 195.37, 2.5xATR). Both in `holdings.csv` +
  `positions.csv` with reconstructed stops (flagged as such). Kite sessions
  expire DAILY (SEBI reg) — re-sync needs a fresh login each time, OR use
  `scripts/import_holdings.py` against a Zerodha Console CSV export (no login).
- **Repo pushed to GitHub** (github.com/kartikeyaav/Golden-Stock), all history
  through commit `8746dc3`+; cloud workflows added but **not yet verified
  live** — the first Actions run is a user-triggered step (see §3J/CLOUD.md).

---

## 5. Open items

**Needs the user (small, all documented in CLOUD.md):**
1. ~~Verify the first cloud run~~ **DONE 2026-07-18** — daily + weekly
   both verified green; Yahoo/screener.in both work from Actions IPs.
2. ~~Enable GitHub Pages~~ **DONE** — dashboard live at
   kartikeyaav.github.io/Golden-Stock/, republished every run.
3. ~~Add repo secrets~~ **DONE 2026-07-18** — all three set; Telegram
   delivery verified end-to-end.
4. ~~Disable the laptop Task Scheduler jobs~~ **DONE 2026-07-18** — both
   `MultibaggerDailyScan` and `MultibaggerWeeklyRefresh` are Disabled; cloud is
   the sole runner. (Re-enable only if the cloud is retired — never run both.)
5. **Update `config.RISK.capital`** to the real account equity periodically
   (monthly is enough) — makes the corrected fixed-fractional sizing (§3H)
   actually track reality; live plans size off this constant.

**Needs time:**
6. **Forward journal** must accumulate a few weeks. Then review: do analyst
   verdicts + committee picks beat the mechanical baseline, and do VALIDATED
   entry-fidelity alerts (§3D, `journal/entry_signals.csv`) beat WEAK ones?
   (the real-capital gate, per brief).

**Alert volume — INVESTIGATED 2026-07-09, still the working assumption:**
7. Evidence-locked scan watches the whole universe (611 names), so alert
   volume runs ~4x a naive "150-name watchlist" estimate; this is intentional
   (lock #3 forbids shrinking the watch set) and cost is already capped
   (analyst max 3 dives/day, conviction-ranked). No action needed.

---

## 6. NEXT TASK (what a fresh chat should pick up)

Priority order:
1. **Watch Monday's scan** (first night the revived analyst can fire on a
   real alert; committee cross-checks refresh from stale Jul-9 verdicts)
   and the first few News Radar nights (precision in the wild — if noise
   creeps in, tighten the whitelist in `data/news_radar.py`, never
   blacklist). ALSO first live night for the two 3L adoptions: the breadth
   regime badge (expect NORMAL/full-size — breadth 58.6%) and the EPISODIC
   PIVOT class (~1/week expected; verify the first real one's card, stop,
   analyst dive, and journal rows look right). P4 (fewer slots {8,10})
   remains the one untested cheap matrix cell.
2. **ANANDRATHI promoter-pledge discrepancy** (committee-flagged vs the
   mechanical "no pledge" read) — the user should confirm before treating
   it as a clean pick; re-veto if a standing pledge is real.
3. **Forward-journal review** after a few more settled weeks: do analyst
   verdicts / committee picks / VALIDATED-entry-fidelity alerts beat the
   mechanical baseline out-of-sample? This is the evidence gate before any
   real-capital scale-up. (Journal-earned dim weights are parked on the
   same clock — the news/theme v0 weights get re-derived from outcomes,
   not argued about.)
4. Longer-term strategy work, deliberately PARKED until the forward journal
   has enough data (do not start these speculatively): pyramiding winners,
   regime up-scaling (size UP in strong uptrends, symmetric to the existing
   down-scaling), an IPO-base module for young stocks that can't form
   45-week structures, and relaxing the 15% position-value cap (the one
   sizing lever the matrix flagged as untested).

Do NOT: add fundamental/news/AI signals into the ENTRY or SIZING decision
(evidence-locked, now 11 items in PROJECT_BRIEF.md §2B). AI stays
context/curation/veto only. Do NOT re-run the sizing or entry matrices without
a new pre-registered hypothesis — re-litigating settled evidence wastes the
discipline that makes this system trustworthy.

---

## 7. File map (quick reference)

```
config.py                     all thresholds (RISK, UNIVERSE, STAGE, TECHNICAL, CONVICTION, CATALYST)
data/cache.py                 local OHLCV CSV cache (keep=last on merge)
data/yahoo_loader.py          Yahoo bulk price fetch
data/screener_fetch.py        screener.in page parser (series)
data/announcements_fetch.py   NSE filings feed + daily archive
data/news_fetch.py            Google News (relevance+trust+sentiment filtered)
scoring/stage_tagger.py       mechanical Weinstein stages + watchlist tags
scoring/technical_score.py    trend template, VCP, ATR, two-lot entry plan
scoring/pit_fundamentals.py   point-in-time fundamental scores (known_as_of lags)
scoring/phase_b.py            fundamental dims + vetoes + archetypes (froth-vs-inflection valuation)
scoring/phase_c.py            news/theme/catalyst enrichment dims
scoring/conviction.py         8-dim composite, coverage renorm, veto cap
scoring/regime.py             market_risk_scale (breadth <50% above 200-DMA -> half;
                              reads state/regime.json, NIFTY/150 fallback — 3L)
state/regime.json             nightly breadth snapshot (written by daily_scan tag loop)
scripts/run_sizing_matrix3.py sizing matrix v3: breadth + progressive-exposure overlays
scripts/run_sizing_matrix3b.py v3b follow-up: chop-segment guards (breadth ADOPTED)
scripts/run_ep_matrix.py      EP matrix: episodic-pivot entry class (ADOPTED)
landing.html                  public landing page (Pages index; dashboard at /dashboard.html)
strategy_review_2026-07-19.md journal audit + research + proposal record (3L)
backtest/engine.py            two-lot event-driven engine + regime/stress hooks
backtest/metrics.py           trade/equity/lot stats, costs, benchmark
scripts/daily_scan.py         nightly job core (safe at any hour — cache guard); logs entry_signals.csv
journal/entry_signals.csv     per-buy-alert entry fidelity (VALIDATED/AWAITING/NO VCP) — forward test
scripts/daily_job.py          what Task Scheduler actually runs: scan -> analyst -> paper -> outcomes -> dashboard -> telegram
scripts/weekly_job.py         what Task Scheduler runs Sundays (weekly_refresh wrapper)
scripts/paper_trader.py       analyst paper book: BUY verdicts -> next-open fills -> two-lot managed, ledgered
scripts/ai_analyst.py         daily deep-dive (sonnet-5), conviction-prioritized, idempotent;
                              format-drift tripwire + committee/regime cross-context (3K)
scripts/ai_picks.py           weekly committee (sonnet-5, adaptive thinking) — LOCAL-ONLY now,
                              subscription auth; cloud weekly always --no-ai (3K)
scripts/weekly_committee_local.py  logon/Sunday wrapper: pull -> freshness guard (shortlist
                              commit vs picks stamp) -> committee -> push; stranded-output guard
data/news_radar.py            news-FIRST discovery: whitelist classifier over the NSE filings
                              archive, symbol matching, confluence/urgent ranking (3K)
state/news_radar.json         radar output (dashboard panel + since-window baseline), committed nightly
logs/committee_local.log      local committee wrapper log
scripts/weekly_refresh.py     full weekly chain
scripts/build_dashboard.py    dashboard.html generator (RUN panel + command palette, terminal UI)
scripts/dashboard_server.py   local server: dashboard + run-jobs API (daily / daily_ai / weekly --no-ai; committee excluded)
scripts/run_shortlist.py      ranked shortlist + shortlist_details.json (drawer data; carries
                              score/coverage/label/scored_at, committed by weekly.yml — 3K)
scripts/position_manager.py   open positions vs their two-lot plans
scripts/survivorship_check.py Wayback constituent diff
scripts/import_holdings.py    sync holdings.csv from a Zerodha Console CSV export (no daily Kite login)
scripts/backup_push.py        commits+pushes the forward record to GitHub nightly (non-fatal)
scripts/run_sizing_matrix.py  sizing matrix v1: risk% x position-slot sweep (slots REJECTED, risk saturates)
scripts/run_sizing_matrix2.py sizing matrix v2: cash- vs equity-basis sizing (equity ADOPTED, ~2x corrected CAGR)
sizing_matrix_report.md       v1 table + verdict
sizing_matrix2_report.md      v2 table + verdict (the CAGR-correction evidence)
state/alert_details.json      per-alert drawer detail blob — merged COVERAGE-AWARE with
                              shortlist_details in the dashboard (most-informed read wins
                              dims/score; fresher read contributes news/plan/date — 3K)
state/analyst_health.json     AI analyst heartbeat (ok/failed/idle), read by daily_scan health check
journal/entry_signals.csv     per-buy-alert entry fidelity (VALIDATED/AWAITING TRIGGER/NO VCP BASE) — forward test data
analyst/DEEP_DIVE_PROTOCOL.md analyst standing orders (incl. second-order ecosystem research task)
analyst/PICKS_PROTOCOL.md     committee standing orders (incl. second-order research + analyst-verdict cross-check)
CLOUD.md                      GitHub Actions setup + operations (cache design, secrets, Pages, risks)
.github/workflows/daily.yml   cloud daily pipeline (13:05 UTC Mon-Fri) + Pages publish
.github/workflows/weekly.yml  cloud weekly refresh (04:30 UTC Sun)
tests/                        two-lot + synthetic regression (both green)
```
