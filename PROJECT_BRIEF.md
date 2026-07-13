# Golden-Stock Watchlist & Screener — Project Brief v2

*This file is the north star for the project. Any Claude Code session working on
this project should read this file first and treat Section 4 (Design Law) as
binding constraints, not suggestions.*

**Version 2 — 2026-07-04.** Supersedes the v1 brief (quality-compounder screener).
v1's engine and risk discipline survive; v1's *target definition* does not — see
Section 1 for why. Strategy design validated by an adversarial review pass; the
corrections from that review are locked in as Design Law (Section 4).

---

## 1. Mission

Build a repeatable, mechanized research system that finds **"golden stocks"** on
the Indian market — names capable of an absolute bull run (3-10x+ over months to
years) — *before or just as* the crowd finds them, and that outputs concrete,
sized, two-lot trade plans with transparent reasoning. Decision support only;
no order execution.

### The exemplars that define the target

| Exemplar | Type of run | What drove it | What it looked like at the ideal buy point |
|---|---|---|---|
| **Suzlon** ('22→'24, ~₹5→₹60s) | Turnaround / deleveraging | Debt restructuring, loss→profit swing, renewables tailwind | **Terrible on paper**: loss-making, drowning in debt, penny stock |
| **BSE** ('21→now) | Structural super-cycle | Retail derivatives boom, exchange duopoly, new products | Decent but boring on paper; the *sector inflection* was the signal |
| **Adani group** ('22→'23 peak) | Hyper-growth capex + theme + flows | Aggressive expansion, govt-aligned infra, index inclusion | Extremely leveraged, extremely expensive — **and it ended −60% post-Hindenburg** |

### The core insight (this is why v1 was rebuilt)

A static quality screen (ROCE > 15%, D/E < 0.5, PEG < 1.5) would have **rejected
Suzlon and Adani at exactly the moment they were the best buys of the decade**.
Quality-compounder filters find Page Industries, not the next Suzlon.

Therefore this system scores **change and inflection, not just level**:
- Every fundamental dimension blends *level* + *trajectory (Δ)*, weighted toward Δ.
- The technical layer hunts *multi-year bases resolving into Stage-2 breakouts* —
  the one signature all three exemplars shared.
- Themes/sectors are first-class signals (BSE was a derivatives-boom story before
  it was a BSE story).

And one explicit anti-goal: **the Adani '22 profile (extreme leverage + extreme
valuation + opaque structure) is what the veto layer exists to EXCLUDE, not a
target.** We accept that safety filters will miss some monsters. Expectancy over
trophy-hunting.

---

## 2. System overview — the two-layer watchlist

Every stock in the universe gets **two tags + one score**. Nothing is a naked
"BUY"; everything is a tagged, scored, reasoned watchlist entry.

### Layer 1a — Stage tag (ripeness; which entry style applies)

Mechanical definitions (no chart-gazing). Weekly frame: 30-week MA of weekly
closes (proxied by the 150-day SMA on daily data), slope measured over the
trailing 8 weeks, "flat" = |slope| below a config band. `pos52` = position of
price within the 52-week range (0 = at low, 1 = at high).

