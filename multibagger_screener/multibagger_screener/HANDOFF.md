# HANDOFF — Golden-Stock Screener (read this first to continue)

**Last updated: 2026-07-09.** This is the single "where we are / what's next"
doc. For strategy read `PROJECT_BRIEF.md`; for the evidence read
`VALIDATION_REPORT.md`. This file is the operational status + next steps.

---

## 0. One-paragraph summary

A decision-support system that finds Indian small/mid-cap "golden stocks",
explains why, sizes the trade, and keeps a forward track record. It runs
itself: a nightly scan (18:35 IST) fires transition alerts, an AI analyst
deep-researches the top buy candidates, and a weekly job refreshes everything
+ an AI investment committee picks 3-5 researched names. Entries are 100%
technical (backtest-validated); fundamentals/news/AI are context + vetoes +
curation, never automated trade drivers. **The system is essentially complete
and live.** What remains is operational (Telegram, auth) and time (the
forward journal must accumulate before real capital).

---

## 1. Environment / how to run (IMPORTANT gotchas)

- **Python**: always use the full path — `C:/Users/karth/AppData/Local/Python/pythoncore-3.14-64/python.exe`.
  Bash `python` PATH is flaky; PowerShell tool also works.
- **Project root** (all commands run from here):
  `C:\Users\karth\OneDrive\Desktop\Karthikeya_claude\files\multibagger_screener\multibagger_screener`
- **Git repo** is at `files/` (parent). Commits through `2415232`. `.gitignore`
  excludes caches, secrets, logs, test artifacts.
- **AI scripts spawn `claude -p`**: they scrub `CLAUDE_CODE_*` + `ANTHROPIC_BASE_URL`
  from the env before spawning (else the host-injected auth poisons the child
  CLI -> "Invalid API key"). This is already coded; don't remove it.
- **Auth**: subscription `/login` works headless (with the scrub). The
  constraint is **subscription session limits** — they reset on a schedule.
  Permanent fix = API key (`setx ANTHROPIC_API_KEY ...`), recommended for the
  daily analyst. `python scripts/ai_analyst.py --selftest` verifies auth.

### Key commands
```
python scripts/daily_scan.py            # tag + diff + alerts + journal (usually scheduled)
python scripts/ai_analyst.py            # deep-dive top-3 buy alerts -> verdicts
python scripts/ai_picks.py              # weekly AI committee: 3-5 researched picks (Opus 4.7)
python scripts/weekly_refresh.py        # universe->prices->focus->fundamentals->shortlist->picks->dashboard
python scripts/build_dashboard.py       # regenerate dashboard.html
python scripts/enrich.py SYMBOL         # on-demand full card for any stock
python scripts/sync_positions.py        # holdings vs positions drift check
```
Open `dashboard.html` in a browser (needs internet for the chart CDN).

---

## 2. What's built and live (the whole system)

**Data spine** (all cached locally, engine reads cache only):
- Prices: Yahoo daily OHLCV 2019->now, 651 stocks, verified paisa-exact vs Zerodha/Kite MCP. `data_cache/`
- Fundamentals: screener.in public pages, all 651, ~12 quarters + 10y series. `fundamentals_cache/`
- Filings: NSE corporate-announcements RSS, archived daily. `announcements_archive.csv`

**Universe**: Nifty Smallcap 250 + Midcap 150 + Microcap 250 = 651 names. `universe.csv`.

**Pipeline** (nightly + weekly):
Universe -> liquidity filter -> RS-percentile focus list (~320) -> mechanical
stage tags (all 609 taggable) -> transition diff vs saved state -> alerts only
on state changes -> per-alert: 8-dim conviction score + vetoes + two-lot plan.

**8-dimension conviction score** (coverage-honest, 0-100):
rs_and_stage 20 (LIVE, validated) · earnings_inflection 20 · theme 15 ·
smart_money 12 · financial_strength 10 · catalyst 10 · governance 8+veto ·
valuation_sanity 5. Fundamentals are point-in-time (`scoring/pit_fundamentals.py`);
news dims are keyword+trust+sentiment filtered ("news-based v0").

**Entry / risk (mechanical, validated, NEVER AI-driven)**: technical breakout
(8-pt trend template + VCP + volume) -> two-lot ATR structure (trading lot
partial@2.5R + 50-DMA trail; core lot exits on weekly close < 30-week MA);
2.5xATR stop, skip if >12% wide; regime sizing (risk x0.5 when NIFTY < 150-DMA).

**Vetoes** (hard, cap score at 25): promoter pledge >10%, leverage+froth,
governance red flags. Data-based; AI cannot override.

**AI layers** (context/curation only, journaled, unvalidated-so-on-probation):
- Daily analyst (`ai_analyst.py`, **claude-sonnet-5**): researches top-3
  conviction buy alerts, writes VERDICT/CONVICTION/SIZE. Can only be MORE
  conservative (take/halve/skip), never override vetoes or resize up.
- Weekly committee (`ai_picks.py`, **claude-opus-4-7 + MAX_THINKING_TOKENS=24000**):
  reads the scored shortlist, selects optimum 3-5, deep-researches, writes theses.

