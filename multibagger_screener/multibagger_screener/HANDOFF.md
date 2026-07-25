# HANDOFF — Golden-Stock Screener (read this first to continue)

**Last updated: 2026-07-25 evening** (audit F1 shipped; the fundamentals-cache
poisoning bug found and fixed; penny screen corrected; local AI jobs revived).
This is the single "where we are / what's next" doc. For strategy read
`../../PROJECT_BRIEF.md` (it lives at the git root `files/`, NOT in this
folder); for the evidence read `VALIDATION_REPORT.md`; for cloud ops read
`CLOUD.md`. Sections 3-3N below are a chronological work-log (kept for
context) — sections 0/1/2/4/5/6/7 are the CURRENT state, kept fresh.

> **If you are a fresh session: read `AUDIT_2026-07-25.md`, then §3O.**
> Audit Findings 1, 1b, 2, 3, 4 and 5 are DONE (§3O). What remains open is
> listed in §5 and needs either the user or forward time, not code.

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

**Analyst OFF API — laptop-pooled, no cloud AI (2026-07-20, user decision):**
the cloud now runs ZERO AI — daily.yml's analyst step is REMOVED and
ANTHROPIC_API_KEY is no longer surfaced there. Nightly deep-dives run on
the laptop's Claude subscription via `scripts/nightly_analyst_local.py`
(pull → pool guard → `ai_analyst.py --pool` with any stray API key stripped
→ commit+push verdicts → optional local Telegram note). NEW `--pool` mode
in ai_analyst: candidates come from the JOURNAL backlog (buy alerts in the
last 5 days whose latest alert has no verdict at/after it, vetoes excluded,
conviction-ranked, capped at MAX_DIVES_PER_DAY=2 per run), NOT tonight's
file — so **alert nights with the laptop off are POOLED and cleared at the
next session**, strongest first; `card_from_details()` rebuilds the card
from state/alert_details.json for prior-night alerts; pool mode APPENDS to
any existing verdict block (a later session adds to an earlier one).
Triggers: Task Scheduler `MultibaggerNightlyAnalystEvening` (daily 21:30
IST) + Startup-folder `GoldenStockNightlyAnalyst.vbs` (logon +3min) — the
same "runs whenever the laptop is on" pattern as the weekly committee.
pages.yml push-paths gained analyst_verdicts.csv + daily_alerts.md so a
local analyst push republishes the dashboard. VERIFIED live 2026-07-21
01:02: pool had 26, dived top-2 (DCBBANK→WAIT logged+pushed, GRANULES hit
the session limit → NO verdict logged → stayed pooled for next session =
the exact resilience pooling is for); DCBBANK dropped to 25 pending.
Subscription --selftest OK. Weekly committee was already local (§3J/3K) —
now BOTH AI layers are subscription-only; the API key is fully retired.

