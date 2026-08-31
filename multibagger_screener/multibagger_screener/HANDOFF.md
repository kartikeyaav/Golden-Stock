# HANDOFF — Golden-Stock Screener (read this first to continue)

**Last updated: 2026-07-26** (capital gate PRE-REGISTERED; exit-risk
surveillance on the main universe; freshness header; stale KPIs corrected;
dashboard + landing REBUILT as a trading terminal with a 615-stock universe
map — see §3Q; the penny universe now settles its own arms once market caps
land, in both directions — see §3R).
This is the single "where we are / what's next" doc. For strategy read
`../../PROJECT_BRIEF.md` (it lives at the git root `files/`, NOT in this
folder); for the evidence read `VALIDATION_REPORT.md`; for cloud ops read
`CLOUD.md`. Sections 3-3N below are a chronological work-log (kept for
context) — sections 0/1/2/4/5/6/7 are the CURRENT state, kept fresh.

> **2026-07-27: the gate's pass condition was RE-REGISTERED at n=0 — the flat
> +0.50R was on a different scale from the ruler that measures it. Read
> `CAPITAL_GATE.md` §4 and §9, then §3S, before quoting any gate number.**

> **If you are a fresh session: read `CAPITAL_GATE.md`, then §3Q, then §5.**
> The gate is registered and OPEN at 0/40 — it is the number this project
> exists to produce, and §6 says do not add features until it has a sample.
> For the audit trail behind the current scan, `AUDIT_2026-07-25.md` + §3O.
> What remains open is in §5 and needs the user or forward time, not code.

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
(backtest-validated, never AI/fundamental-gated). **As of 2026-07-26 the whole
thing points at one number: a PRE-REGISTERED capital gate (`CAPITAL_GATE.md`)
that decides whether real money is ever deployed — 40 validated signals at
>= +0.50R, beating a momentum ETF, by 2026-12-31. It stands at 0/40 and every
threshold was fixed before the cohort existed.** The dashboard is a trading
terminal built around it (universe heatmap of all 615 watched names, gate and
regime dials, live tape, Ctrl+K palette, decision-first Actionable panel).
**The backtested read was corrected 2026-07-12: sizing was measured off
remaining cash, undersizing every late entry — equity-basis sizing is the same
rules, same entries, just honest measurement, and it roughly DOUBLES the CAGR
read** (see §3H). **The system is complete, live and laptop-independent
— and has NOT yet demonstrated its validated entry in the forward record.**
The scan was structurally blind to 73% of the entries the backtest took until
2026-07-25 (audit F1); the corrected trigger fires for the first time from
2026-07-27, which is when the gate cohort starts. What remains is time and
discipline, not code.

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
Universe -> liquidity filter -> RS-percentile focus list (~300, reporting-only)
-> mechanical stage tags (every name with enough history — ~615 tonight, the
FULL universe, evidence lock; both counts drift with the weekly refresh, so
read them off the dashboard funnel line rather than trusting this sentence)
-> transition diff vs saved state -> alerts on state changes, **plus the
validated entry fired as an EVENT** (`BUY TRIGGER`, adopted 2026-07-25 — audit
F1 found transitions alone missed 73% of the entries the backtest took)
-> per-alert: 8-dim conviction score + vetoes + two-lot plan +
**entry-fidelity label** (VALIDATED = exact backtested VCP-pivot+volume
breakout / AWAITING TRIGGER = base live, pivot not cleared / NO VCP BASE =
trend read only — logged to `journal/entry_signals.csv`; VALIDATED is now the
cohort the capital gate judges, see §3Q).
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

