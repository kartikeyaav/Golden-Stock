# Scoring audit — the 8 conviction dimensions against the reference systems

**Asked for (2026-08-02):** "the fundamentals, technicals, data governance,
smart money, check all the scores and the parameters we are using to create the
scores — are they good as it is weighing in our conviction score, any
improvements needed there? refer to the trademark systems and successful
traders online — and see if anything can be improved."

**Scope note, stated first because it changes how everything below should be
read.** The conviction score does **not** gate, rank or size any trade. Entries
are 100% technical and full-universe (brief §2B, evidence lock); fundamentals
survive as *vetoes* and as *context on a human's card*. Eleven overlays were
tested and rejected before that lock was written, and the monotonic
dose-response — more fundamental gating, worse expectancy — is the project's
most important empirical result. So an improvement to a dimension here improves
**how well the card explains a name to you**, not the P&L. Nothing in this
document touches an entry, a stop or a position size.

The reference systems used: O'Neil (CAN SLIM), Minervini (SEPA / trend
template), Qullamaggie (episodic pivots, breakouts), Marcellus and Motilal
Oswal (QGLP). These are the same sources the original design drew on; the
question here is whether the *implementation* still matches them.

---

## Summary of what changed

| # | Dimension | w | Verdict | Change |
|---|---|---|---|---|
| 1 | rs_and_stage | 20 | **Sound** — the only backtested dimension | none |
| 2 | earnings_inflection | 20 | **Half-implemented** | persistence term + Design Law #5 guard **shipped** |
| 3 | theme_tailwind | 15 | **Weakest weight-to-evidence ratio in the score** | flagged, not changed |
| 4 | smart_money | 12 | **Signal is being cancelled by its own arithmetic** | flagged, not changed |
| 5 | financial_strength_trend | 10 | Sound, but dead for ~20% of the universe | flagged, not changed |
| 6 | catalyst | 10 | Materially rebuilt this session | see news notes |
| 7 | governance | 8 | Blocked by data availability, with one free upgrade path | flagged, not changed |
| 8 | valuation_sanity | 5 | One real defect | PEG turnaround exemption **shipped** |

Measured effect of the two shipped changes on the live shortlist: mean move
**0.86 points** on the 100-point score, 8 of 99 names moving more than 2 points,
and one change in the top ten. Small on purpose — these are corrections to
components, not a re-weighting.

---

## 1. rs_and_stage (weight 20) — no change

RS as a 6-month/12-month blend, Weinstein stage classification, Minervini's
8-point trend template, and the VCP base test. This maps cleanly onto O'Neil's
**L** (leader, RS ≥ 80) and Minervini's trend template, and it is the *only*
dimension in the score with a backtest behind it — because it **is** the entry
system (+1.67R over 96 positions, equity-basis, costs applied).

Left alone deliberately. Changing the one thing that has been validated, in a
score that gates nothing, would be backwards.

## 2. earnings_inflection (weight 20) — CHANGED

**The defect.** The dimension read exactly one quarter: `np_latest_q` against
`np_yoy_q`. O'Neil separates **C** (this quarter) from **A** (the run of
quarters behind it) precisely because one print is noise and several in a row
is a business changing. Design Law #5 in this project's own brief asks for
"2+ consecutive improving quarters" — the margin half of that guard was
implemented, the persistence half never was.

The screener page carries **13 quarters** of Sales, Operating Profit, OPM% and
Net Profit. The score used one of them.

**Measured across the 291 scored names:**

| consecutive quarters beating their year-ago quarter | names |
|---|---|
| 0 | 62 |
| exactly 1 | 46 |
| 2–4 | 83 |
| 5–8 | 45 |
| 9+ | 49 |
| history too short to say | 6 |

A name improving every quarter for over two years and a name with a single
bounce were answering the heaviest question in the score identically. Of the 15
loss→profit names — the ones eligible for the full 1.0 — **3 turn on exactly
one quarter** (GMRAIRPORT, SPARC, MANAPPURAM).