**Dashboard** (`dashboard.html`, single self-contained SPA): tabs = Overview /
AI Picks / Screener (cap-tier + tag filters, 320 rows) / Positions / Journal /
Validation. Click any stock -> drawer with candlestick chart + why-this-score +
plan + news + fundamental trend charts.

**Ops**: Windows Task Scheduler — `MultibaggerDailyScan` 18:35 IST,
`MultibaggerWeeklyRefresh` Sun 10:00. Journal (`journal/`), health checks
(loud on stale data/broken parser/degenerate tagger), position management
(`positions.csv` vs plan), holdings drift check.

---

## 3. What's validated (evidence — see VALIDATION_REPORT.md)

- Baseline (technical-only, 2-lot, after costs): **+1.27R/trade** honest 3y
  window (+1.59R on the 7.5y look-back), payoff ~8:1, win ~28%, CAGR ~21.5%,
  maxDD ~-13%. Survivor-biased => directional; churn measured ~9.2%/2y.
- **11+ configs tested, every fundamental/sector/news GATE on entries was
  REJECTED** (price leads reported fundamentals). Entries stay technical-only.
- **Adopted**: regime sizing (Pareto improvement). **Validated as alert-only**:
  anticipation tier with fundamentals (+0.41R, positive both cohorts).
- Design is evidence-locked (PROJECT_BRIEF.md section 2B). Changing it needs
  new pre-registered evidence.

---

## 4. Live production state (as of 2026-07-09)

- **First real alerts fired 2026-07-07 18:40**: ~10 transitions incl.
  BANDHANBNK/CARBORUNIV/KARURVYSYA (buys), ACUTAAS/ANANDRATHI/SYRMA/J&KBANK
  (re-entries), CDSL/CHOLAHLDNG/NBCC (anticipation).
- **First real analyst verdicts**: SYRMA, SHILPAMED, LAURUSLABS — all BUY
  (`journal/analyst_verdicts.csv`).
- **First committee run** (was Sonnet; now set to Opus 4.7): picked
  KEI(HIGH)/STLTECH/CHENNPETRO/EMCURE/MAHABANK across 5 sectors.
- **External benchmark done**: all 5 committee picks corroborated by
  independent analysts; the AI's caution on STLTECH (MEDIUM despite top score)
  matched analysts calling it "overvalued ~67%" AND our risk engine skipping
  it as too volatile. Coupling adds real value.

---

## 5. Open items

**Needs the user (small):**
1. **Telegram** — 2-min BotFather setup, then alerts+verdicts hit the phone
   (currently they land in `daily_alerts.md` + dashboard only). See
   `scripts/send_telegram.py` header.
2. **API key (recommended)** — fixes the subscription session-limit problem
   permanently for the automation. `setx ANTHROPIC_API_KEY "sk-ant-..."`.
3. **Cloud migration (optional)** — so it runs when the laptop is off; needs
   `gh auth login` + a private repo + scheduled cloud agent decision.

**Needs time:**
4. **Forward journal** must accumulate a few weeks. Then review: do analyst
   verdicts + committee picks beat the mechanical baseline? (the real-capital
   gate, per brief).

**Worth investigating (build):**
5. **Alert volume calibration** — 2026-07-07 fired ~10 alerts in ONE day vs
   the 1-5/week design. Check whether it was a genuinely strong market day,
   a stale state baseline from testing, or the RS>=60 focus floor being too
   loose (320 names). Tightening RS floor to ~75 (-> ~150 names) was flagged
   earlier. This directly reduces analyst load / session-limit pressure.

---

## 6. NEXT TASK (what a fresh chat should pick up)

Priority order:
1. **Decide auth**: switch the daily analyst to an API key (recommended) OR
   accept subscription + reduce load via item #5. This is the main friction.
2. **Calibrate alert volume** (item #5): investigate the ~10-alert day; if the
   RS floor is too loose, raise it (build_focus_list.py `RS_PCTILE_FLOOR`, and
   consider the daily-scan watch set). Goal: alerts back to a trickle.
3. **Let the weekend weekly job run** (Sun 10:00) with the new Opus-4.7
   committee and review the picks quality vs last run.
4. **Telegram setup** whenever the user is ready (delivery layer).
5. Longer term: cloud migration + the forward-journal review after ~2-4 weeks.

Do NOT: add fundamental/news/AI signals into the ENTRY or SIZING decision
(evidence-locked). AI stays context/curation/veto only.

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
scoring/regime.py             market_risk_scale (half below 150-DMA)
backtest/engine.py            two-lot event-driven engine + regime/stress hooks
backtest/metrics.py           trade/equity/lot stats, costs, benchmark
scripts/daily_scan.py         nightly job core
scripts/ai_analyst.py         daily deep-dive (sonnet-5), conviction-prioritized, idempotent
scripts/ai_picks.py           weekly committee (opus-4-7 + high thinking)
scripts/weekly_refresh.py     full weekly chain
scripts/build_dashboard.py    dashboard.html generator
scripts/run_shortlist.py      ranked shortlist + shortlist_details.json (drawer data)
scripts/position_manager.py   open positions vs their two-lot plans
scripts/survivorship_check.py Wayback constituent diff
analyst/DEEP_DIVE_PROTOCOL.md analyst standing orders
analyst/PICKS_PROTOCOL.md     committee standing orders
tests/                        two-lot + synthetic regression (both green)
```