**Dashboard** (`dashboard.html`, single self-contained SPA — rebuilt as a
trading terminal 2026-07-26, §3Q): tabs = Overview / AI Picks / Sectors /
Screener (full 615-name universe with a "Focus only" chip, cap-tier + tag
filters) / Penny / Positions / Journal. A **live tape** runs above every tab.
Overview opens on three instruments — **capital-gate dial** (the number the
system exists to produce), **market-regime dial** (the breadth rule that sizes
tonight's trades) and tonight's scan — then the **UNIVERSE MAP**: all 615
watched stocks as one grid, ranked by relative strength, coloured by stage,
ringed if alerted in the last 7 days. **Ctrl+K (or `/`) opens a fuzzy
search palette** across every watched stock -> arrow-nav -> Enter opens the
drawer. Below the map, the **Actionable panel** (the only thing you act from):
headline verdict line, every row a plain-English DO chip (BUY SETUP / WATCH /
WEAK / WAIT / IGNORE / DO NOT BUY), filter chips (do-kind isolate-on-click +
conviction floor), resolved signals collapsed. Click any stock anywhere ->
drawer with candlestick chart + why-this-score + plan + news + fundamental
trend charts + an **exit-risk panel** when the name carries an ASM/GSM/band
flag (drawer data covers every alerted name, not just the weekly shortlist —
§3F). A **freshness strip** in the header ages every subsystem against its own
cadence. KPI strip shows the ADOPTED config's ideal/stressed pairs, sourced
from `config.EVIDENCE` (it was hardcoded and two adoptions stale until §3Q).

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

## 3Q. The capital gate, exit risk, and a UI that states its own age (2026-07-26)

Four changes, all driven by one observation: the system had grown six
information surfaces while the single number it exists to produce — a positive
forward expectancy — had no threshold, no deadline and no widget.

### The gate is now pre-registered (`CAPITAL_GATE.md`, `config.GATE`)

Written the day BEFORE the first scan that can produce a qualifying signal, so
the cohort it judges did not exist when the numbers were chosen. **40 validated
signals, mean `plan_followed_R` ≥ +0.50R, must beat a momentum-quality ETF over
the same window, ≤55% stop-outs, ≤60% of gains from one trade, by 2026-12-31.**
A pass authorizes 25% of intended capital, not the account. §8 of that file
carries the anti-gaming clauses (no post-hoc exclusions, no mid-flight ruler
swaps, no swapping the benchmark for a weaker one); §9 is the amendment log.

`scripts/gate_status.py` computes the standing into `state/gate.json` and keeps
**three populations apart**, which is the substantive part:

- **GATE COHORT** — `BUY TRIGGER` + `EPISODIC PIVOT` from 2026-07-25. Currently
  **0 of 40**; the trigger shipped after the last scan, so the first can arrive
  Monday 07-27.
- **LEGACY** — the 150 pre-fix transition alerts, **−0.27R** (plan ruler, sized
  only). Zero of them were the validated entry (F1). Kept visible, reported
  apart, never folded in. Judging the strategy by them is as wrong as judging
  it by the backtest.
- **EXCLUDED** — `VALIDATED (EXTENDED)` (the live system skips those entries)
  and unsized signals (the risk engine refuses them). Both measured, neither
  averaged in.

Note the trap found while building it: applying the closed-or-aged rule to a
17-day-old journal selects only the stop-outs and reports −1.81R. The gate
needs that rule; the running read must not use it. Both are computed and
labelled rather than one being quietly chosen.

### The benchmark is now a pass condition, not a footnote

`MOMENTUM100` (Mirae Nifty MidSmallcap400 Momentum Quality 100 ETF, Yahoo
`MOM100.NS`, cached back to 2019) refreshes with every price update. Same
factor exposure as this system, one click, ~0.5%/yr. **Trailing 12m: ETF
+7.6% vs NIFTY −3.7%** — that is the bar. Until the cohort exists the gate
window is empty, so the card shows trailing 3m/12m context explicitly labelled
as NOT the test (substituting a friendlier window is what §8 forbids).

### Exit risk on the main universe (`scripts/surveillance_snapshot.py`)

The penny screen has always gated on ASM/GSM/circuit band/settlement series,
on the argument that you lose in that class because you cannot GET OUT. The
main 651 were never checked. They are now: **66 of 652 carry a flag**, and the
first run found them in exactly the places that matter —

- **DIACABS, a live holding, is on a 5% band.** Its stop sits 18% below the
  last price: **four consecutive limit-down sessions away.** It cannot fill in
  one move. The drawer now says this in those words.
- **STLTECH** (alerted within 7 days): ASM + 5% band + BE trade-to-trade.
- 2 of 4 committee picks flagged (PARAS on ASM); 7 of 61 names alerted in the
  last week.

**DISPLAY ONLY — it flags, it does not gate.** No matrix has tested
surveillance as an entry filter, and the evidence lock says a gate needs
pre-registered evidence. A missing snapshot renders as UNKNOWN, never clean.

### The UI states its own age, and stopped lying about its own numbers

- **Freshness strip** in the header: one pip per moving part, each judged
  against ITS OWN cadence (a weekly committee at 3 days is calm, a nightly
  analyst at 3 days is loud). Both AI layers have died silently for ~a week
  each and on both occasions the page looked completely normal.
- **The KPI strip was two adoptions stale.** It read +1.67R / 47.4% / −18.5%
  — sizing-matrix v2 config B — after breadth regime AND the EP class were
  adopted. Now from `config.EVIDENCE`: **+1.34R / 54.5% / −15.2% / MAR 3.58**
  (6E COMBINED VCP+EP), with the stressed pair shown underneath instead of
  hidden in a tooltip, and a carried caveat that the two adoptions were
  measured separately and their gains are NOT added.
- **The Market-trend tooltip still said the NIFTY/150-DMA sets position size.**
  It has not since 2026-07-19. A live line under the chart now names the rule
  actually in force and tonight's breadth reading.
- Also fixed: `+1.27R` (superseded cash-basis) in the anticipation note,
  hardcoded `1.25%`/`₹10L`/`611`/`~320`, "since 2026-07-05" (journal starts
  07-07), "max 3 dives" (it is 4).

### Visual rebuild — v6 "terminal" (same day, second pass)

**The first pass failed and the user was right about why.** It kept the v4
skeleton and repainted it: new tokens, glass nav, softer shadows. The result
still read as a dark admin panel — paragraphs where a terminal shows numbers,
flat grey boxes of equal visual weight, and **no market visualisation anywhere
above the fold.** Lesson worth keeping: a token swap is not a redesign. What
changed the verdict was changing what is ON the page, not how it is shaded.

Rebuilt against how trading desks actually present data — dense monospace
numerics, high contrast on near-black, heatmaps, little whitespace:

- **UNIVERSE MAP** (`#heatmap`) — all 615 watched stocks as one grid, ranked
  by relative strength, coloured by chart stage, with opacity carrying
  strength so the SHAPE of the market reads at a glance. Names alerted in the
  last 7 days carry a ring; any cell opens the standard drawer. This is the
  panel every earlier version was missing, and it is the one that made the
  page look like a market instead of a report.
- **Instrument row** replaces the prose hero: capital-gate dial + condition
  LEDs · market-regime dial (the breadth rule that actually sizes tonight's
  trades) · tonight's-scan readout.
- **Live tape** across the top. Real reads only — gate, regime, stage counts,
  benchmark, exit-risk count, movers. A tape of invented numbers on a system
  whose whole claim is an auditable record would be the one unforgivable
  decoration; if you extend it, keep that rule.
- Panels became terminal windows (title bar, accent tick, 6px radius); tables
  went dense monospace with a green edge-glow on hover; `spark()` now draws a
  gradient-filled area with a glowing last point, and the Actionable table
  carries a 60d sparkline column.
- `landing.html` moved to the same palette and leads with the same live
  universe map, built from `state/tags_state.json` + `focus_list.csv`.

`landing.html` is **generated** by `scripts/build_landing.py` from the same
state the dashboard reads. The old hand-written page advertised +1.67R and a
32.5% CAGR after both were superseded, and its terminal mock still described
the retired NIFTY regime rule. Positioning moved from "autonomous golden-stock
hunting" to the only claim that is both true and hard to copy: *the track
record is the product* — with a "what it refuses" section listing every
rejected overlay and a "what this is not" section stating the forward record is
unproven.

### Notes for the next editor (all cost real debugging time)

- **`main` needs `min-width:0`.** As a flex child it cannot shrink below its
  widest descendant, so one unwrapped strip (the health pips) pushed the whole
  page 250px wide. The same fix already existed on `.grid2>div`; it was missing
  on `main` itself.
- **Function-hoisting is not binding-hoisting.** `spark()` is called by the
  instrument panels ~400 lines above its own source. A `let` declared beside it
  is still in the temporal dead zone at that moment — the ReferenceError blanked
  every panel below the tape, and the page looked *plausible* rather than
  broken. Its counter now lives on the function (`spark._n`). Anything the
  instruments call must own its state the same way.
- **The preview browser throttles `requestAnimationFrame` and CSS transitions**
  when the tab is not painting, so rAF-based reveals silently never run there.
  Use `setTimeout`. Custom properties inside `@keyframes` also failed to
  substitute — an early progress ring sat at zero fill while printing a real
  number. Dial/ring offsets are now static attributes nudged by `setTimeout`.
  **A gauge that lies is worse than one that does not move.**
- **Screenshots work; large viewports time out.** 1280x820 and 375x812 capture
  fine, 1440x900 does not. For below-the-fold, set a tall viewport (1280x1700)
  rather than scrolling — scrolling produced blank captures.

---

## 3R. Sales-page rewrite, duplicate-panel cull, penny arm defect (2026-07-26)

User feedback on the v6 terminal, five items. Two of them turned out to have a
real defect behind them rather than a styling problem.

### The landing page was arguing against itself

It carried a `CORRECTED — Its own headline numbers` card ("the scan was blind
to 73% of the entries it had validated, a caching bug was ranking companies
higher the less it knew about them") and a limitation reading "the AI layers
are unproven and on probation... both have silently broken for a week at a
time". Both are true, both belong in `HANDOFF.md` / `VALIDATION_REPORT.md` /
the dashboard, and neither belongs on the page whose job is to make someone
want to open the terminal. A marketing page narrating its own bug history
reads as doubt, not candour. The `build_landing.py` docstring now states that
boundary so the next editor does not re-import it.

Rewritten around what was built rather than what was fixed: hero leads with
the nightly desk, `#evidence` replaces the old backtest strip, limitations
became four professional lines. The `CORRECTED` card was replaced with a real
rejection (risk 1.75%/2.5%, both breached the drawdown limit) so the refusals
section still has six.

**+1.34R is the honest unit and a terrible headline** — it looks like 1.34 of
something small. R is a MULTIPLE of what a trade risks, so the page now
converts it once, explicitly, in a three-panel row: `₹1 at risk` →
`₹2.34 back` → `9.6:1 payoff at a 31% win rate`, with the compounding stated
underneath (`₹10 lakh → ₹36.9 lakh` over the window, `₹23.3 lakh` stressed).
Every figure still comes from `config.EVIDENCE`; nothing was invented to make
the number look bigger.

### Overview: three panels were answering questions another panel had answered

- **Stage tally** — its five counts were already in the universe-map legend.
  The proportion bar moved INTO that legend (`#hmdist`), beside the grid it
  describes instead of 1,500px below it.
- **Sector strength** — 18 NSE-industry bars, 449px, while the Sectors tab
  ranks the same universe by actual theme and does it better. Moved to the
  Sectors tab as a "By NSE industry" cross-reference. One tab now owns sector
  reading (the standing "collaborative, not parallel" rule).
- **Market trend** — a 190px NIFTY chart under a caption explaining that NIFTY
  stopped setting position size in July. The market-regime instrument at the
  top already carries the live rule, its reading and a NIFTY sparkline. Cut.
  (Also removes one lightweight-charts canvas from the Overview.)
- **Legend** — a collapsed `<details>`. A legend you have to click is a legend
  that does not exist. The state half duplicated the map legend; the ACTION
  half moved inline into the Actionable header (`#actkey`).
- **News radar** stood **961px** — a full screen of filings above the evidence
  strip, for a signal class this project's own measurement says does not lead
  the trigger (7.3% vs a 16.6% base rate). `Risk on your exposure` — the one
  actionable class — was promoted to its own red panel beside the transitions
  list; Building capped at 6, Tonight at 8. Panel is now 696px, below the
  decision layer.

Overview: ~3,620px → ~2,650px.

### The instrument row was not actually a row

All three cards shared an outer box and nothing else. `#marketinst` centred its
gauge against a taller text column while `#gatecard` top-aligned its own, so
two circular dials 250px apart sat 26px out of line, and each panel left a
different amount of dead space at its foot (15 / 42 / 48px). This is what the
user meant by "the capital gate info section is somewhere in the middle".
`.inst` is now a flex column, `.instbody` fills it, and `.instrow` /
`.instside` / `.instcol` give all three panels one internal grid. Gauges now
share a baseline (y=256) and all three bodies end on the same line (y=458).

### PENNY: 22% of a nano-cap universe were not nano-caps

`build_penny_universe.py`: `price_arm = cheap & ~(mcap >= ceiling)`. When
`market_cap_cr` is NaN — the common case at universe-build time, since caps
resolve later on a `penny_fundamentals` run — `NaN >= ceiling` is False and
`~False` is True, so **every** cheap share enters the price arm, and the arm is
never re-evaluated once the cap lands. Measured on `penny_ranked.csv`
(2026-07-24): **34 of 153 names** sat above the ₹5,000 Cr ceiling the user
registered on 2026-07-25 — IDEA at ₹1.42 lakh Cr, IRFC ₹1.15 lakh Cr, IDBI,
NTPCGREEN, NHPC, NMDC, YESBANK, SUZLON. UJJIVANSFB (₹13.8k Cr) ranked #1. This
is most of why the tab "looked off": the top of a nano-cap screen was PSU
large-caps.

`_build_penny` re-applied the ceiling at READ time as a stopgap (universe
153 → 113). **The durable fix landed the same evening — see §3R.**

Also on that tab: the exclusion funnel printed its own scrubbing at the reader
(`illiquid: Rs* lakh median daily turnover (floor Rs* lakh)`, `ASM LT Stage I —
surveillance: N% margin`) because reasons carry per-name numbers and were
grouped by regex-blanking the digits. Now classified to a stable GATE
(`_PENNY_GATES`) and drawn as ranked bars. The `Cov` column was folded into the
score cell as its existing `°` marker, and the freed column became **Max size**
= 10% of median daily turnover — the number that should decide whether a penny
name is worth reading at all (a 90-scoring stock you can only put ₹40,000 into
is not an opportunity). Three tier populations (clean / unchecked / vetoed)
were separated only by 55% opacity; they now get a named divider row.

### Sectors, and the rest of the tabs

- Theme rows were 18 boxed numbers, which can only be compared a pair at a
  time. The closed row is now the chart: rank, name, **a bar that tracks
  whichever column is sorted** (normalised against the largest value present),
  then stats. The duplicated stat is dropped when it is the sort key.
- Positions tab opened on the notional paper book with the user's own two
  holdings 700px below it. Real money first.
- Journal `Stage changes` (50 raw rows, 1,571px — the largest panel in the app,
  under the two that actually answer something) and Screener `Watching — not
  qualified` (1,026px, taller than the 611-name qualified table it sits under)
  both scroll in their own box now, with their size stated in the header.
  Journal 2,917 → 1,738px; Screener 1,679 → 1,093px.
- AI Picks could not answer the first question anyone asks of a week-old pick
  list. Each pick now carries `+x.x% since pick`, measured from the last close
  the committee could have seen (last bar ON OR BEFORE the run date — the
  committee runs Sunday, when the newest bar is Friday's; taking the first bar
  at-or-after would measure from the wrong day).

### Notes for the next editor

- `tests/test_capital_gate.py::test_cohort_split` errors under pytest
  (`fixture 'monkey_status' not found`) and passes when run directly. Pre-
  existing, unrelated to UI work. 30 pytest + all 9 script-style files pass.
- The screenshot tool still times out on `dashboard.html` at every viewport.
  Verify via `read_page` / JS DOM measurement — measuring bounding boxes for
  every child of a tab is what found all three alignment defects above.

---

## 3R. The penny universe now settles its own arms (2026-07-26 evening)

The durable fix for §3Q's ceiling defect, and the measurement that showed the
defect was **twice as large as reported and ran in both directions**.

**What was actually wrong.** The arm assignment ran once, at build time,
against whatever market caps happened to be in the fundamentals cache at that
instant — and the caps arrive from a LATER step. The weekly chain is
`build_penny_universe -> penny_fundamentals -> penny_scan`, so the builder is
structurally one step behind its own input, and nothing ever revisited the
decision. The universe shipped on 2026-07-26 was built by the cloud (commit
`e43477d`) against a cold cache and resolved **zero** caps:

| | 2026-07-25 (warm, local) | 2026-07-26 (cold, cloud) |
|---|---|---|
| qualified | 178 | 153 |
| price arm | 113 | **153** |
| mcap arm | 106 | **0** |
| held "pending a cap read" | 15 | 984 |

- **40 of 153** names (not 34) were above the ₹5,000 Cr ceiling: IDEA ₹1.42
  lakh Cr, IRFC ₹1.15 lakh Cr, IDBI ₹91k Cr, NTPCGREEN, NHPC, NMDC, YESBANK,
  SUZLON, with UJJIVANSFB ₹13.8k Cr ranked #1.
- **65 genuine nano-caps were missing entirely** — the mcap arm, the one the
  report calls "the one that means genuinely small", did not exist that night.
  DJML (₹411 Cr), ATALREAL (₹382 Cr) and PREMIERPOL (₹831 Cr) — the names the
  07-25 session had just promoted to the top of the table — were sitting in
  `penny_excluded.csv` marked "pending".

A read-time filter can only fix the first half. You cannot filter a name back
into a universe it was never in.

**The fix.** Arm assignment is now a pure function, `assign_arms(df)`, applied
by `_finalize()` — which both `build()` and the new `recheck_caps()` call, so a
build and a re-check cannot drift about what "penny" means. `build()` also
snapshots its gate verdict for every security to `state/penny_gates.csv` (the
gate depends on NSE data only — series, band, surveillance, liquidity, listing
age — never on market cap), which is what lets the arms be recomputed later
without going back to the exchange. `penny_scan.py` calls `recheck_caps()`
before it ranks anything: no network, it reads the cache the previous step just
filled, and it settles the universe **in the same run** instead of a week
later. It fired on its first live run and promoted 9 more names.
`--recheck-caps` on the builder and `--no-recheck` on the scan exist for
running either half alone.

Both directions are handled, and neither is silent: a name that outgrows the
ceiling is written to `penny_excluded.csv` with a per-name reason that states
both numbers the reader will argue with — *"not penny/nano — too big on both
arms: a ₹13 share of a ₹142,254 Cr company (the price arm's ceiling is ₹5,000
Cr — a cheap share is not a small company)"* — which classifies under the
funnel's existing `not penny/nano` gate, so the dashboard needed no new label.

**Two smaller things the same bug was hiding.** `mcap_pending` was computed as
`isna & ~price_arm`, which excluded exactly the cheap names whose cap decides
their arm — they entered on price and were never queued for a read, so the
ceiling could never bind. It is now `tradable & cap unknown`, and this costs no
extra scraping (`penny_fundamentals` already fetches every universe member).
And the meta file gained `arm_provisional`: how many admitted names are in on
an unread cap. On a cold build that number equals the whole universe, which is
the fact the 07-26 run had no way to state.

**The read-time filter stayed, as a tripwire.** It should never fire now. If it
does, the upstream re-check did not run and the build **prints a loud `!!` line
naming the offenders** before filtering them, rather than quietly publishing a
nano-cap screen led by a PSU bank.

**Journal.** All 20 rows of the 2026-07-26 penny run came off the wrong
universe — 7 names that never belonged and a `rank` column that was wrong for
every row — so the whole run moved to
`journal/quarantine_penny_universe_2026-07-26.csv` (append-only journals are
never edited silently; same handling as 2026-07-09 and 2026-07-25). The scan
re-journaled 07-26 correctly, and it now continues coherently from 07-25 (same
names, small score drifts), which is itself the confirmation that 07-25 was the
sound run and 07-26 the anomaly. The 07-25 rows were checked against today's
caps and are clean — nothing to quarantine there.

Current universe: **187 names**, price arm 113 / mcap arm 106 (41 on both),
largest cap ₹4,732 Cr, zero pending. Top of the table: DJML ₹411 Cr,
PREMIERPOL ₹831 Cr, ESAFSFB, ATALREAL ₹382 Cr, SCPL ₹599 Cr.

**Tests**: `tests/test_penny_screen.py` gained 18 assertions across
`test_arm_assignment` (each arm case, including the unread cap that must never
CREATE mcap-arm membership) and `test_cap_recheck_settles_both_directions`,
which replays the incident end to end on synthetic data — cold build admits the
huge cheap share, caps land, re-check demotes it and promotes the nano-cap, the
reason survives, and a second re-check is a no-op.

**Note for the cloud**: `state/penny_gates.csv` (~700 KB) is gitignored like
the rest of `state/`. It does not need committing — the build and the scan run
in the same job on the same workspace — and `recheck_caps()` returns `None`
and leaves the universe untouched when it is absent.

---

## 3S. Verification pass: the gate's bar was on the wrong scale, and the test suite could not fail (2026-07-27)

A full verify-every-flow pass on the morning the gate cohort was due to open.
Four defects, each found by testing something that had been assumed. Ordered by
how much they mattered.

### 1. The test suite could not fail

`test_capital_gate.py` and `test_penny_screen.py` define pytest-visible `test_`
functions, but their `check()` helper appended to a list and printed — it never
raised. **Under pytest all 16 of those tests passed unconditionally**: injecting
a deliberately false check still reported `7 passed`. The two files guarding the
capital decision and the penny universe were decorative. (`test_capital_gate`
additionally had a leftover `monkey_status` fixture arg erroring at collection —
that one at least was visible.)

The fix took two attempts, and the second only happened because CI caught the
first. `_UNDER_PYTEST = "PYTEST_CURRENT_TEST" in os.environ` evaluated at
**import** time is always False — pytest sets that variable while a test *runs*,
not while the module is imported. So the first fix changed nothing, and the
three failures observed right after it were genuine exceptions (bad signature,
missing key), not check failures. Detection is now a call-time function testing
the env var **or** `pytest in sys.modules`.

**`.github/workflows/tests.yml` now runs on every push, with a CANARY step that
injects a false check and requires the suite to fail.** Nothing ran the tests
anywhere before this — a broken commit went straight to the nightly runner.
Keep the canary. It has already paid for itself once.

### 2. The gate's bar was on the wrong scale — RE-REGISTERED at n=0

The gate is the number this project exists to produce, so this is the important
one. `CAPITAL_GATE.md` §9 carries the dated amendment; the short version:

The flat **+0.50R** came from halving the *full-hold* stressed backtest read.
But the ruler marks **open** positions to market at whatever age they have
reached, and this strategy earns its expectancy in the right tail. Measured on
the validated baseline's own trades:

| trades held | n | mean R | sum R |
|---|---|---|---|
| 0–90 days | 64 | negative throughout | **−45R** |
| 90+ days | 32 | +0.57 → +25.7 | **+200R** |

Five entries held over a year produced 83% of all gross positive R. So at day 30
only ~29% of full-hold R has developed; at day 90, ~40%. Judging a 30-to-150-day
live read against half of a full-hold number asks the live system to do in a
month what the backtest needed a year for.

Bootstrapping 20,000 cohorts of n=40 from the strategy's own entries: **a live
system reproducing the validated strategy EXACTLY passed the flat bar 67% of the
time, and 21–44% at the stressed level.** A gate that rejects a working system a
third to four-fifths of the time is a broken instrument, not a conservative one.

Condition 1 is now like-for-like: each signal is measured against what the
backtest read **at that signal's own age**, and the cohort must reach 50% of it.
Same fraction, correct scale; power rises to 77–83%. At a realistic 90-day age
mix the bar is **+0.36R**.

The curve is **FROZEN** in `config.GATE.expectancy_curve` — a bar that drifts
with a re-run is not pre-registered. `scripts/gate_reference_curve.py`
regenerates it and reports drift; **drift is a §8 re-registration trigger, never
a licence to edit the constant.** It reproduces exactly today.

Amended at cohort **n=0**, hours before the first scan that could produce a
qualifying signal, so no collected data informed the change and the sample does
not restart. That timing was luck. It would not have been available a week later.

**Also disclosed, NOT fixed:** condition 2 (`sum(R) × risk_per_trade_pct`) is a
*signal-basis* number — it scales with the COUNT of signals rather than with
capital, so it crosses the benchmark at about +0.15R and **cannot bind once
condition 1 passes**. It is a visible sanity read, not a fourth independent
test. Making it a real portfolio comparison means running the cohort through the
engine as a portfolio, which is a ruler change and needs its own registration.

### 3. Silent price-staleness

`update_symbols` returns `(ok, failures)`; `daily_scan` called it for the side
effect and **dropped the list**. Prices are the one input every tag, score and
trigger depends on, and a failed refresh was invisible: the benchmark is among
the first symbols fetched so it refreshes, every name still tags, no single
holding looks odd, and the report reads like a normal night.

Three links fixed: `fetch_yahoo_daily` retries with backoff on 429/5xx (one
rate-limit reply used to turn into hundreds of consecutive failures);
`daily_scan` raises a health problem carrying the failed count; and a new
**universe-wide staleness check** compares every name to the newest bar anywhere
in the cache. A market holiday moves every symbol together, so it cannot
false-positive. `update_prices` also now exits non-zero above 20% failures —
`weekly_refresh` runs that step with `fatal=True`, which meant nothing while a
run failing most of the universe still exited 0.

**Note on the local cache**: the local copy IS badly stale (643 of 652 names
behind, MOSCHIP 11 days) — but that is expected and NOT a production defect. The
laptop scan jobs have been disabled since 2026-07-18 and the cloud keeps its own
cache in `actions/cache`. Production was verified healthy the hard way: eight
closes journaled by the 07-24 cloud run match the real 07-24 bars to the paisa.
**Do not diagnose production from the local cache.** Run
`python scripts/update_prices.py --all` if you want the local dashboard current.

### 4. There was no way to test the nightly path

Every prior test run wrote to an append-only journal — the 2026-07-09 intraday
rows and the 2026-07-07 synthetic row both entered that way and could only be
quarantined afterwards. **`daily_scan.py --dry-run`** computes everything and
writes nothing (implies `--no-update`).

Building it immediately found a live side effect: `news_radar.scan_radar`
windows from its own last-run stamp, so a test run **silently shortened the real
run's window and dropped a night of filings**. `scan_radar` and
`news_pressure.scan` now take `persist=`. `tests/test_scan_integrity.py` locks
all of it.

### Verified working (no defect found)

- `BUY TRIGGER` wiring is sound. A dry run over the real universe produced 0
  triggers, and a direct count confirmed that is correct, not broken: 0 names
  had `validated_entry` tonight, 49 have a VCP base awaiting a trigger, 565 have
  no base. At ~1.7/week across 611 names a zero night is the *most likely*
  single outcome (~71% under Poisson). A transition-night validated entry is
  also correctly picked up by the gate via `status_ok`, not just `kind_ok`.
- 42 pytest + 10 script-style test files green; all 28 modules import clean;
  `compileall` clean.

### Pre-registered experiment queue (NOT implemented — register before running)

Both come out of this session's measurements and both fit the evidence lock.
Neither may be wired live before passing out of sample against the baseline.

**RUN AND CLOSED, same day.** Pre-registered in `PREREG_2026-07-27.md` (committed
before the run, commit `36745eb`), verdicts in `VALIDATION_REPORT.md` §6F.

**P5 — queue ranking: NOT RUN, killed by measurement.** Ranking decides an entry
only when `1 ≤ free slots < same-day candidates`. Measured: 358 breakouts over
243 days, 68% alone on their day, largest same-day cluster 6 against a 12-slot
cap — an expected **8.2 decisions in three years**. Against a heavy right tail
that is indistinguishable from noise. This also corrected a conflation: "the cap
binds 39% of days" is the portfolio being FULL (30% of days, breakout rejected
outright), not same-day ordering. Different lever.

**P6 — trailing speed: REJECTED.** Every faster trail is worse (−0.05R at 30,
−0.34R at 20, −0.32R at 10, against a required +0.10R); the trading lot itself
degrades 0.538R → 0.309R. Qullamaggie's 10/20-DMA trail does not transfer to this
position horizon. MAR rose monotonically with trail speed (2.56 → 2.78) — noted,
NOT adopted, because it was not the registered metric.

**P5b — slot count on equity sizing: REJECTED, 12 confirmed as a real optimum**
(MAR falls on both sides: 2.51 @8 / **2.56 @12** / 2.50 @16 / 2.48 @20). Worth
having run: the 2026-07-11 rejection's stated mechanism — a monotonic expectancy
collapse — was a **cash-sizing artifact and does not reproduce** on equity basis
(1.681 → 1.564 → 1.661). The conclusion survives on cleaner grounds.

**The single most reusable finding of the day is in §6F's drawdown column:**
maxDD is constant at −18.44% to −18.47% across 74, 96, 116 and 127 positions.
**Position count buys no drawdown protection here** — these names sell off
together. Do not reach for "hold more names" as a risk lever in future work;
drawdown control comes from exposure (the breadth-regime halving), not breadth of
holdings.

**Measured and NOT worth pursuing — a day-30 "dead wood" cut.** All 7 eventual
monsters were already positive at day 30 (p≈0.015 against a 55% base rate),
which looked like a slot-freeing opportunity. It is not: of the 61 entries still
open at day 30, only 11 are non-positive, they average −0.38R, and cutting them
frees ~12% of slots, not the ~48% a first pass suggested (that number wrongly
counted already-closed trades, which occupy no slot). Recorded here so it is not
rediscovered and overrated a third time.

---

## 3T. Six user-reported defects, and what each one turned out to be (2026-08-02)

The user reported six things. Every one had a real mechanism behind it, and two
of them were bugs of the same family this project keeps rediscovering: a fix
that never reached the stored record, and a filter that discarded data before
anything judged it.

**(1) "the news and filings are showing same news multiple times."** Two
separate causes. NSE publishes most filings TWICE — once under the company's
free-text description and once under its own XBRL category, with different links
— and one earnings call arrives under five labels across four days ("Schedule of
meet", "Audio Recording/Video Recording", "Link of Recording", "Transcript",
"Transcripts - earnings or quarterly calls"). `phase_c` deduped on
`subject[:80]`, which only ever caught byte-identical repeats. Now deduped by
EVENT: a normalized gist with the preamble and XBRL tail stripped, token overlap
≥0.7, same event class on the same day, or a shared filing TOPIC inside 6 days
(`_FILING_TOPICS`: concall, results, board notice, credit rating, management
change). A declared topic beats a token-overlap guess, so "Board Meeting to be
held on the 5th to consider results" no longer merges with "Outcome of Board
Meeting - results". Live: WELCORP 7 filings → 3 events, SHILPAMED 5 → 2.
**On the headline side the user found the sharper case** (HONASA, four outlets
on one CEO appointment): the story clustering was ALREADY correct — all four in
one story with novelty decayed 1.00/0.45/0.20/0.09, which is why the score never
double-counted them — and only the DISPLAY ignored it. No ML layer was needed or
added; the panel now shows one line per story with "— 6 outlets: ET BrandEquity,
ET Retail, …", because corroboration is evidence rather than noise. Two
clustering fixes fell out of it: Google News appends " - Publisher" to every
title and those tokens were diluting the overlap between retellings, and one
appointment gets a dozen barely-overlapping write-ups so "management change"
joined results and broker-call as a repeatable topic (requiring a ROLE, not just
the verb — "exit" is what a fund does to a position, and on the verb alone a
Helios Flexicap reshuffle merged into the CEO story).

**(2) "it is missing important news, so the fetch has to be improved."**
Correct, and the mechanism was precise: `google_news` truncated to the 20 most
recent articles **by recency, before anything judged importance**, while the
feed was returning up to 72. Measured across five live names, **42 whole stories
were being discarded past the cut** — including "HFCL to Invest Rs 950 Crore in
Optical Fibre Cable Production", "Welspun Corp Bags Pipeline Orders" and
"Granules secures sole First-to-File status". The cap is now
`NEWSQ.fetch_articles_per_company = 60` and it is a safety ceiling, not an
editorial decision. This was affordable because `count_other_companies` was
prefiltered (a candidate whose first token is nowhere in the headline cannot
match, so 652 regex searches became a handful): **read_article went 66 ms →
1.2 ms**, verified identical on 1,200 real headlines. Reading 60 articles now
costs a third of what reading 20 used to. The card also ranks what it shows by
weight instead of fetch order — the Rs 960 Cr Welspun order used to sit fourth
behind two auto-generated metric pages and a multibagger listicle.

**(3) "HFCL showed scores until yesterday and today some are empty."** The
weekly `shortlist_details.json` was built ONLY for names tagged CONFIRMED or
ANTICIPATION. HFCL was CONFIRMED last week and is not this week, so it left the
file — **27 names did** — and the dashboard, finding no weekly read, fell back
to its alert blob of 2026-07-17 whose five fundamental dimensions are null.
HFCL's complete fundamentals were in `fundamentals_flat.csv` the whole time. A
tag is a statement about the CHART; it was never a reason to stop knowing what a
company earns. Two fixes: `run_shortlist` now scores every focus name that has a
fundamentals row (news enrichment stays on the ranked shortlist — that is the
network cost), and `fetch_fundamentals` **flattens wider than it fetches** —
all 280 focus names had real cached screener data and only 152 were reaching the
CSV, so 128 names were being scored as if nothing were known about them, for
zero network. Scored names went 99 → 280, median coverage 75%, six names below
60%. HFCL now reads 84.9 at 75% coverage.

**(4) "!! [NSE FILING] 'sebi': Pursuant to Regulation 32(6)…"** The 2026-07-28
fix was real and the code was correct — but `state/alert_details.json` is a
RECORD, frozen the night each name alerted and kept 30 days, and it still held
34 of those false positives. **A fix that does not reach the stored record is
not visible to the person reading the record.** `scripts/heal_alert_details.py`
re-judges stored blobs with today's classifier using the text they already carry
(no network): 49 red flags → 7, all genuine, survivors relabelled under current
event names, filings re-deduped and re-ordered, every blob stamped
`news.v = phase_c.NEWS_SCHEMA`. Two false positives that SURVIVED re-judging
were then fixed properly in the engine: "Federal Bank of India Combats Card and
Merchant Fraud" (the company is fighting the harm, not causing it) and "Penalty
over minimum bank balance not consideration: Karnataka high court" (a state
institution absorbing a company's name token — Karnataka Bank, Gujarat Gas,
Punjab & Sind Bank all collide this way).