**Tonight-panel vocabulary fix (2026-07-20, user: "Actionable shows no buys
but Tonight has buy candidates — confusing"):** root cause = the Tonight
panel printed raw scanner kinds (`BUY CANDIDATE`) which read as buys, while
Actionable correctly required the VALIDATED trigger. Tonight is now titled
"Tonight — what the scan saw" and every chip is translated into the
Actionable vocabulary: `BUY CANDIDATE [NO VCP BASE]` → **NEW UPTREND · NO
TRIGGER** (gray), `[AWAITING TRIGGER]` → **NEW UPTREND · WATCH PIVOT**
(amber), `[VALIDATED]` → **BUY SETUP** (green), RE-ENTRY → **RE-ENTRY · …**,
WATCH CLOSELY → **FORMING**, EPISODIC PIVOT → **EP BUY**. Header tooltip
explains Tonight = raw scan, Actionable = decision layer. The word "BUY"
now appears only when the validated trigger actually fired — the two panels
can no longer look contradictory.

**Readability overhaul (2026-07-20 evening, user-driven):** (1) TELEGRAM
now sends a decision-first phone DIGEST built by send_telegram.build_digest
from daily_alerts.md at send time (validated/EP triggers -> "BUY TRIGGER —
act", awaiting -> "Watch + pivot", NO-VCP -> "weak-trend, not buys" — the
SAME vocabulary as the dashboard's DO chips, killing the "phone says BUY,
dashboard says nothing actionable" contradiction; analyst verdicts as
one-liners, top-3 radar hits, positions, regime line, dashboard link;
~500 chars vs the old 20-50KB dump; any digest exception falls back to the
full-report send). (2) Overview verdicts panel = structured cards (symbol +
BUY/SKIP pill + conviction + size + one-line WHY, full memo behind a
toggle) instead of a 4000-char text wall; renamed "AI analyst — tonight's
deep-dives" with a tooltip explaining analyst (nightly per-alert triage)
vs AI Picks (weekly committee portfolio). First production night for the
whole 3L stack ran clean 2026-07-20 15:24Z: 15 alerts, radar LIVE with 5
hits (WABAG order-win CONFLUENCE), breadth 59.2% -> NORMAL, analyst
revived (IPCALAB BUY/MEDIUM/HALF — first verdict since Jul-9).

**End-to-end audit (2026-07-20, same session):** full sweep of workflows,
pipeline, and UI after the 3L adoptions. Fixed: (1) paper_trader's alert
lookup excluded kind=EPISODIC PIVOT — an analyst BUY on an EP alert would
have been permanently SKIP-ledgered ("no matching alert"); (2) pages.yml
cache step SAVED a ~75MB copy per publish, polluting the golden-data-
restore-key namespace the scans restore from -> now actions/cache/restore
(read-only), and ai_picks.json added to its push paths so a local
committee push republishes the dashboard; (3) dashboard.html untracked +
gitignored (was committed once Jul-18 then never updated by the cloud —
permanently stale in git, permanently dirty locally; Pages builds it
fresh); (4) daily_scan: per-symbol try/except around EP+breadth in the tag
loop (one bad CSV must not kill the scan), breadth-snapshot write failure
now degrades to the NIFTY fallback + health line instead of aborting, and
a same-night transition+EP dedupe (EP banner prepends the existing card
instead of double card + double fundamentals fetch); (5) drawer OHLC
coverage extended to recent buy-journal symbols (young EP listings have no
alert_details entry but DO appear in Actionable — chart was empty);
(6) tests/test_episodic_pivot.py added (detection, negative controls,
locked-gap stop floor, plan override, legacy path). Verified: sandbox
end-to-end scan exit 0 (news radar caught its first REAL confluence in the
wild during the test — WABAG order win on a CONFIRMED RS-93 chart),
dashboard badge shows "NORMAL RISK (breadth 58.6%)", landing mobile has
zero horizontal overflow, all 3 workflow YAMLs parse.

---

## 3M. Chart geometry + journal forensics + score coherence (2026-07-21/22)

Three DISPLAY-ONLY dashboard features under the evidence lock — no change to
alerts, tags, entries, stops, sizing, or journaling.

- **Drawer trade geometry + RS line.** The drawer candle chart now draws the
  plan's stop / breakeven / +2.5R price lines and the VCP `pivot` (lightweight
  `createPriceLine`, same pattern as Positions). Lines draw only when the datum
  exists (honest empty state); when a real position exists its own lines show,
  so we add only the pivot there to avoid doubling. Below the candles a ~80px
  "RS vs NIFTY" pane plots stock-close ÷ NIFTY-close, date-matched and
  normalized to 1.0 at window start — computed CLIENT-SIDE from `D.ohlc`+
  `D.nifty` (no new per-stock series embedded), hidden when <10 aligned points.
  Schema: `pivot_price` (from `tag_stock`) added to the drawer detail blob in
  BOTH `run_shortlist.py` and `daily_scan.build_candidate` (parity kept). Old
  blobs without the key null-guard fine; the key populates on the next
  weekly/nightly write.

- **Journal forensics (Journal tab).** New cohort-expectancy table built from
  `journal_outcomes.csv` joined with `entry_signals.csv` (nearest alert date)
  and `analyst_verdicts.csv`: cohorts by signal kind, conviction band
  (<50/50-60/60-70/70+), entry-fidelity label, and analyst verdict — columns
  n / open / stopped / avg-R / med-R / max-R / hit-stop% / avg-MFE / avg-MAE,
  rows shown only at n≥3 (else an "n too small" note). Plus an R-distribution
  histogram (8 bins, CSS bars). `journal_outcomes.py` extended with
  `max_adverse_R` (worst low excursion in R vs suggested-stop risk, mirrors
  `max_favorable_R`) — new derived column, regenerated. Framed as the forward
  evidence that gates real-capital scaling; MAE informs future stop-width tests
  (display only, no stop change now). No A/B machine-vs-AI framing.

- **Score coherence.** Overview Actionable "Conv" column now shows the CURRENT
  read from `_score_cov(sym)` (fallback: journal alert value); when the two
  differ ≥1.0 a subtle `*` marks a "was X at alert (date)" tooltip. Journal
  scorecard "Conv" header labelled "at alert" (frozen record). Drawer header
  appends "(was X at alert)" when the current read diverges ≥1.0 from the
  alert-night conviction. No journaled value touched on disk.

Verified: all 3 test scripts exit 0, build exits 0, payload asserts pass
(forensics kind+conviction cohorts present, pivot_price null-guarded,
USHAMART screener row 71.3 / cov 100 regression intact), main inline script
passes `node --check`, and a served render shows forensics + RS pane + drift
tooltips with zero console errors.

---

## 3N. Penny / nano-cap screen + system audit (2026-07-25)

Two deliverables. The audit is in `AUDIT_2026-07-25.md` (read it — Finding 1
is the most consequential thing found since the equity-basis sizing
correction). Summary of the audit:

- **F1 (critical)** The nightly scan is structurally blind to ~**73%** of the
  entries the backtest validated. Measured: the engine's entry fires 66 times
  in a 60-stock/6.2-year sample (~1.7/week across 611 names); the live tagger
  agrees on 55/66; but only **15 of 55** fell on a tag-TRANSITION day, and
  transitions are the only thing the scan alerts on. Live corroboration
  (through the 07-24 cloud run): **117** buy alerts, **zero** VALIDATED,
  forward expectancy **-0.20R** (was +0.14R on 07-21) vs backtest +1.67R. Fix is
  the EP pattern — fire `validated_entry` as an **event** alert (idempotent by
  `{symbol: bar_date}`), which adds no gate and no signal, it only makes an
  already-validated entry alertable. **NOT implemented — needs your go-ahead
  because it changes what fires nightly.**