**Shipped.** `fetch_fundamentals.flatten` now emits `np_yoy_streak` and
`opm_yoy_streak` (YoY, not sequential — Indian quarterly results are strongly
seasonal, so a Q1-vs-Q4 comparison mostly measures the calendar). The dimension
gained a persistence component at weight 0.15, and the loss→profit branch now
requires margin confirmation **and** a 2-quarter streak for full marks; margin
confirmation with a 1-quarter streak scores 0.7 with a note saying "one print,
not a trend".

Missing history **drops out and the remaining components renormalize**, rather
than scoring neutral-and-included. Absent data has been scored as good news in
this codebase three times now; it does not get a fourth.

Effect: mean 0.84 points on the 100-scale, 16 names moving >0.10 on the
dimension. Downgrades are the single-quarter names (NAZARA, NEULANDLAB, M&MFIN
lose an unearned 1.000); upgrades are the long streaks the old score could not
see (BHEL, CHENNPETRO, RAIN, TARC, HFCL).

**Known remaining gap, not shipped:** no **sales** acceleration term. O'Neil
wants sales growth ≥25% alongside earnings, and Minervini wants sales, margin
and earnings accelerating *together* — a margin-only expansion on flat sales is
cost-cutting, which does not compound. The Sales row is already parsed and
cached, so this is cheap. It is left out of this pass because it changes the
dimension's shape rather than correcting it, and it deserves its own before/after
measurement.

## 3. theme_tailwind (weight 15) — flagged, not changed

**This is the weakest weight-to-evidence ratio in the whole score, and it should
be said plainly.** 15 points ride on a cross-industry theme heat rank, and the
closest thing to it that has ever been tested here — matrix v2 config E,
sector-heat gating — was **rejected**, at +0.22R and +0.11R against an ungated
baseline of +1.27R, with the same dose-response shape as every other overlay.
The mechanism found then was that stocks *lead* their sector's turn.

Two further limits: theme membership covers only ~26% of the universe by
construction (banks, insurers, jewellers belong to no cross-industry theme), and
heat is a *rank across themes*, not an absolute — the absolute version was built
first and compressed all 18 themes into a 33–41 band.

I have not changed the weight. Re-weighting a dimension on an argument rather
than a pre-registered test is exactly what the evidence lock exists to prevent,
and the honest statement is that **15 points of a 100-point score currently rest
on the dimension whose nearest tested analogue failed**. If any weight in this
score is revisited first, it should be this one, with a file committed before
the measurement runs.

## 4. smart_money (weight 12) — flagged, not changed

Three problems, in descending order of size.

**(a) The arithmetic cancels the signal.** FII and DII changes are *summed* into
one number: `change = (fii_now - fii_then) + (dii_now - dii_then)`. Domestic
institutions selling into foreign buying nets to roughly zero, and the two
readings mean different things. HFCL is the live case — FII 7.48% → 15.74%
(+8.26) with DII 13.57% → 10.92% (−2.65) — which nets to +5.6 and saturates the
dimension at 1.0, reporting as unanimous institutional accumulation something
that is actually a handover between two kinds of institution.

**(b) It measures the wrong quantity.** O'Neil's **I** is about the *number of
institutional holders rising* and the *quality* of the sponsors, not the
aggregate percentage. Percentage held moves with price even when nobody trades.

**(c) The signal is split across two dimensions.** Promoter *buying* is scored
under governance (+0.1), not here — but a promoter adding to their own stake is
the highest-conviction insider signal available, and it belongs with smart
money.

Not changed, because the fix is a redesign rather than a correction and it wants
its own before/after on the live cache. Sketch for next pass: score FII and DII
separately, reward *agreement* between them, and treat a large divergence as
information rather than letting it cancel.

## 5. financial_strength_trend (weight 10) — flagged, not changed

The deleveraging test (debt down >20% over 3 years), D/E level, CFO sign and the
share-capital dilution check are sound, and deleveraging is the Suzlon
signature this system is explicitly hunting.