**(5) "the positive negative sentiment parameter also has to be improved."**
Four measured defects. **A decimal point inside a rupee figure ended the metric
window**: `[^.;|]{0,28}` between the financial noun and its direction word was
terminated by the "." in "Rs 1,476.77 crore", so *every* Moneycontrol quarterly
print read as neutral in BOTH directions — 11 of the 2,669 headlines on disk,
all tier-1, all in the most decision-relevant class. Three event classes were
missing entirely and are now in the shared taxonomy: **capex/investment**
(Paras Defence's Rs 6,200 crore semiconductor plan carried the largest figure on
its card and classified as nothing), **deleveraging** ("Granules India turns
debt-free"), and **partnership** (deliberately the lowest-materiality positive
class — an MoU is intent, not revenue; the pattern demands an action verb so the
exchange's bare "Agreements,Contracts,Arrangements,MOU-XBRL" category label, 44
of them in the archive, stays unclassified). Also: **"Bagging/Receiving of
orders/contracts" is NSE's own label for an order win** and neither `\bbags?\b`
nor `\breceives?\b` reaches the gerund, so every first-party order filing
classified as nothing; and pharma First-to-File / exclusivity now classifies as
an approval. The frozen 216-headline corpus stayed at 96.8% exact with zero sign
flips throughout — it contains none of these classes, which is why they were
missed. 12 new trap tests plus `tests/test_filings_card.py` (18 checks).