- **F2 (high)** `journal_outcomes.py` never applies the two-lot exits and
  enters at the alert-night close, so the forward number is not comparable
  with the backtest number it is meant to gate.
- **F3-F8** gap-through stops booked at exactly -1R · capture-recall headline
  excludes ineligible movers before computing the ratio · **holdings.csv and
  positions.csv are public** in the repo and on Pages · `RISK.capital` still
  the ₹10L placeholder · EP class has not fired yet (watch) · universe
  blindness (addressed below).

**PENNY / NANO-CAP SCREEN — a second, separate universe.** The main system
watches 651 index constituents; real penny names are in none of those indices.
User decisions (2026-07-25): universe = **price < ₹100 OR mcap < ₹1,000 Cr**
(both arms, filterable in the UI); status = **research-only, journaled, zero
capital**.

- **Data spine** `data/nse_all.py` — four free unauthenticated NSE sources,
  all verified working: `EQUITY_L.csv` (symbol master + series + listing date),
  the daily **bhavcopy** (OHLC + turnover + trade count for every security,
  UDiFF zip), `sec_list.csv` (**circuit band** + GSM stage), and
  `api/reportASM` (ASM long/short). Cached under `nse_cache/` (gitignored,
  refetches in ~1 min).
- **The screen's edge is the exclusions, not the score.** In this class you
  lose because you cannot EXIT: a 2-5% band, trade-to-trade (BE) settlement,
  GSM/ASM surveillance or a circuit-locked tape turns a -8% stop into a -40%
  hole. `scripts/build_penny_universe.py` applies hard gates first —
  EQ series only · band >= 10% · no GSM · no ASM · >= ₹0.5 Cr median daily
  turnover · >= 300 trades/day · traded every session · <= 20% of sessions
  circuit-locked · price >= ₹5 · listed >= 1 year. First run:
  **2,479 EQ securities -> 1,251 tradable -> 218 penny/nano** (157 on the price
  arm, 94 on the mcap arm, overlapping; 112 more held pending a market-cap read
  and resolving as the fundamentals cache fills). Every reject keeps its reason
  in `penny_excluded.csv` and the funnel is shown in the UI.