The honest limit is documented already: financial companies get a flat 0.5 and
a note, because borrowings are their raw material. That is correct — and it also
means **10 of the 100 points are dead for roughly a fifth of the universe**.
Bank-specific ratios (NIM trend, GNPA trend, CASA) are on the same screener
pages that are already being fetched and cached. This is the second-cheapest
real improvement available after sales acceleration.

## 6. catalyst (weight 10) — rebuilt this session

Covered in the news notes rather than here. In brief: filings are now deduped by
*event* rather than subject prefix, headlines are ranked by materiality rather
than fetch order, the fetch no longer discards two thirds of what the feed
returned, three new event classes (capex/investment, deleveraging, partnership)
and the pharma exclusivity class were added, and a decimal point inside a rupee
figure no longer makes every quarterly results headline read as neutral.

Measured across 18 live names after the change, catalyst spreads 0.00–1.00 with
a median of 0.55 and only one name pegged at the top. For comparison, the
pre-2026-07-28 version produced five distinct values over 117 alerts with 54% at
or below 0.1. It is still labelled v0 and still unvalidated forward.

## 7. governance (weight 8) — flagged, not changed

Currently pledge percentage plus promoter-stake trend. The pledge branch was
corrected on 2026-07-28: screener.in publishes pledge **only** when material, so
a verified zero is unobtainable from this source and `None` now scores 0.70
("not flagged") rather than 0.85 ("confirmed zero"). That remains right.

Every card still reads "auditor/SEBI/related-party checks pending (Phase C)",
and it has read that since Phase C shipped, because no free source publishes
them as structured data.

**There is now a free upgrade path that did not exist before.** This session's
work made `data/news_radar.classify` able to recognise real regulatory action —
SEBI/RBI/NSE warnings, debarments, show-cause notices, search-and-seizure — as
distinct from the LODR boilerplate that had been generating 35 of this system's
51 all-time red flags. And `announcements_archive.csv` holds **27,115
first-party filings** going back weeks, matched per company. A governance term
that reads that archive for regulatory actions against the name would be a real
measurement of something the card currently declares "pending". Not built here;
it is a new dimension component, not a correction.

## 8. valuation_sanity (weight 5) — CHANGED

The froth-versus-inflection distinction added on 2026-07-07 was only applied
above P/E 60. Below that, the score falls to a PEG branch — and **PEG uses the
three-year profit growth rate**, which for a turnaround spans the loss years and
comes out near zero, so the ratio explodes.

HFCL is the case: P/E 52.6 against 3-year profit growth of 1% scored "full
price, PEG 52.60", while its TTM growth was 1591% and its operating margin had
gone −5% → 22% over five quarters. The exact archetype this system hunts,
penalised by a denominator drawn from the period it was recovering from.

**Shipped.** The existing `inflection` test now also guards the PEG branch,
scoring 0.5 with an explanation instead of 0.45 with a misleading number.
Catches 3 names in the current file: HFCL, QUESS, IIFL — all genuine
turnarounds. Deliberately narrow; a mature company at a bad PEG is still scored
as one.

---

## What was deliberately NOT done

* **No weight was changed.** Every weight in this score is a pre-registered
  starting point, and moving one on an argument rather than a walk-forward test
  is the failure mode the evidence lock was built to stop. The theme_tailwind
  weight is the one that most deserves a test — that is a recommendation, not a
  change.
* **No new gate, filter or sizing rule.** Entries remain 100% technical.
* **Nothing was tuned to make a name look better.** The two shipped changes
  move the shortlist by a mean of 0.86 points and were measured before being
  accepted.

## Ranked queue for the next pass

1. **Sales acceleration** in earnings_inflection — data already cached, closes
   the O'Neil/Minervini "margin expansion on flat sales is cost-cutting" gap.
2. **Split FII from DII** in smart_money and reward agreement — the current sum
   actively destroys information.
3. **Governance from the filings archive** — 27,115 first-party filings and a
   classifier that can now read regulatory action, against a card that says
   "pending".
4. **Bank-specific financial strength** — 10 points are inert for ~20% of names.
5. **A pre-registered test of the theme_tailwind weight** — 15 points on the
   dimension whose nearest tested analogue was rejected.