**(6) "the episodic buy trigger fired for a stock which rose more than 10% —
does it still have momentum?"** Answered from this project's own evidence rather
than changed. The live case is SMLMAH on 2026-07-30: gap **+10.0%** on **19.5x**
average volume, closing above its open. `ep_matrix_report.md` tested exactly
this: EP_A (gap≥8%, vol≥3x) 83 positions +1.377R, and the STRICTER **EP_C
(gap≥10%, vol≥4x) scored HIGHER per trade at +1.868R with P2 +1.033R** — the
dose-response runs opposite to the intuition, bigger gaps did better. Combined
with the VCP class, MAR went 2.70 → 3.58 with LOWER drawdown. The risk is
bounded structurally, not by a percentage: the stop is the gap-day LOW (SMLMAH
8.4%, inside the 12% Design Law #7 cap, which skips the ones that are too far
gone). This is also the third time extension has been tested here —
`PREREG_2026-07-29.md` X1 found distance above the 30-week MA, prior 6-month
return and 52-week position all correlate **positively** with forward R
(+0.214/+0.158/+0.223), and the mildest usable filter destroyed 56–66% of all
profit. Honest caveat: exactly ONE EP has fired live so far, so the claim rests
on the 83-position backtest, not the forward record.

**(7) The scoring audit** (`SCORING_AUDIT_2026-08-02.md`) covers all 8
dimensions against O'Neil/Minervini/Qullamaggie/QGLP. Two corrections shipped —
earnings_inflection gained a persistence term and the Design Law #5 "2+
consecutive improving quarters" guard it had only half-implemented (the screener
page carries 13 quarters; the score read one, so a name improving every quarter
for two years and a name with a single bounce answered the heaviest question
identically), and valuation_sanity's turnaround exemption now guards the PEG
branch too (HFCL: P/E 52.6 against 1% three-year growth scored "full price, PEG
52.60" while its TTM growth was 1591%). Combined effect on the live shortlist:
mean **0.86 points**, 8 of 99 names moving >2, one top-10 change. **No weight
was changed** — the audit's loudest finding is that theme_tailwind carries
weight 15 while its nearest tested analogue (matrix v2 config E, sector gating)
was REJECTED at +0.22R against +1.27R, and moving a weight on an argument rather
than a pre-registered test is the failure the evidence lock exists to prevent.
Ranked queue for next pass is in the report's last section.

**Also found and fixed while checking filings:** one archive row whose RSS
`<title>` was empty gave `announcements_for`/`archived_for` a blank
`company_norm`, and every string starts with `""` — so that single filing
("Ekalavya Foundation … Resignation of Chief Compliance Officer") attached
itself to **all 651 companies** and took a slot on every card in the system.
Prefix matching now needs 6 characters on both sides.

---

## 3U. The four deferred scoring items, built — and the ticker the reader could not see (2026-08-03)

Designs are in `SCORING_PROPOSALS_2026-08-03.md`, written after checking what
the data actually contains. **That check overturned two of the five
recommendations `SCORING_AUDIT_2026-08-02.md` had made the day before**, which
is the entry worth remembering: an audit that recommends without measuring is
a hypothesis, not a finding.

**THE USER-REPORTED MISS, and the largest single fix here.** "SCI has an
important news yesterday, that it floated a global tender for 8000 ships — why
did we miss it?" It was **fetched** and then thrown away by the READER:
`relevance` scored it 0, "company not named in the headline". Shipping
Corporation of India reduces to the single token `["shipping"]` once
Corporation/India/Ltd are stripped, `shipping` is a weak-solo token, and
"ships" is not a prefix of it — so a headline that says **SCI** matched
nothing. **91 of the 651 universe names reduce to one short or generic token
like this** (BEML, CESC, EIH, CCL, BLS, DOMS, HFCL…), and the Indian press
refers to exactly those by ticker. `_symbol_match` now matches the exchange
ticker, CASE-SENSITIVE against the original text — capitalisation is the
cheapest available disambiguator between SAIL the steel company and the verb —
with a blocklist for tickers that are ordinary capitalised words (MAX, ONE,
IDEA, GST, RBI…), a 3-character floor, and a rule that a bare ticker hit never
overrides an explicit "this headline is tagged NSE:UMESLTD" finding. Also added
`capex/investment` patterns for a tender the company FLOATS (procurement, i.e.
spending — a tender it WINS is still an order win, checked first). Live result:
the SCI story is now the card's LEAD STORY at catalyst 0.742.

**(1) FII and DII no longer cancel each other.** `score_smart_money` summed the
two changes into one number. Measured across the 290 names with all four
values: 59 have both legs buying, 20 both selling, and **152 have them moving
in opposite directions** — so on 52% of the universe the sum reported the
residue of a disagreement as a consensus. AAVAS (FII 13.0pp out, DII 10.6pp in)
netted to −2.4 and read as mild distribution. Now scored as two legs: agreement
is pushed away from the middle (the closest this data gets to O'Neil's
"increasing number of sponsors"), divergence weights the DOMESTIC leg higher
because FII flows track global risk conditions rather than company
fundamentals, and the note names both legs and the verdict. Promoter BUYING
moved here from governance — it is an insider signal, not a hygiene check, and
splitting one fact across two dimensions meant neither told the story.
Effect: 108 of 290 names move >0.15 on the dimension. HFCL 1.00 → 0.47,
ENTERO 0.00 → 0.55.

**(2) Sales confirms earnings.** O'Neil's C wants same-quarter sales >25% OR
acceleration over three quarters, and says why: earnings can be lifted by cost
cuts, one-offs or accounting. Minervini wants sales, margins and earnings
moving together. The dimension had no sales term at all. Added as a
MULTIPLIER, never a component — both systems treat sales as confirmation of an
earnings signal, not as something that can rescue a weak one, so it can only
discount (×1.0 / 0.92 / 0.80 / 0.65). Distribution across 291 names: 250
unaffected, 12 at ×0.65. NAZARA is the showcase — **sales −23.5% YoY against
TTM profit growth +1271%** — and the card now says "MARGIN-LED, check whether
this is cost cutting rather than growth", which is the most useful sentence
this dimension could carry and previously could not.

**(3) Governance flags from the filings archive — CORRECTED to a flag, not a
score.** The audit called this "a real measurement". Measured across 27,115
filings: auditor resignation hits **1** universe name, modified opinion 2,
pledge events 1, rating downgrades 0, and 33 of the 42 negative-classified
filings are routine director changes. About 8–11 governance-relevant events
across 651 names per three weeks. A scoring component on that leaves 640+
names unmoved and measures nothing; sparse-but-real is a ruin-avoidance
profile. `phase_c.governance_flags()` reads 180 days of first-party filings for
auditor exit / modified opinion / pledge CREATED-or-INVOKED / regulatory action
(hard) and KMP exit (soft). **10 of 652 names flagged**, incl. GALLANTT's
genuine auditor resignation. A pledge RELEASE was caught red on the first run
and excluded — it is promoters de-risking, and direction is the whole point for
a flag even though news_radar's own pledge class lumps all three together.
I wrote it as a ninth Dimension first; that was wrong twice — `CONVICTION.weights`
must sum to 100 so a new key has no defined weight, and the density does not
support one. It is display-only, and its firing rate gets counted before
anyone argues for a veto.

**(4) Banks get a real read — but NOT the one the audit recommended.** The
audit said "NIM trend, GNPA trend, CASA". **None of those exist on the free
screener.in page.** A bank page carries Revenue, Financing Profit, Financing
Margin %, Net Profit, EPS, Equity Capital and Reserves — no NPAs, no CASA, no
capital adequacy, no cost-to-income, not even Borrowings. `flatten` already
maps "Financing Margin %" onto the `opm_*` columns, so the margin trend and its
streak arrive free. `score_financial_strength_bank` = margin trend 0.35 + ROE
0.25 + book-value compounding 0.25 + dilution 0.15, replacing a flat 0.5 that
had sat on **48 financial-sector names** for a month. The note states the
limitation on every card, because a bank score that silently omits asset
quality is more dangerous than a flat 0.5 — 0.5 at least looks like an
abstention. Range: MCX 1.00 (margin 55→75%, ROE 56%) to SAMMAANCAP 0.04
(margin →−263%, ROE −3.18%, share capital +154%).

**(5) NOT built, by design.** The theme_tailwind weight test is specified in
the proposals doc and deliberately not run: 157 outcome rows exist but only 33
carry a frozen `news_catalyst`, and 0 of 199 have hit a stop. Also corrected my
own framing — matrix v2 config E tested sector heat as an entry GATE, and this
dimension gates nothing, so it never actually answered the question. The
answerable version is a leave-one-out rank correlation over ALL EIGHT
dimensions at once. Build the harness so the decision rule is fixed before any
number is visible; run it when the frozen-news cohort reaches ~100.

COMBINED effect of 1–4 on the live shortlist: mean **2.19 points**, 24 of 99
names moving >3, and a genuine top-10 reshuffle (JAMNAAUTO and CHENNPETRO out —
both had been scoring 1.00 on the cancelled FII/DII sum; DCBBANK and SANSERA
in). 194 pytest green, canaried.

**Also fixed:** the dashboard's coverage-aware merge used `>=`, so on equal
coverage the OLDER read won the drawer — meaning every scoring improvement
stayed invisible on any name carrying an equal-coverage alert until it aged
out. Now strictly-better coverage, or equal coverage and fresher. Same
frozen-record family as §3T(4), this time in the merge rather than the store.

---

## 3V. The policy radar — reading the 86% of the news that names no company (2026-08-28)

User request: "we are identifying stock based news... I want to check the top
news and global or Indian trends based on government or trends in general and
identify the stocks which will have an impact and impart that in the news
catalyst score."

**The gap was real and bigger than expected.** Every news path in this system
required a headline to NAME a company: Google News is queried per company,
`news_sources.archived_for` matches the market archive by a company's
distinctive name tokens, and `news_radar` reads NSE filings, which are
first-party by construction. So the system read what was said ABOUT a company
and never what was decided about the WORLD it sells into. Measured on the
archive already on disk (7,937 headlines / 44 days):

```
headlines naming >=1 universe company :  1,107  (13.9%)
headlines naming NO universe company  :  6,830  (86.1%)   <- read by nothing
```

Sitting unread in that 86%: "Cabinet approves Rs 1.27 trillion for
Semiconductor Mission 2.0", "Gujarat unveils shipbuilding policy... targets
Rs 27,000-crore investments", "NTPC-NPCIL JV floats Rs 28,000 crore tender for
nuclear power plant", "Govt approves 31 proposals worth Rs 7,877 crore under
electronics component scheme". Three of the ten swept feeds are ECONOMY
sections — the data was already being fetched, archived and committed. It was
being thrown away at the symbol-matching join.

**The measurement inverted the obvious design.** Counting macro headlines per
theme over the same 44 days gave finfra 172 hits (SEBI/IPO/mutual-fund
boilerplate) and shipbuilding 139 ("port", "supply chain" in generic trade
news), against semis 5, nuclear 2, ems 1 — where the real policy events live.
Volume-weighting would have handed the biggest uplift to the noisiest themes
and the smallest to the ones that mattered: the same error §3K's phase_c
rewrite removed from company news. So `data/macro_radar.py` scores
**materiality, never volume**, and is built to be rare: an ACTOR (a body that
can decide something, incl. public-capital deployers like NTPC/NPCIL/DRDO)
must take an ACTION (decide it) on one of the 17 mapped themes. On the live
archive that is **18 policy events out of 7,935 headlines**.

- **Intent is not action.** "Govt weighs / plans / mulls / may" is demoted to
  attention and contributes ZERO — same reasoning that puts "partnership" at
  0.2 in `NEWSQ.event_materiality`. A headline pulling both ways ("Govt eases
  battery PLI norms... subsidies lowered") resolves to `attn`, not to a
  guessed direction.
- **One decision, one story.** Retellings collapse; syndication breadth is
  displayed and never summed.
- **Absent data grants nothing.** No radar / no theme membership / no policy
  news on a name's themes -> delta exactly 0.0 with a note saying WHICH, never
  a middle value. A radar older than `MAX_AGE_DAYS` (4) is treated as absent,
  because the decay was applied at BUILD time and a frozen store would keep
  asserting a tailwind that has since faded (the §3T(4) family).
- **Bounded and reporting-only.** The overlay moves the CATALYST dimension by
  at most `MACRO_CAP` = 0.12, and moves nothing else. It is deliberately NOT
  also fed into `theme_tailwind`: one event moving two of the eight dimensions
  would be double-counting dressed up as corroboration. **It gates, ranks and
  sizes nothing — entries stay 100% technical.** `scoring/themes.py` records
  that sector heat was tested as an entry filter and REJECTED (+0.22R at a 40%
  gate vs +1.27R ungated); this must never become that filter by the back door.
- Every moved number carries its headline: the dimension note gains
  "+0.042 from policy tailwind on railways (pressure +0.35 from 3 events):
  Railway Ministry approves...", and the card blob carries `macro_evidence`.

**Two bugs found in the SHARED amount parser** (`news_nlp.extract_amount_cr`),
which affect company news too, not just this module: "Rs 1.14 lakh crore" read
as "1.14 lakh" returned **0.0114 crore for 1,14,000 crore** — a ten-million-fold
understatement in the unit Indian policy and large-order headlines are most
often written in — and "trillion" was not a unit at all, so the Rs 1.27
trillion Semicon Mission parsed as no figure. Both fixed, with the pre-existing
cases held.

**Live tonight:** 93 of 650 universe names receive a non-zero policy delta
(+0.014 to +0.042 catalyst units), across railways, ev, ems, semis, capex,
shipbuilding, defence, renewables and hospital. Note the divergence this
surfaces: Jupiter Wagons' theme_tailwind reads 15/100 (price-derived heat is
cold) while the policy layer reads +0.35 — information the system did not
previously have anywhere.

**Wiring:** `daily_scan` builds it after the feed sweep and before any
enrichment (ordering matters both ways); `run_shortlist` rebuilds it for the
weekly, since the staleness guard would otherwise blank every weekly card;
`state/macro_radar.json` is in daily.yml's commit list (a file that is not
would silently not exist in production); a "## Policy radar" block goes to
daily_alerts.md -> Telegram, naming the affected symbols. Guards in
`tests/test_macro_radar.py` (13), built from the real archive including every
false positive the first two runs produced — cyber-defence read as the defence
sector, a "Defence stocks fire up!" price roundup, a statistic quoted to a
ministry — and verified able to go red by zeroing MACRO_CAP.

