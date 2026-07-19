# Strategy Review — Forward Journal Audit + External Research (2026-07-19)

Scope: (1) verify the forward journal, (2) judge whether the live logic is
behaving as the evidence said it would, (3) scan the methods of proven
momentum/breakout practitioners for upgrades worth testing. Everything in
section 3 is a PROPOSAL — nothing changes without its own pre-registered
test (PROJECT_BRIEF §2B evidence lock).

---

## 1. Journal integrity — PASS

- 151 signal rows / 105 outcome rows / 72 entry-fidelity rows; 0 duplicate
  (logged_at, symbol, kind) keys; date range 2026-07-07 → 2026-07-17.
- 16 buy-type rows without a stop = risk-engine skips (2.5×ATR > 12% cap) —
  by design, excluded from R stats.
- 9 "no data yet" rows = Friday 07-17 alerts awaiting their first bar.
- Paper book (6 positions), ledger, verdicts, committee journal all
  mutually consistent; the analyst-dead gap (Jul 10-18) is visible in the
  verdict file exactly as the incident record says it should be.
- Local price cache is 1 session behind the cloud (Jul 16 vs Jul 17) —
  cosmetic for this review; outcome stats were computed in the cloud on
  fresh data.

## 2. Is the logic sound? What 9 days of forward data actually says

**Headline: +0.049R over 105 signals, avg 3.9 days elapsed, 95 still open.
NO conclusion at this horizon** — backtest winners held 1-2 years and the
median core hold was 32 days. The number to watch is the trend, not the level.

What IS meaningful this early is **structure** — does the machine rank
things the way the evidence said it would? So far, yes, on every axis:

| Cut | Result | Reads as |
|---|---|---|
| Conviction bands | <50: −0.06R · 50-60: +0.03R · 60-70: +0.12R · 70+: +0.68R (n=3) | monotonic — the score ranks |
| Entry fidelity | AWAITING +0.00R vs NO VCP BASE −0.08R (pos rate 36% vs 21%) | the VCP/breakout mechanism shows up live |
| Kind | RE-ENTRY +0.10R vs fresh BUY −0.03R | the "load-bearing re-entry alert" finding reproduces |
| Analyst cohort | +0.34R (n=10) vs +0.02R rest; paper book +6.6%, 6/6 green | AI layer earning its keep so far |
| Stops | 1 stop-out in 105 (POLYCAB −1.0R, clean) | risk discipline intact |

Honest caveats:
- The strongest cohort ("pre-labeling", +0.24R) is also the OLDEST vintage
  (Jul 7-9) — age and cohort are confounded until labeled signals mature.
- Jul 11-16 vintages are net negative — the known chop weakness (P2 cohort)
  in a defensive tape (NIFTY < 150-DMA, half-size active — system behaving
  as designed, not a malfunction).
- **Zero VALIDATED entries in 72 labeled alerts.** Backtest frequency
  (~28 entries/yr across the universe) predicts ~0.5-1/week, so 0 in 8
  sessions is within expectation — but if this stays 0 for another 3-4
  weeks it becomes a finding (the exact backtested trigger not appearing
  in the live tape).
- Committee record is mixed (CHENNPETRO +10% vs MAHABANK −10% since pick);
  its most consistent conviction is CHENNPETRO (picked in 6/6 runs).

**Verdict: the system is doing what its evidence said it would do.
Nothing in the forward data contradicts the locked design. The sample is
too young for any expectancy claim — the review clock (§5 open item 6)
stays the gate for real-capital scaling.**

## 3. External research → candidate upgrades (each needs pre-registration)

Sources: Minervini progressive exposure / SEPA; Qullamaggie (Kullamägi)
breakout management; Bonde episodic pivots; O'Neil FTD/distribution-day
market model + pyramiding. Filtered to what fits an EOD, evidence-locked,
position-trade system — and explicitly excluding anything the matrix
already rejected (fundamental entry gates, more slots, higher risk%).

### P1 — Breadth-based regime scale (O'Neil market model, internalized)
Current regime = NIFTY vs 150-DMA (binary half/full). O'Neil's model uses
market character (distribution-day clusters, follow-through days); the
quant equivalent we can compute FROM OUR OWN CACHE tonight: % of the 651
universe above its 200-DMA (and/or net advancers). Hypothesis: a graded
breadth scale (e.g. <40% → 0.5×, 40-60% → 0.75×, >60% → 1.0×) beats the
binary 150-DMA switch on MAR/DD without hurting expectancy. Zero new data
dependencies. Test: engine `risk_scale` driven by breadth series, same
window/costs as V3b (which adopted regime sizing on exactly this bar).

### P2 — Progressive exposure (Minervini) = equity-curve feedback sizing
Scale risk with recent SIGNAL traction, not just index regime: e.g.
trailing-20-signal expectancy < 0 → 0.5-0.75×, > 0 → full 1.25×. This is
the sizing family where our only two adopted improvements (regime scale,
equity basis) both live. Natural complement to P1; test both, adopt the
Pareto winner. (Minervini: "increase only when there's traction; scale
back when trading poorly.")

### P3 — Episodic-pivot entry class (Bonde/Qullamaggie) — NEW alpha source
Gap ≥8% on ≥3× average volume with a catalyst = a technical entry pattern
(gap + volume are price/volume facts; the news radar we just built is the
natural catalyst cross-reference — attention, not gate). Why it matters
here: EPs don't need 45-week structures, so this directly attacks our
known young-IPO blind spot (IREDA/WAAREERTL missed for lack of long
bases). Backtestable from the existing cache (gaps + volume multiples are
in the data). Bigger build than P1/P2 — separate pre-registered matrix
(entry rules, stop = low of gap day, own two-lot params) before a single
live alert.

### P4 — Concentration direction (the untested half of the slot matrix)
Sizing matrix v1 tested slots {12, 16, 20} — expectancy fell monotonically
as slots rose, meaning marginal same-day breakouts are weaker. Nobody
tested FEWER: {8, 10}. O'Neil/Minervini/Kullamägi all concentrate hard.
Cheapest test on the list (one matrix run) and the existing dose-response
points in this direction.

### P5 (parked, spec only) — Faster trading-lot exits (Qullamaggie style)
Sell ⅓-½ into strength day 3-5, trail rest on 10/20-DMA vs our
partial@2.5R + 50-DMA. Core lot earned 91% of backtest profits, so the
ceiling here is low — spec it, run it only after P1-P4.

### P6 (parked, already queued) — Pyramiding winners (O'Neil: add at
+2.5-3%, taper sizes) and the IPO-base module. Both stay parked until the
forward journal matures (HANDOFF §6.4) — P3, if adopted, may cover much of
the IPO-base need for free.

### Explicitly NOT proposed
- Any fundamental/news/AI gate on entries (13 configs rejected; locked).
- Higher per-trade risk (rejected twice: DD breach + P2 negative).
- Tighter global stops (2.0×ATR): swing-style stops fight the two-lot
  position-trade design; revisit only if P5 runs.

## 4. Suggested order of operations

1. Let the forward journal run — Monday is the first night with the
   revived analyst + radar + fidelity labels all live at once.
2. P1 + P2 as one pre-registered sizing-overlay matrix (they share
   infrastructure); adopt only a Pareto winner, exactly like V3b.
3. P4 as a one-run add-on to the same matrix session.
4. P3 (episodic pivots) as its own project once 1-3 settle.
5. Re-run this review when the journal hits ~6 weeks / first VALIDATED
   cohort outcomes.