- **Score** `scoring/penny_score.py`, five blocks, coverage-renormalized and
  veto-capped exactly like the main conviction score: inflection 30 (loss->
  profit only counts when the OPM series confirms it — Design Law #5),
  momentum 25 (RS ranked *within the penny universe*, trend template, 52w
  position, volume expansion, EP), ownership 20 (promoter level+trend, pledge,
  any institutional holder at all — most shells have none), tradability 15
  (scored, not just gated), valuation 10 (froth guard only). **Vetoes** cap at
  25: pledge >10%, promoter stake <15%, share capital up >50% in 3y (serial
  dilution is the value-transfer pattern in this class), trailing sales <₹10 Cr.
- **Wiring** `scripts/penny_fundamentals.py` (separate from
  `fetch_fundamentals.py` so penny names can never leak into
  `fundamentals_flat.csv`; shares only the page cache) ·
  `scripts/penny_scan.py` -> `penny_ranked.csv`, `penny_report.md`,
  `state/penny_details.json`, and the append-only `journal/penny_journal.csv`
  (top 20 per run, one row per symbol per day) · **Penny tab** in the dashboard
  (hidden until the scan has run; amber accent, arm/stage/veto filters, funnel
  panel, per-name drawer with the five blocks, risk flags and a "can you get
  out?" table) · added to `weekly_refresh.py` as three non-fatal steps
  (`--skip-penny` to skip) with the fundamentals fetch capped at 150/run.
- **Honesty guardrails baked in:** the tab, the report and the drawer all state
  that no backtest stands behind these reads; suggested discipline (<=5% of
  book in the class, <=1% per name) is shown as guidance, never as a sized
  plan; the reference stop exists only so the journal can score outcomes.
- **First live result:** 59 of 218 (27%) carry a hard veto — JPPOWER (73%
  pledge), HCC (82% pledge), IDEA (share capital +123% in 3y AND negative net
  worth), INOXWIND (+430% dilution), PAISALO (+102% dilution — it ranked #1
  before fundamentals landed, which is the whole argument for putting the
  survival screen ahead of the score). Veto refinement made during the build:
  "no promoter" alone does NOT veto when institutions hold >=25% — IDFC First
  and Ujjivan SFB are widely held by design, not abandoned; they get a risk
  flag instead.
- **The journal was reset once, deliberately.** The first run's rows were
  written before the fundamentals landed (40% coverage, zero vetoes wired) and
  would have poisoned the forward record from day one — same call as the
  synthetic-row removal in the 2026-07-07 audit. It had never been committed or
  published. The record now starts 2026-07-25 with the complete scorer.
- **Tests** `tests/test_penny_screen.py` — 35 checks, all green (vetoes fire
  and cap, coverage renormalizes, the margin guard separates confirmed from
  unconfirmed turnarounds, tradability scoring, risk flags, and the bhavcopy
  liquidity/circuit statistics).

**Known limitation, stated plainly:** the price arm admits large companies with
many shares outstanding (South Indian Bank, Vodafone Idea, Ujjivan). That is
inherent to a price-based definition — filter the tab to the **MCAP** arm for
genuine nano-caps. The mcap arm needs the fundamentals cache filled for the 601
pending names before it is complete.

**The next honest step for this screen** is a pre-registered backtest of the
penny score through `backtest/engine.py` with the same two-lot rules and costs,
against the technical-only baseline. Until that exists these are ideas with a
liquidity check, not signals.

---

## 3O. Cache poisoning, penny correction, AI revival (2026-07-25 evening)

Four user questions drove this session; all four had a real defect behind them.

**THE ROOT-CAUSE BUG — an empty parse cached as a valid record.**
`fetch_company` accepted the `/consolidated/` page whenever the quarterly table
had ROWS. A single-entity filer — most banks and insurers, and any company that
files standalone only — HAS a `/consolidated/` URL, and screener.in renders it
with row labels present and every data column empty. The test passed, the
standalone fallback never fired, and the empty parse was written to cache with
a fresh timestamp, so the age check never retried it.

The damage is asymmetric, which is what made it expensive: a name with no
fundamentals does not score LOW. `build_vetoes` returns `[]` on no data, the
composite renormalizes over whichever blocks survived, and the name floats to
the TOP. Measured at discovery: **52 of 651 main-universe names** (BANDHANBNK,
DCBBANK, KARURVYSYA, DATAPATTNS, STARHEALTH, NETWEB, CUB, GRSE, BDL…) and
**22 of 218 penny names**, and those 22 held penny ranks 1, 2, 3, 4, 6, 8, 9,
12 and 13. Across the penny universe `corr(score, coverage) = -0.335` — the
less the screen knew about a company, the higher it ranked it.

- `data/screener_fetch.py`: new `has_real_data()` (dated quarter columns, or a
  parsed top-ratios box); the fallback now tries both URLs and RAISES when
  neither carries data, so junk can never reach the cache.
- Both fetchers treat an empty cached record as a miss, so this heals itself.
- `scripts/heal_fundamentals_cache.py` (new): one-shot repair + standing audit,
  scoped to the watched universes (`--all` to include ETFs, `--dry-run`).
  **65 of 68 healed**; 3 (AGL, TIPSMUSIC, VMART) have no readable page under
  that symbol code and now fail loudly instead of scoring blind.
- `parser_health` was testing the same wrong thing (`quarters["rows"]`) — fixed.
- Shortlist rescored on real data: 29 names moved ≥4 points (BANDHANBNK -12.9,
  ASTERDM +31.6, KARURVYSYA +12.3, FEDFINA +12.3, WELCORP +15.7).
- `tests/test_screener_fetch.py` (new, network-stubbed) locks the behaviour.

**PENNY SCREEN — three fixes.**
1. **Tier split.** `PennyRead.assessed` (`veto_inputs_present`) separates "we
   checked and it is clean" from "we could not check". Ranking is now tier 0
   assessed-and-clean → tier 1 NOT ASSESSED → tier 2 vetoed, tier first no
   matter which column is sorted; only tier 0 is journaled. After the heal
   tier 1 is empty and coverage is 100% across all 178 names.
2. **Price-arm market-cap ceiling** (`PENNY.price_arm_max_market_cap_cr =
   5000`, user decision). A cheap SHARE is not a small COMPANY — the arm's top
   ranks were Equitas SFB ₹8,961 Cr, Ujjivan SFB ₹13,761 Cr, Bank of
   Maharashtra ₹62,325 Cr, with Vodafone Idea (₹1.4 lakh Cr) inside the
   universe. 222 → **178 names**; overlap with the main index universe fell
   49 → 8; the top of the table is now DJML ₹411 Cr, PREMIERPOL ₹831 Cr,
   ATALREAL ₹382 Cr. The mcap arm is unchanged.
3. **The blank exclusion reason.** 112 tradable names sat in
   `penny_excluded.csv` with an EMPTY `exclude_reason` — neither in the
   universe nor honestly excluded, invisible in a funnel whose whole point is
   that every reject is accounted for. They now carry "held pending a
   market-cap read", and the heal closed all but 15 of them.

The penny journal was consolidated to a single coherent run: 40 rows written
under the broken parse or a superseded universe definition moved to
`journal/quarantine_penny_prefix_2026-07-25.csv` (append-only journals are
never edited silently — same handling as the 2026-07-09 intraday incident).

**FORWARD RULER (Findings 2 + 3) — `plan_followed_R` shipped.**
`journal_outcomes.py` now reports TWO rulers. RAW (unchanged, kept for
continuity) marks to market from the alert-night close and books every stop at
exactly -1R. PLAN-FOLLOWED replays each signal **through `backtest/engine.py`
itself** — next-session-open fill, two-lot exits, gap-aware stop fills, costs —
so it cannot drift from the +1.67R it is compared against. Current read:
raw -0.18R vs plan-followed **-0.23R over 127 signals**.
Also: **17% of signals (25 of 150) carried NO stop** because 2.5×ATR exceeded
the 12% cap and the risk engine skipped them — every R column was blank, so
they were invisible in the record, and they are not a random sample (they are
the most volatile names, where a 30%-win/9.6:1 strategy keeps its right tail).
They are now measured against a reference stop and flagged `plan_sized=False`
(engine gained a `max_stop_pct` measurement hook; default unchanged so every
historical config reproduces). **DIACABS is the case that exposed this**: a
real +1.53R signal showing a blank scorecard row. Both rulers now appear in the
Journal tab (plan R first, raw R beside it, each with a tooltip saying what it
measures).

**Finding 4** — `capture_audit.recall_line` prints BOTH ratios now: raw
(of all top movers) and eligible-only, with the count of structurally
ineligible names stated inline instead of silently leaving the denominator.

**LOCAL AI JOBS WERE NOT RUNNING** (the user's report: "no update on the UI").
- `MultibaggerNightlyAnalystEvening` had `DisallowStartIfOnBatteries=true`,
  `StopIfGoingOnBatteries=true` and no `StartWhenAvailable` — last result
  `0x800710E0` ("the operator or administrator has refused the request", i.e.
  battery). **No verdict since 2026-07-21.** This is the same defect fixed for
  the scan jobs after the 2026-07-09 incident, reintroduced by `schtasks`
  defaults when the task was created on 07-21.
- `MultibaggerWeeklyCommittee` had `ExecutionTimeLimit=PT1H` while a committee
  run takes ~2h50m — the wrapper was killed mid-run on 07-19 (result 1067,
  process aborted), which is what the "stranded output" guard was papering
  over. Raised to 4h.
- Both now: battery-OK, `StartWhenAvailable`, sane limits. Verified live —
  a real pooled run produced STLTECH SKIP and RADICO BUY and pushed them.
- **Dive cadence** (user decision): `MAX_DIVES_PER_DAY` 2 → **4** (the scan
  fires ~8 buy alerts a night; at 2 the analyst saw under a quarter of them),
  and `pending_pool` now applies `POOL_AGE_PENALTY_PER_DAY = 5.0` — a
  queue-only discount so a 4-day-old alert stops outranking tonight's. Nothing
  journaled is touched.

---

## 3P. News memory, Sectors tab, committee unfreeze (2026-07-26)

Four user-requested strategic changes. Commit `b4d1105`, pushed.

### The committee had been dead for a week — inverted timeouts

`ai_picks.json` was dated **19 Jul 17:27** while the shortlist it feeds on was
committed **25 Jul 23:42**. The freshness guard was open the whole time; the
job kept dying. Root cause was three nested budgets in the wrong order:

| layer | was | is |
|---|---|---|
| `ai_picks.TIMEOUT_S` (the CLI) | 900s | **10800s (3h)** |
| `weekly_committee_local` subprocess | 1200s | **12000s (3h20m)** |
| Task Scheduler `ExecutionTimeLimit` | PT4H | PT4H |

The observed run is ~2h50m, so *every* scheduled attempt was killed and the
only picks that ever landed came from an orphaned child a later logon swept
up ("fresh but UNPUSHED" in `logs/committee_local.log`). `TIMEOUT_S` is not the
cost lever — `MAX_TURNS` is; the budget can be generous.

The tab now computes `age_days` at build time, shows a coloured badge, and
past one weekly cycle (≥8d) prints a **NOT THIS WEEK'S READ** banner. The
failure was invisible for a week behind a 10px grey footnote.

### News radar: from a nightly window to a 90-day memory

The complaint was that the radar felt like an independent scan. It was worse
than that — `news_radar.py` windows from the last scan and overwrites its state
file nightly, so it *cannot* express duration. Two measurements shaped the fix
(16 days of archive: 18,307 filings, 4,017 universe-matched, 221 material
across 122 names):

1. **Filings are not stories.** GABRIEL led the raw count with 9 hits = one
   acquisition (HL Klemove) plus the preferential issue funding it, filed 9
   times over 4 days. Counting filings ranks companies by paperwork.
   `data/news_pressure.py` collapses same-company/same-event-class inside
   `NEWS.story_gap_days` (5d) into one story dated at its FIRST filing —
   221 raw → 145 stories — and decays from that date (half-life 21d), so
   re-filing cannot refresh your own pressure.
2. **News does not lead the trigger.** Names with a positive filing produced a
   later BUY/RE-ENTRY alert **6/82 = 7.3%** against a **108/651 = 16.6%**
   universe base rate; names with 2+ distinct stories, **0 of 7**. Sixteen days
   proves nothing on its own, but it points the same direction as every
   rejected overlay here (sector-heat gating, PIT-fundamentals gating).

So the radar was **not** rebuilt as a discovery funnel. It is a dossier and a
risk watch: `NEWS-PRIMED` + the story history is stamped on the card at the
moment the *technical* trigger fires, `news_primed`/`news_pressure`/
`news_stories` are frozen into `entry_signals.csv`, and Journal forensics gains
a **By news memory** cohort. The panel is now three sections — Risk on your
exposure / Building / Tonight's filings — and the drawer shows a 90-day news
memory block. Nothing gates, ranks or sizes.

`state/news_pressure.json` is DERIVED (rebuilt nightly from the committed
archive). The only forward RECORD is the frozen columns — a cohort you can
recompute proves nothing.

### Sectors tab (`scoring/themes.py`)

18 cross-industry themes over the same universe the scan watches. NSE's 22
macro-industries are accounting categories: BEL and DATAPATTNS are one story in
different buckets; APARINDS and POWERINDIA are one grid-capex trade. Membership
= explicit seeds + name/industry patterns, and a stock may sit in several
themes on purpose.

**Heat is a RANK across themes, not an absolute score.** The absolute version
was built first and compressed all 18 into 33–41 — arithmetically true (the
whole tape moves together) and useless for ordering a reading queue. Blend is
3m move 45 / chart breadth 40 / news per name 15; themes under 4 names are
flagged `thin`, excluded from the ranking and sorted last, because a two-name
median is noise.

Two greedy patterns caught against the real name list, both worth remembering:
`\bhealthcare\b` is the NSE *industry* string and dragged all 63 pharma names
into a hospitals theme; `\blabs?\b` then caught Alkem/Ipca/Laurus
**Laboratories**, which are drug makers.

The banner states the binding evidence: sector heat was tested as an entry
filter and REJECTED (matrix v2 config E: +0.22R at a 40% gate, +0.11R at 60%,
vs +1.27R ungated — monotonic the wrong way). This tab orients research; every
name still has to fire the same trigger. `state/themes.json` is written for the
weekly committee, which now receives the map and writes a `THEME READ` block
into `ai_picks.json` (absent = mechanical table stands alone).

### Penny tab

Raw filenames removed from user-facing copy, the five-line intro cut to two,
meta reshaped as a funnel line, type scale normalised to the rest of the app.

### Note for the next editor

`entry_signals.csv` gained three columns. `_widen_entry_signals_header()`
migrates value-preservingly and **raises** on anything that is not a clean
prefix — appending wide rows under a narrow header would silently shift every
value in the one file that has to stay trustworthy.

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
  [redacted]) and DIACABS (100 @ [redacted] — a stock the system itself alerted
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

6. ~~DECIDE: implement Audit Finding 1?~~ **DONE 2026-07-25** — `BUY TRIGGER`
   fires as an event alert (commit `c4744a9`), F1b labels the EXTENDED
   divergence, and F2/F3's `plan_followed_R` landed the same day (§3O).
7. **MAKE THE REPO PRIVATE** — user chose this 2026-07-25 for Finding 5
   (`holdings.csv` / `positions.csv` are real personal financial data on a
   public repo + public Pages site). Not doable from here (no `gh` auth):
   github.com/kartikeyaav/Golden-Stock → Settings → General → Danger Zone →
   Change visibility → Private. **CAVEAT the user must weigh first:** GitHub
   Pages from a PRIVATE repo requires a paid plan (Pro/Team/Enterprise). On
   the free plan, going private takes `kartikeyaav.github.io/Golden-Stock/`
   offline — the dashboard is then local-only (`dashboard_server.py`) or via
   the run artifact. If that trade is unacceptable, the fallback is scrubbing
   both CSVs from the repo and its history and teaching `daily.yml` /
   `backup_push.py` not to commit them.

**Needs time:**
8. **Forward journal** must accumulate a few weeks. Then review: do analyst
   verdicts + committee picks beat the mechanical baseline, and do VALIDATED
   entry-fidelity alerts (§3D, `journal/entry_signals.csv`) beat WEAK ones?
   (the real-capital gate, per brief). **Caveat:** Finding 2 says the current
   forward number is not comparable to the backtest number — this review only
   means something after §6 Task 1c lands.

**Alert volume — INVESTIGATED 2026-07-09, still the working assumption:**
9. Evidence-locked scan watches the whole universe (611 names), so alert
   volume runs ~4x a naive "150-name watchlist" estimate; this is intentional
   (lock #3 forbids shrinking the watch set) and cost is already capped
   (analyst max 3 dives/day, conviction-ranked). No action needed.

---

## 6. NEXT TASK (what a fresh chat should pick up)

**Task 1 below is DONE (2026-07-25) — kept for the reasoning trail; see §3O
for what shipped.** The live open items are §5 #7 (make the repo private, one
user action with a Pages caveat) and #5 (`RISK.capital`, user deferred). Then
Task 3.2 (a pre-registered penny backtest) is the only thing that can move the
penny screen off "research", and Task 2 (the playground) is user-deferred.

**Added 2026-07-26 (§3P):** two new layers are now accruing forward evidence
and neither may be given weight until it has a number.
- **NEWS-PRIMED cohort.** `entry_signals.csv` freezes the news read per alert;
  Journal forensics renders it as "By news memory". The 16-day pre-study says
  news does NOT lead the trigger (7.3% vs a 16.6% base rate), so the prior is
  that this cohort shows nothing. Revisit at n ≥ 30 per arm. If primed alerts
  do not beat unprimed, delete the label — do not keep it because the panel
  looks good.
- **Theme heat.** Untested by construction and explicitly barred from gating
  (matrix v2 config E rejected sector gating outright). If it is ever proposed
  as an input, it needs its own pre-registered config, not an argument.

Also worth a cheap check next session: the committee is due to run Sunday
11:00 IST against the fixed timeouts. Confirm `ai_picks.json` refreshed and
that `logs/committee_local.log` shows a clean commit+push rather than another
"fresh but UNPUSHED" recovery.

---

### ~~TASK 1~~ DONE — make the validated entry alertable  [F1 + F2 together]

**Why:** the backtested entry (+1.67R) fires ~1.7×/week across the universe,
but the scan only alerts on tag TRANSITIONS, and only 27% of validated entries
land on a transition day. Result: **117 live buy alerts, zero validated,
forward -0.20R.** Full measurements + how to re-run them: `AUDIT_2026-07-25.md`.

**Ask the user to confirm before shipping** — it changes what arrives on their
phone each night. Then:

**1a. `scripts/daily_scan.py` — new event alert.** Copy the EPISODIC PIVOT
wiring exactly (it already solved this shape of problem; see the `ep_hits` /
`ep_alerted` blocks):
  - the tag loop already computes `tag_results[sym]` for every name, and
    `tag_stock` already returns `validated_entry` / `pivot_price` /
    `breakout_volume_ratio` — nothing new is computed, nothing is gated
  - collect `entry_hits = {sym: tr for sym, tr in tag_results.items()
    if tr.get("validated_entry")}`
  - fire `kind = "BUY TRIGGER"` for each, transition or not
  - idempotency: `state["entry_alerted"] = {sym: last_date}`, 10-day retention,
    written by `save_state` alongside `ep_alerted` — a catch-up re-run of the
    same bar must not double-journal
  - same-night dedupe with an existing transition card for that symbol
    (`card_idx`) — prepend a banner, do not build a second card
  - expected volume ~1-2/week, so no cost concern; `ai_analyst` picks them up
    automatically once its buy-kind regex includes the new kind (**check
    `ai_analyst.py` and `paper_trader.py` — both filter on kind strings; the
    Jul-20 audit found paper_trader silently dropping EPISODIC PIVOT for
    exactly this reason**)

**1b. Label the EXTENDED divergence (F1b).** 9 of 66 engine entries land on
days the tagger calls EXTENDED and refuses to label. The backtest TOOK those.
Do not change the tag — add the label (`entry_status = "VALIDATED (EXTENDED)"`)
so the forward journal can measure whether skipping them helps or hurts.

**1c. `scripts/journal_outcomes.py` — measure what the backtest measured (F2).**
Today it only reports open/stopped-at-exactly-1R, entered at the alert-night
close. Add a `plan_followed_R` column alongside the existing raw read:
  - fill at the NEXT session's open (the backtest's stress-validated fill)
  - apply the two-lot rules: partial at +2.5R, stop→breakeven at +1.5R,
    trading lot trails the 50-DMA, core lot exits on a weekly close below the
    150-DMA (reuse `position_manager.check_positions` logic rather than
    re-implementing it)
  - book gap-throughs at the actual gap fill, not -1.0R (F3)
  - keep both columns and label them in the Journal tab — the raw read stays
    for continuity, `plan_followed_R` is the one comparable to +1.67R

**Acceptance:** a synthetic fixture where a stock is CONFIRMED for 10 days and
breaks out on day 7 must produce exactly one BUY TRIGGER alert, one
`entry_signals.csv` row, zero duplicates on re-run, and a `plan_followed_R`
that matches a hand-computed two-lot result. Test in an **isolated sandbox copy
with `--state-file`** — note the Jul-07 lesson that `--state-file` runs still
write the real journal, so copy the project dir rather than trusting the flag.

---

### TASK 2 — the playground (user deferred it 2026-07-25: "we will do the playground later")

Multi-user paper trading, ₹1L starting capital, driven off the screener.
Decisions already taken so a fresh session does not re-litigate them:

- **It needs a backend.** The dashboard is a static file on GitHub Pages;
  real logins are impossible there. Build ONE engine in Python (accounts,
  orders, fills, P&L) + a stdlib `sqlite3` store + a thin HTTP API, and have
  the Playground tab talk to it. **Do not** write a second engine in JS for
  the static copy — this project's recurring bug class is two surfaces
  drifting apart.
- **Separate server from `dashboard_server.py`.** That one binds 127.0.0.1 and
  exposes RUN buttons; a multi-user playground must never sit behind the same
  door. New `scripts/playground_server.py`, no run-job endpoints.
- **Fills at the NEXT session's open**, same convention as `paper_trader.py`
  and the validated stress mode — it also makes "buy at yesterday's close
  knowing today's move" impossible.
- **Order tickets pre-filled from the mechanical plan**, scaled to ₹1L
  (1.25% risk, 15% position-value cap) so the playground teaches the actual
  discipline and generates data on whether people who follow the plan do better.
- **Task 4 (privacy) is a hard prerequisite** — do not add other people's
  accounts to a system that publishes the owner's positions.

---

### TASK 3 — penny screen follow-ups (`§3N` shipped, `§3O` corrected)

1. ~~Close the mcap arm.~~ **DONE 2026-07-25** — the pending list went 112 → 15
   once the cache-poisoning bug (§3O) was fixed and the fundamentals fetched;
   every one of the 178 universe names now has a market-cap reading. The
   weekly job keeps the remainder closing at 150 fetches/run.
2. **Pre-registered penny backtest** — the honest next step, and the only thing
   that can move this screen off "research". Run the penny universe through
   `backtest/engine.py` with the same two-lot rules and costs, against the
   technical-only baseline. Register the hypothesis and the pass criteria
   BEFORE running it (the discipline that killed 13 prior overlays).
   Caveat to state up front: the penny universe is survivor-biased worse than
   the index universe — delisted shells are simply gone from the master.
3. Watch the first few weekly runs for NSE rate-limiting from GitHub Actions
   IPs (bhavcopy + `api/reportASM`). All penny steps are non-fatal, so a block
   shows up as a skipped step, not a broken pipeline.

---

### TASK 4 — privacy (F5): DECIDED, awaiting one user click

The user chose **make the repo private** (2026-07-25). See §5 #7 for the exact
steps and the GitHub-Pages-on-a-private-repo caveat they need to weigh. Do not
force-push a history rewrite unless they change their mind and pick the scrub
option instead.

---

### TASK 5 — the standing watch list (unchanged, lower priority than the above)

- **ANANDRATHI promoter-pledge discrepancy** — committee-flagged vs the
  mechanical "no pledge" read; confirm before treating it as a clean pick.
- **EP class has still never fired** (adopted 2026-07-19). ~1/week expected.
  If it is still zero by mid-August, that is a finding, not weather.
- **News Radar precision in the wild** — if noise creeps in, tighten the
  whitelist in `data/news_radar.py`, never blacklist.
- **P4 (fewer slots {8,10})** remains the one cheap untested matrix cell.
- **Forward-journal review** once the cohort matures: do analyst verdicts,
  committee picks and VALIDATED-fidelity alerts beat the mechanical baseline?
  This is the real-capital gate. Note Task 1c changes the ruler — the review
  is only meaningful after it lands.
- **Parked until the journal has data** (do not start speculatively):
  pyramiding winners, regime up-scaling, an IPO-base module, relaxing the 15%
  position-value cap.

---

**Do NOT:** add fundamental/news/AI signals into the ENTRY or SIZING decision
(evidence-locked, 11 items in PROJECT_BRIEF.md §2B — the penny screen lives
outside that lock precisely so it cannot contaminate it, see §2C). AI stays
context/curation/veto only. Do NOT re-run the sizing or entry matrices without
a new pre-registered hypothesis — re-litigating settled evidence wastes the
discipline that makes this system trustworthy.

**Environment gotcha added 2026-07-25:** the Bash tool here is Git Bash.
PowerShell here-strings (`@'...'@`) do not work in it and will silently corrupt
a `git commit -m` message. Use a heredoc, or `git commit -F file`.

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
scripts/nightly_analyst_local.py  logon(+3m)/21:30-IST wrapper: pull -> pool guard ->
                              ai_analyst.py --pool (subscription, no API) -> push verdicts;
                              clears the buy-alert backlog across sessions the laptop is on
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
AUDIT_2026-07-25.md           system audit: the validated-entry visibility gap (F1) + 7 more, with measurements
data/nse_all.py               whole NSE cash market: symbol master, bhavcopy, circuit band + GSM, ASM
scripts/build_penny_universe.py  penny/nano universe = tradability gates first, then price<100 OR mcap<1000Cr
scripts/penny_fundamentals.py    screener.in for penny names (never touches fundamentals_flat.csv)
scoring/penny_score.py        5-block penny score + survival vetoes (research only, no backtest)
scripts/penny_scan.py         rank + report + append-only journal/penny_journal.csv
penny_universe.csv            names that survived the gates      penny_excluded.csv  every reject + reason
penny_ranked.csv              scored + ranked                    penny_report.md     the readable output
state/penny_details.json      drawer blob   state/penny_meta.json  funnel counts (single source for the UI)
tests/test_penny_screen.py    32 checks on the penny screen's judgement
scripts/run_sizing_matrix.py  sizing matrix v1: risk% x position-slot sweep (slots REJECTED, risk saturates)
scripts/run_sizing_matrix2.py sizing matrix v2: cash- vs equity-basis sizing (equity ADOPTED, ~2x corrected CAGR)
sizing_matrix_report.md       v1 table + verdict
sizing_matrix2_report.md      v2 table + verdict (the CAGR-correction evidence)
state/alert_details.json      per-alert drawer detail blob — merged COVERAGE-AWARE with
                              shortlist_details in the dashboard (most-informed read wins
                              dims/score; fresher read contributes news/plan/date — 3K)
state/analyst_health.json     AI analyst heartbeat (ok/failed/idle), read by daily_scan health check
journal/entry_signals.csv     per-buy-alert entry fidelity (VALIDATED/AWAITING TRIGGER/NO VCP BASE) — forward test
                              data; also freezes news_primed/news_pressure/news_stories per alert (3P)
data/news_pressure.py         90d story-level news memory (dedupes repeat filings of one event, decays from
                              the first filing). Derived — state/news_pressure.json is rebuildable
scoring/themes.py             18 cross-industry themes + relative heat rank (Sectors tab; research only —
                              sector gating was tested and REJECTED, matrix v2 config E)
state/themes.json             theme table for the weekly committee's THEME READ block
tests/test_news_pressure.py   story dedupe + decay + primed threshold (8 pytest checks)
tests/test_themes.py          membership traps + heat spread (9 pytest checks)
analyst/DEEP_DIVE_PROTOCOL.md analyst standing orders (incl. second-order ecosystem research task)
analyst/PICKS_PROTOCOL.md     committee standing orders (incl. second-order research + analyst-verdict cross-check)
CLOUD.md                      GitHub Actions setup + operations (cache design, secrets, Pages, risks)
.github/workflows/daily.yml   cloud daily pipeline (13:05 UTC Mon-Fri) + Pages publish
.github/workflows/weekly.yml  cloud weekly refresh (04:30 UTC Sun)
tests/                        two-lot + synthetic regression (both green)
```