**Not built, deliberately:** the AI analyst and weekly committee briefings do
not yet receive the policy radar. That is a genuine cross-feed (§3K's "layers
collaborate" directive) and the obvious next step, but it is a separate change
to what those layers are told, not part of the catalyst score.

---

## 3W. Nothing was checking that the scans had run (2026-08-31, user-reported)

The user opened the dashboard and found every panel stale. Four independent
faults, none of which had ever raised a signal, and the reason they could not
is structural: **the page, the Telegram digest and the health strip are all
produced BY the nightly job.** When it does not run there is nothing to build
them and nothing to complain. Silence is indistinguishable from a quiet day.

**1. One best-effort cron is a single point of failure.** GitHub's scheduler
delays and drops schedules. The repo's own run history: ~45 min late through
mid-August, ~10 h late on 08-27 and 08-28 (created 22:5x UTC for a 13:05 cron),
and on Mon 08-31 it never fired at all. `daily.yml` now has FOUR slots — 13:05,
16:05, 19:05, 22:05 UTC — all inside the same UTC day, plus a `guard` job that
skips when `state/tags_state.json` already carries today's date.

The guard is not optional politeness. `daily_scan.py` is idempotent within a
session (transitions diff against the SAVED tag state; BUY TRIGGER/EP events
are keyed on the bar), so a second pass finds nothing new — and would then
rewrite `daily_alerts.md` with an empty list and blank the day's alerts. All
four slots must stay inside one UTC day because the guard compares a plain UTC
date; a slot past midnight UTC would re-run and do exactly that damage.

**The guard's first version was decorative and shipped that way for an hour.**
It read the stamp with `python -c`. The guard job has no `setup-python` step,
and bare `python` is not on PATH on GitHub's ubuntu runners — only `python3`.
The read fails, the `|| echo ""` fallback swallows it, the stamp comes back
empty, and an empty stamp can never equal today's date: **it answers "run" on
every firing**, which is worse than no guard at all. It reads with `grep` now
and depends on nothing the runner might not have.

**2. A failed pull bought the committee a no-op — for thirteen days.**
`weekly_committee_local.py` discarded `git_pull_retry`'s return value. On 08-23
the tree had unmerged files, all four pull attempts failed, and the wrapper
logged *"the freshness guard below is judging against a STALE shortlist"* — then
judged anyway, compared 18-Aug picks against a 16-Aug local stamp the cloud had
already moved past, declared itself current and exited 0. Task Scheduler
recorded success every time. On an unsynced tree the local stamp is only a
LOWER BOUND, so "mine is newer" is not a verdict the wrapper is entitled to
reach; past `PICKS_MAX_AGE_DAYS` (8, the same number the health strip paints
amber at) it now runs anyway, and an unsynced no-op exits 1 rather than 0.
`nightly_analyst_local.py` had had this exact rule since 08-18 — **the fix
reached one wrapper and never its twin.**

**3. The penny screen published nowhere.** It ran on its own 3-day cadence and
committed correctly, but `pages.yml` listed only Daily and Weekly under
`workflow_run`, and none of penny's paths under `push`. It ran at 11:32 UTC on
08-31 and the live site still served the 08-28 screen. It had been that way
since the workflow was split out on 08-17. A job whose output never reaches the
page has not run, as far as the user is concerned.

**4. The laptop slept for 61 hours** (08-29 10:01 -> 08-31 23:00 IST, from
`Microsoft-Windows-Power-Troubleshooter` — the TaskScheduler *Operational*
channel is disabled here and has nothing). Three Task Scheduler behaviours
compound and none of them log:

- a missed WEEKLY trigger advances a FULL WEEK — the slept-through Sunday
  committee trigger jumped straight to 09-06, a 14-day gap from one bad night;
- a logon trigger does NOT fire on resume from sleep, only on a real logon;
- `StartWhenAvailable` did not catch up — both tasks still showed the pre-sleep
  `LastRunTime` 17 minutes after wake.

Committee moved from weekly-Sunday to DAILY (its freshness guard makes idle
days a sub-second no-op — that is what the every-logon design was always for),
and the analyst gained the logon trigger this document already claimed it had.
`NumberOfMissedRuns` / `NextRunTime` from `Get-ScheduledTaskInfo` are the
fastest read on all three.

**What was actually added: something outside the pipeline.** All four faults
share one shape — the only thing that could have noticed was the thing that
failed. `scripts/scan_watchdog.py` + `.github/workflows/watchdog.yml` run at
01:30 UTC Tue-Sat with **no cache, no write permission, no shared concurrency
group and no pip install**, reading only the committed record. If the whole
pipeline is wedged, the watchdog still runs. It is allowed to stay silent; a
watchdog that chats every night gets muted. Its dependency chain is
stdlib-only on purpose — giving it the pipeline's dependencies would let a
broken dependency take out the alarm at the same moment it takes out the
pipeline.

`tests/test_scan_freshness_guards.py` covers all four, and **every guard in it
was checked by making it go red** — the two committee cases against the pre-fix
code, and the no-interpreter rule by putting a `python -c` back in the guard.

**Open:** `weekly.yml` and `penny.yml` still carry a single cron each and the
same drop risk. Both fired on time through this incident, so they were left
alone rather than rewritten speculatively; the guard shape in `daily.yml` is
the template if either starts slipping. The watchdog covers the detection gap
for both in the meantime.

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
  [redacted]) and DIACABS ([redacted] — a stock the system itself alerted
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
   **GATE PREREQUISITE (CAPITAL_GATE.md §6):** at the ₹10L placeholder every
   sized plan on screen is fiction. Must be real before any capital moves.

6. ~~DECIDE: implement Audit Finding 1?~~ **DONE 2026-07-25** — `BUY TRIGGER`
   fires as an event alert (commit `c4744a9`), F1b labels the EXTENDED
   divergence, and F2/F3's `plan_followed_R` landed the same day (§3O).
7. **MAKE THE REPO PRIVATE** — **also a GATE PREREQUISITE (CAPITAL_GATE.md
   §6).** User chose this 2026-07-25 for Finding 5
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

**Needs watching (added 2026-07-26):**
8b. **The 07-27 scan is the first that can produce a gate signal.** Confirm a
   `BUY TRIGGER` fires, lands in `journal/entry_signals.csv` with
   `entry_status=VALIDATED`, and appears in `state/gate.json` as cohort n=1.
   If the whole week passes at 0, that is a FREQUENCY finding to investigate
   (CAPITAL_GATE.md §5) — not a reason to loosen the cohort definition.
   The EP class has also still never fired since adoption on 2026-07-19; if it
   is still zero by mid-August that is a finding, not weather.

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

**Added 2026-07-26 (§3Q) — the standing instruction now:** the capital gate is
registered and OPEN at 0/40. Do not add features until it has a sample. The
first qualifying signal can arrive on the 07-27 scan; the honest next moves are
(a) watch that `BUY TRIGGER` actually fires and lands in `entry_signals.csv`,
(b) §5 #5 and #7 — `RISK.capital` and repo privacy — both of which must be
closed BEFORE any capital moves, and (c) the one cheap untested matrix cell,
P4. A trailing-speed test (20-DMA vs the 50-DMA trail on the trading lot,
Qullamaggie-style) is the other pre-registerable idea worth a run.

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
data/macro_radar.py           POLICY radar: the 86% of swept headlines that name no company —
                              government/regulatory decisions -> per-theme pressure -> a bounded
                              (MACRO_CAP 0.12) delta on the catalyst dimension. Whitelist, rare
                              (18 hits in 7,935), materiality-weighted not volume-weighted (3V)
state/macro_radar.json        policy radar output + the evidence headlines, committed nightly.
                              Treated as ABSENT past MAX_AGE_DAYS (4) — decay is applied at build
                              time, so a frozen file would keep asserting a faded tailwind
tests/test_macro_radar.py     13 guards built from the real archive: recall on 7 live policy
                              headlines, silence on 8 real false positives, intent-vs-action,
                              absent-data-grants-nothing (with a positive control), MACRO_CAP bound
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
scoring/news_nlp.py           THE reading layer (2026-07-28). Judges each article on four axes —
                              relevance 0-100 (co-mention aware, off universe.csv), kind
                              (corporate/procedural/price-move/listicle/datapage/fluff), direction
                              (event taxonomy first, lemma lexicon second, contrast+negation+
                              homographs handled), materiality (event class x rupee size / market
                              cap). Groups retellings into stories and decays repeats. Imports the
                              event vocabulary from data/news_radar — never restates it
data/news_sources.py          where headlines come from: nightly sweep of 10 tier-1 market-section
                              RSS feeds -> news_archive.csv (matched per company, same shape as the
                              filings archive) + per-company Google News. GDELT implemented but OFF
                              (429s every attempt); BSE API dropped (returns no records)
news_archive.csv              the tier-1 sweep archive, append-only, deduped by link
company_aliases.json          press names that differ from universe.csv's registered name
                              (SHRIPISTON trades as SPR Auto) — without these the name goes dark
news_engine_report.md         the measurements, the before/after table, and what was tested and
                              rejected. Read this before touching the news layer
tests/fixtures/news_corpus.json  216 hand-labelled headlines, 45 symbols, labelled BEFORE the new
                              engine existed. Carries a label revision log
tests/eval_news_nlp.py        the ruler: old vs new precision/recall/F1 (--errors lists misses)
tests/test_news_sources.py    16 robustness checks on the fetch layer: link dedup, archive
                              retention, sweep health, blind-outage detection. Network-free
tests/test_news_nlp.py        trap tests, every one a real headline this system got wrong
analyst/DEEP_DIVE_PROTOCOL.md analyst standing orders (incl. second-order ecosystem research task)
analyst/PICKS_PROTOCOL.md     committee standing orders (incl. second-order research + analyst-verdict cross-check)
scripts/build_dashboard.py    ALSO holds the whole UI (CSS + HTML + JS in TEMPLATE). The v6 "terminal"
                              rules sit LAST in the stylesheet and deliberately override the v4 card
                              styling; the universe map, dials and tape are rendered in the script block
CAPITAL_GATE.md               THE pre-registration: the threshold that decides real capital, fixed
                              2026-07-26 before the cohort existed. Amendment log in §9 — never edit silently
scripts/gate_status.py        computes the gate standing -> state/gate.json; keeps the validated cohort,
                              the pre-fix legacy cohort and the excluded classes strictly apart
scripts/surveillance_snapshot.py  ASM/GSM/circuit band/series for the MAIN universe -> state/surveillance.json
                              (display-only exit risk; a missing snapshot is UNKNOWN, never clean)
scripts/build_landing.py      generates landing.html from live state — the old hand-written page drifted
                              two adoptions behind the system it advertised
tests/test_capital_gate.py    19 checks: cohort isolation, the closed-or-aged rule, unsized exclusion,
                              concentration/stop guards, benchmark windowing
CLOUD.md                      GitHub Actions setup + operations (cache design, secrets, Pages, risks)
.github/workflows/daily.yml   cloud daily pipeline, FOUR crons (13:05/16:05/19:05/22:05 UTC
                              Mon-Fri) behind a guard job that skips once tags_state.json
                              carries today's date. GitHub drops schedules; one cron is a
                              single point of failure for the whole system's freshness (3W)
.github/workflows/weekly.yml  cloud weekly refresh (04:30 UTC Sun)
.github/workflows/watchdog.yml  the job that notices the other jobs did not run. 01:30 UTC
                              Tue-Sat, OUTSIDE the pipeline: no cache, no write permission,
                              no shared concurrency group, no pip install (3W)
scripts/scan_watchdog.py      reads only the committed record — scan/committee/penny/analyst
                              stamps vs their cadences — and stays silent unless something is
                              genuinely late. stdlib only, so a broken dependency cannot take
                              out the alarm and the pipeline together
tests/test_scan_freshness_guards.py  the guards that let a job SKIP. Every case verified able
                              to go red, incl. the no-interpreter rule for the daily guard
tests/                        two-lot + synthetic regression (both green)
```