| Tag | Mechanical rule | Meaning / action |
|---|---|---|
| **ANTICIPATION** | Stage 1 (flat 30wMA, price near it, lower half of 52w range) AND base depth ≤ 40% AND price within 25% of base high AND RS improving. Phase B adds: fundamentals inflecting. | Watch. **Zero capital** until Phase B validation (Design Law #8). |
| **CONFIRMED** | Stage 2 (price > rising 30wMA) AND passes 8-point trend template AND not Extended. | Buyable on a defined pivot/breakout trigger. |
| **EXTENDED** | Stage 2 but price > 25% above 50-DMA or > 3.5×ATR above it. | Right idea, wrong price. Wait for a proper base/pullback setup. |
| **BROKEN** | Stage 4 (price < falling 30wMA), or Stage 3 with price below the MA. | Avoid / exit core positions. |
| **WATCH** | Anything else (transitional). | Neutral; keep scoring. |

Stage classification: price>MA & slope>+band → Stage 2 · price<MA & slope<−band
→ Stage 4 · slope within band → Stage 1 if pos52 < 0.5 else Stage 3.

### Layer 1b — Archetype tag (what kind of story; can be multiple)

| Archetype | Signature (scored on Δ, not level) |
|---|---|
| **Turnaround** | Loss→profit swing, D/E falling multiple quarters, interest coverage flipping positive |
| **Super-cycle / Theme** | Sector-level inflection (govt push, demand super-cycle), stock is leader or picks-and-shovels |
| **Hyper-growth capex** | Capacity expansion + order book → future operating leverage. **Leverage/valuation guardrails always on** |
| **Quality compounder** | High and stable ROCE, clean balance sheet, steady growth (the v1 target — still valid, just no longer the only target) |

Archetype tagging is fundamentals-driven → Phase B. Until then stocks carry
`archetype: unassessed`.

### Layer 2 — Conviction score (0-100), with honesty rules

Eight dimensions, weighted, each 0-1. **Coverage rule (Design Law #1):** the
composite is computed only over dimensions with live data, weights renormalized,
and every displayed score carries its **coverage %**. Below 60% coverage the
score is labeled a *Technical Read*, not a Conviction score, and no 0-100
conviction card is shown.

| # | Dimension | Weight | What scores high | Phase |
|---|---|---|---|---|
| 1 | Earnings inflection & quality | 20 | PAT/EBIT accelerating YoY, loss→profit, margins/ROCE rising (level+Δ, Δ-weighted) | B |
| 2 | Relative strength & stage | 20 | RS blend (0.6×6m + 0.4×12m) percentile, healthy base (depth/duration), Stage 2, live trigger | **A (now)** |
| 3 | Industry / theme tailwind | 15 | Sector super-cycle, govt push (PLI, defence, capex...), leader or picks-and-shovels | C |
| 4 | Smart money & ownership | 12 | FII/DII stake rising, promoter buying, delivery % rising, bulk deals | C |
| 5 | Financial strength trend | 10 | Debt falling, interest coverage rising, CFO turning positive, **share count not exploding** | B |
| 6 | Catalyst (dated events) | 10 | Order wins, capacity commissioning, guidance raises, exports | C |
| 7 | Management & governance | 8 **+ veto** | Clean pledge history, no auditor/CFO churn, sane related-party ledger, capital allocation | C |
| 8 | Valuation sanity | 5 | NOT cheapness — only penalizes extreme froth (blow-off P/E vs history/sector) | B |

**Vetoes (hard caps, not weights):** promoter pledge above threshold · auditor
resignation · SEBI action / credible fraud allegation · going-concern doubt ·
extreme leverage + froth combination (the Adani rule). Any triggered veto caps
the composite at 25 regardless of other scores.

**Boundary rule:** Theme (dim 3) = slow-moving sector tailwind, months-years.
Catalyst (dim 6) = dated, company-specific event. An item goes in exactly one.

### What a finished pick card looks like (Phase C target)

```
XYZ Ltd — Conviction 84/100 (coverage 92%)
Tags: CONFIRMED · Turnaround + Super-cycle
Why: PAT positive 2 qtrs and accelerating · D/E 2.1→0.9 over 4 qtrs ·
     defence-electronics indigenisation tailwind · RS 92 · broke 3-yr base on 3× volume ·
     FII +180bps QoQ
Plan: Entry ₹420-430 · ATR stop ₹388 (risk 1.25% of book)
      Trading lot (50%): partial at 2.5R ≈ ₹510, then trail 50-DMA
      Core lot (50%): exit only on weekly close < 30-week MA
Risks: raw-material inflation · dilution history · circuit-limit liquidity
Veto check: clean (pledge 0%, auditors stable)
```

---

## 2A. The identification pipeline (canonical, finalized 2026-07-04)

Doctrine: find stocks where an improving business meets a confirmed breakout
from a long base, in a sector with a tailwind — buy only on confirmation,
size so being wrong is cheap, hold in two lots so winners can become
multibaggers. **Alerts fire on STATE TRANSITIONS, never on list membership**
(a score level that stays high fires daily-spam or goes permanently silent;
a transition is rare and actionable). News NOMINATES names onto the focus
list; price CONFIRMS and times the entry.

| # | Step | Cadence | Rule | Survives |
|---|---|---|---|---|
| 1 | Universe | weekly | Nifty Smallcap 250 + Midcap 150 + Microcap 250 constituents; ADV >= 1 Cr; price >= Rs 2; listing age = flag only. Historical constituent lists double as the survivorship-bias mitigation | ~650 |
| 2 | Garbage filter + vetoes | weekly | Hard vetoes (pledge >10%, auditor churn, SEBI flags, going-concern). Keep if EITHER improvement path (operating earnings inflecting 2+ qtrs / debt falling) OR quality path (sustained ROCE, clean B/S). Never static-quality-only | ~300-450 |
| 3 | Strength rank | weekly | RS percentile (0.6x6m + 0.4x12m) >= ~60, PLUS Stage-1 names with improving RS (anticipation pipeline) | ~100-150 = FOCUS LIST |
| 4 | Stage tags | daily | Mechanical Weinstein tags on focus list + all holdings | — |
| 5 | Trigger detection | daily | Stage-2: base + pivot break on >=1.5x volume today. Stage-1: anticipation gate newly satisfied | — |
| 6 | Transition diff | daily | Diff vs yesterday's state file. Fresh breakout -> BUY CANDIDATE; new ANTICIPATION -> WATCH (zero capital); EXTENDED cooled -> RE-ENTRY; holding BROKEN -> EXIT WARNING. No transitions = silence | 1-5 alerts/week |
| 7 | Deep dive | per transition | Conviction score + vetoes + on-demand qualitative research (news/theme/mgmt/smart money) on the 1-3 transitioned names ONLY — never daily across the list (LLM score drift + cost). Cache until a new filing/event | 0-3 cards |
| 8 | Trade plan | per card | Section 3 two-lot spec | — |
| 9 | Feedback loop | continuous | Log everything; baseline-first marginal testing (Section 6); pre-registered threshold changes only | — |

Delivery: Telegram bot (scripts/send_telegram.py) + Windows Task Scheduler
(daily 18:35 IST scan, Sunday 10:00 weekly refresh), registered 2026-07-06.

---

## 2B. EVIDENCE-LOCKED AMENDMENTS (2026-07-06 — supersede anything above that conflicts)

Two pre-registered experiment matrices (11 configs, point-in-time fundamentals,
2023-08→2026-07, full detail in multibagger_screener/VALIDATION_REPORT.md)
locked the following. Changing these requires NEW pre-registered evidence:

1. **Entries are 100% technical, across the FULL universe.** Every tested
   gate — PIT fundamental gates (3 variants), fundamental entry-ranking,
   sector-heat gates (2), core-lot patience, fundamental lot-splits — reduced
   expectancy, monotonically with gate strength (baseline +1.27R vs +0.11 to
   +0.54R gated). Mechanism: price leads confirmation; gates remove exactly
   the explosive early-turnaround entries (TARIL scored 0.537 while starting
   its 13x). The conviction score NEVER gates the machine.
2. **Fundamentals = vetoes + human card context only.** Vetoes target ruin
   avoidance (untestable in-window, kept on tail-risk logic, cost ≈ 0).
3. **The focus list is reporting/prioritization only.** The daily scan
   watches the whole universe — a focus-filtered scan would be an untested
   gate (this exact bug was caught and fixed 2026-07-06).
4. **Phase C news/catalyst is live-only enrichment** on alert candidates
   (no historical corpus exists); any future weight must be earned through
   the forward journal.
5. **Execution robustness verified:** next-open fills +0.96R, 0.40%/side
   costs +1.20R, gap-aware stops +1.23R — the edge is not fill-dependent.
6. **Known weakness, accepted:** choppy regimes (2025+ cohort +0.15R across
   ALL configs). Managed by drawdown discipline and sizing, never by adding
   filters (all 8 tested filters made it worse).
7. **Forward journal is the ongoing audit** (journal/signals_journal.csv,
   append-only, auto-written by the daily scan; outcomes via
   journal_outcomes.py). Real-capital gate: journal expectancy within ~50%
   of backtest at meaningful sample size; small sizes until then.
8. **Regime sizing ADOPTED (matrix v3b):** risk per trade ×0.5 whenever
   NIFTY50 closes below its 150-DMA. Identical trades, higher CAGR, lower
   drawdown in test. Sizing only — never an entry filter.
9. **Anticipation tier validated as an ALERT tier (matrix v3a):**
   Stage-1-base signals WITH PIT fundamentals ≥0.60 earned +0.41R (positive
   both cohorts, 7× better than price-only) — proof that fundamentals lead
   price INSIDE bases even though they lag at breakouts. Still zero capital:
   +0.41R < +1.27R breakout economics; the tier's job is earlier attention.
10. **Survivorship bounded by measurement:** 9.2% smallcap churn per ~2 years
   (Wayback diff), mostly mergers/renames. Backtests modestly optimistic,
   not fantasy (see survivorship_report.md).
11. **Sizing basis corrected — equity, not cash (matrix v2, 2026-07-12):**
   the engine sized risk% and the position-value cap off REMAINING CASH,
   which undersizes every late entry (at ~73% typical deployment, a "1.25%
   risk" trade was actually risking ~0.3%). Fixed-fractional on
   marked-to-market EQUITY (same entries, same stops, same everything else)
   corrected the read: window CAGR 22.5%->47.4% ideal / 32.5% under
   deployment stress (next-open fills + gap-aware stops + full costs), maxDD
   -12.9%->-18.5%/-20.7%, chop cohort IMPROVED not worsened. This is a
   MEASUREMENT fix, not a new strategy — live plans were never affected (they
   already size off configured capital). Also tested and REJECTED in the same
   matrix: expanding the 15% position-value cap (adds nothing at 1.25% risk)
   and raising risk-per-trade above 1.25% (breaches the drawdown bound and
   turns the chop cohort negative again — same monotonic-rejection shape as
   every other over-aggressive lever). Full table: multibagger_screener/
   multibagger_screener/sizing_matrix2_report.md.

---

## 3. Trade management spec (two-lot structure)

This is Design Law #2 and it exists because the exemplars **drew down 30-50%
mid-run** (BSE 2024, Suzlon repeatedly). A single tight trail converts a 10x
into three +30% trades. So every position splits at entry:

| | Trading lot (default 50%) | Core lot (default 50%) |
|---|---|---|
| Purpose | Pay for the risk, validate fast | The lot that's allowed to become a 10x |
| Initial stop | Shared: entry − 2.5×ATR(14), skip trade if that's wider than the hard cap (12%) | Same shared initial stop |
| Breakeven | Both lots' stops move to entry at +1.5R | Same |
| Profit taking | Sell ⅓ of lot at +2.5R | None |
| Trail | After partial: exit on daily close < 50-DMA | **Only** weekly close < 30-week MA (150-day SMA proxy) |

**Sizing (risk-normalized, Design Law #7):** `shares = (equity × risk% ) /
(entry − stop)`. Wider stop ⇒ automatically smaller position, same ₹ at risk.
Position value additionally capped at 15% of equity. Portfolio: max 12 open
positions · max ~25-30% of book in Turnarounds · theme caps (no six correlated
defence names) · 25% portfolio-drawdown circuit breaker (pause + review, never
widen rules).

Turnaround-specific: minimum ADV liquidity floor, circuit-band awareness (a
low-price name in a lower-circuit freeze cannot be exited at the "stop"),
dilution/share-count check.

---

## 4. Design Law — binding corrections (from the validation pass, 2026-07-04)

These were the failure modes found when red-teaming the design. **Do not build
in violation of these.**

1. **No false-precision scores.** Composite only over live dimensions, weights
   renormalized, coverage % always displayed. No 0-100 conviction card below
   60% coverage — until then output is labeled "Technical Read".
2. **Two-lot exits are mandatory** (see Section 3). Backtests must report the
   two lots separately.
3. **Backtest = marginal-value test.** The technical-only system (Phase A) is
   the BASELINE. Every later dimension must beat the baseline out-of-sample or
   it is decoration and gets weight 0. No free weight optimization — a small
   set of pre-registered coarse weight configurations, walk-forward evaluation.
   If rankings flip when a weight moves ±5 pts, the signal isn't real.
4. **Survivorship bias is partly unsolvable on our free data stack.** Kite and
   screener.in drop delisted names. Mitigate by building historical universes
   from index-constituent snapshots where possible. All first-pass backtest
   results are DIRECTIONAL only: failing a favorably-biased backtest kills a
   strategy; passing one merely means "not yet dead". Never quote raw backtest
   CAGR as expected return.
5. **Δ-scoring guards:** YoY comparisons only (seasonality); require ≥2
   consecutive improving quarters; check EBIT-level, not just PAT (one-off
   "other income" fakes turnarounds — Suzlon itself did this in past cycles);
   winsorize % changes (loss→small-profit = ∞ growth); cyclicals show beautiful
   ROCE inflection at cycle TOPS — sector-relative context required.
   **Point-in-time discipline:** every fundamental record carries a
   `known_as_of` date (~45-day filing lag; shareholding files with a lag too).
6. **The Adani profile is a veto target, not a hunt target.** Extreme leverage
   + froth + opacity stays excluded even though it will cost us some winners.
7. **Turnaround mechanics:** ATR-based stops with risk-normalized sizing (no
   fixed 8% stop), hard stop-width cap (skip untradeably volatile setups),
   min-ADV floor, circuit awareness, archetype exposure cap, dilution check.
8. **Anticipation tier ships watchlist-only.** Mechanical triggers + aging rule
   (bases that never break out expire off the list). Zero capital and no
   claimed backtest validity until point-in-time fundamentals exist (Phase B+).
9. **Listing age is a FLAG, not a gate.** All three exemplars fail the old
   2-6-year filter. Universe = NSE main board + liquidity floor (optionally
   excluding the very largest caps). "Recent IPO" becomes one theme flag.
10. **Stage tags are mechanical** (30-week MA, 8-week slope, pos52, ATR/pct
    extended rules — Section 2). RS = 6m+12m blend. Base depth/duration are
    computed metrics, not judgment calls.
11. **Theme vs Catalyst boundary** as defined in Section 2.

---

## 5. Architecture

```
Pipeline:  Universe → per-stock OHLCV cache → Stage/Archetype tagger
           → Dimension scores (1-8, phased) → Vetoes → Conviction + coverage
           → Two-lot entry plans → Watchlist report
           → (separately) Backtest engine → baseline & marginal-value metrics
```

### Data spine (dual path — decided after live validation)

| Path | Used for | Why |
|---|---|---|
| **Yahoo Finance chart API → local CSV cache** (`data/yahoo_loader.py` + `data/cache.py`, stdlib urllib, no API key) | Bulk historical daily OHLCV for the whole universe + benchmarks | Free, scriptable, no per-call context cost. OHLC is split/bonus-adjusted (verify around known events, e.g. BSE's 2:1 bonus 2025) |
| **Zerodha Kite MCP** (already connected & validated) | Instrument metadata incl. listing dates, live LTP/quotes, spot-verification of Yahoo data, portfolio context | Validated 2026-07-04: serves multi-year daily OHLCV back to listing. Caveat: corporate actions can spawn a new token with truncated history (MOSCHIP token history starts 2025-02-05) |

Rule: the Python engine reads **only the local cache**; network fetches are a
separate, explicit backfill/update step. Spot-check protocol: after each bulk
backfill, diff a sample of rows against Kite MCP values before trusting.

### Module map (`files/multibagger_screener/multibagger_screener/`)

| Module | Status | Role |
|---|---|---|
| `config.py` | **v2 rewrite** | Every tunable: risk/two-lot, stage tagger, conviction weights, vetoes, universe |
| `data/cache.py` | **new** | CSV-per-symbol OHLCV cache + manifest |
| `data/yahoo_loader.py` | **new** | Yahoo chart-API fetch → cache (stdlib only) |
| `data/kite_client.py` | kept (unused for bulk) | Legacy paid-API path; superseded by MCP+Yahoo |
| `data/fundamentals_loader.py` | kept, Phase B | screener.in export ingestion (needs `known_as_of` addition) |
| `data/shareholding.py` | kept, Phase C | Promoter holding/pledge trend |
| `data/news_catalyst.py` | kept, Phase C | Theme/catalyst tagging (LLM-assisted) |
| `scoring/stage_tagger.py` | **new** | Mechanical Weinstein stages + watchlist tags + base metrics + RS blend |
| `scoring/technical_score.py` | extended | Trend template, VCP, breakout (validated); + ATR; entry plan → ATR-based |
| `scoring/conviction.py` | **new** | 8-dimension composite, coverage renormalization, veto engine |
| `scoring/fundamental_score.py` | kept, Phase B rework | Will be rebuilt around level+Δ per Design Law #5 |
| `backtest/engine.py` | **v2 rewrite** | Two-lot event-driven engine, ATR stops, weekly core exit, exposure caps |
| `backtest/metrics.py` | extended | Per-lot stats, costs, benchmark comparison |
| `reports/watchlist_card.py` | **new** | Tagged, coverage-honest cards (ASCII-safe) |
| `scripts/fetch_data.py` | **new** | CLI backfill: Yahoo → cache |
| `scripts/demo_phase_a.py` | **new** | Run tagger + technical read on cached names → report |
| `tests/` | extended | Synthetic regression (v1) + two-lot engine test |

---

## 6. Backtest protocol

1. **Baseline first.** Phase A produces the technical-only system's numbers on
   real data (trend template + VCP/breakout + two-lot management, static
   neutral fundamentals). This number is the bar.
2. **Marginal value.** Each dimension added later must improve out-of-sample
   expectancy/Sharpe over the baseline, else weight 0 (Design Law #3).
3. **Walk-forward** with an untouched holdout period. Archetype/threshold rules
   are defined from principles BEFORE testing (no tuning on Suzlon/BSE — the
   exemplars are qualitative design guides, not fitting targets).
4. **Costs:** apply `apply_costs()` with Zerodha delivery brokerage + STT +
   small/mid-cap slippage before quoting anything.
5. **Per-lot reporting:** trading lot and core lot evaluated separately (the
   core lot is the multibagger claim; the trading lot is the survival claim).
6. **Point-in-time and survivorship rules** per Design Law #4 and #5.

### Success metrics (evaluated on real data, after costs)

| Metric | Minimum bar | Target |
|---|---|---|
| Expectancy per trade (blended) | > 0R | ≥ +0.3R |
| Payoff ratio (avg win : avg loss) | ≥ 1.5:1 | ≥ 2.5:1 |
| Core-lot capture | — | ≥ 1 trade per ~25 that exits ≥ +5R (the golden-stock claim) |
| Win rate | tracked, never optimized | — |
| CAGR vs Nifty Smallcap 250 / Midcap 150 | beats | by ≥ 8-10 pts/yr |
| Max drawdown | ≤ 30% | ≤ 25% |
| Sharpe (annualized) | ≥ 0.7 | ≥ 1.2 |
| Closed trades before trusting anything | ≥ 50 | ≥ 100 across ≥ 2 cycles |
| Screening funnel | fundamental filter passes 2-90% of universe (outside that = broken) | — |

Out-of-sample degradation > ~30-40% vs in-sample ⇒ thresholds were fit to noise.
Paper trading (Phase D): 3-6 months forward; realized expectancy within ~50% of
backtest or find the hidden bias before any real capital.

---

## 7. Roadmap & acceptance gates

**Phase A — Technical spine (NOW).**
Build: config v2 · cache + Yahoo loader · stage tagger · conviction skeleton
(dim 2 live, honest coverage) · two-lot engine · watchlist cards · demo on
exemplars (Suzlon, BSE) + a pilot basket.
*Acceptance:* synthetic tests pass (incl. two-lot behaviors) · tags on the
exemplars match their known history at key dates · baseline backtest run on a
real pilot universe with ≥50 closed trades, per-lot metrics reported.

**Phase B — Fundamentals with time discipline.**
screener.in ingestion with `known_as_of` · level+Δ scoring with all Design Law
#5 guards · dims 1, 5, 8 live · archetype tagging live · anticipation-tier
triggers validated · marginal-value test vs Phase A baseline.
*Acceptance:* out-of-sample improvement over baseline or the dimension's weight
goes to 0.

**Phase C — Theme, news, ownership, governance agents.**
Theme map + news/catalyst tagging (LLM-assisted reading of filings/news) · FII/
DII/promoter/delivery tracking · governance vetoes live · dims 3, 4, 6, 7.
*Acceptance:* same marginal-value bar. Coverage crosses 60% ⇒ real Conviction
cards unlock.

**Phase D — Forward validation.**
3-6 months paper trading on live signals · divergence analysis · only then any
real capital, at reduced size.

---

## 8. Out of scope / disclaimers

- **No automated order execution.** Research and decision support only. Any
  execution is a separate, independently reviewed component gated on Phase D.
- **Not investment advice.** Every number here is a target for evaluating the
  *system*, not a promised return. Backtests on this data stack are known to be
  optimistic (Design Law #4). Verify qualitative claims against primary sources
  before risking capital.
- Model workflow note: strategy validation passes run on a different model than
  build passes (user preference), so this brief must stay self-contained.

## 9. Current status (2026-07-04)

- Zerodha MCP validated as data/verification path; Yahoo chosen for bulk.
- v1 engine (trend template, VCP, breakout, sizing, backtest bookkeeping)
  verified on synthetic data; runs on local Python 3.14.
- Phase A build in progress: config v2, cache, tagger, conviction, two-lot
  engine, cards, demo.
- Next: Phase A acceptance run (pilot universe baseline backtest).
