# Implementation proposals for the five deferred scoring improvements

Follow-up to `SCORING_AUDIT_2026-08-02.md`, which listed five improvements and
built none of them. This document designs each one against **what the data
actually contains**, checked before any design was written.

**That check changed two of the five recommendations, and one of them was
wrong in a way worth stating plainly.** The audit recommended bank-specific
ratios "NIM trend, GNPA trend, CASA" — none of those exist on the free
screener.in page. It also called a governance term from the filings archive
"a real measurement"; the archive yields roughly **8 governance-relevant events
across 651 names per three weeks**, which is too sparse to move a score and
exactly the right density for a flag. Both are corrected below.

Everything here remains decision-support. The conviction score gates no entry,
no stop and no position size (brief §2B). These proposals change how well a
card explains a name, not the P&L.

---

## 1. Sales acceleration in `earnings_inflection` — READY, recommend building

### What the reference systems actually say

O'Neil's **C** criterion is not earnings alone. He wants same-quarter sales
growth above **25%**, *or* clearly accelerating sales growth over the last
**three** quarters, and the stated reason is exactly the failure mode this
dimension has: earnings can be lifted by cost cuts, one-offs or accounting, and
sales confirm the growth is real ([AAII on
CAN SLIM](https://www.aaii.com/journal/article/how-to-use-the-can-slim-approach-to-screen-for-growth-stocks)).

Minervini is more explicit about the triple: sales above ~15% YoY and
accelerating, earnings ≥20% and accelerating, **and margins expanding** —
"when dealing with growth stocks, really only three things matter: earnings,
sales, and margins" ([SEPA
overview](https://www.quantvps.com/blog/mark-minervini-trading-strategy/)).

Our dimension currently scores earnings and (in the swing branch only) margins.
Sales is absent entirely.

### Data check

`Sales` quarterly series present for **257 of 291** scored names (the other 34
are bank-shaped and carry `Revenue` instead — handled in §4). 13 quarters each.
Already parsed, already cached, zero network.

### Proposed design

Add a fourth input to `score_earnings_inflection`, computed in `flatten` the
same way `np_yoy_streak` was:

```
sales_yoy_pct      # latest quarter sales vs the same quarter last year
sales_yoy_streak   # consecutive quarters beating their year-ago quarter
```

Then a **confirmation multiplier**, not a fifth additive component:

| condition | effect | rationale |
|---|---|---|
| sales YoY ≥ 25% **or** sales streak ≥ 3 | ×1.0 | O'Neil's C is satisfied |
| sales YoY ≥ 10% | ×0.92 | growing, below the bar |
| sales YoY between −5% and +10% | ×0.80 | earnings improving on flat sales |
| sales YoY < −5% while profit is up | ×0.65 | **cost-cutting, not growth** |
| sales series absent | ×1.0 | never penalise for missing data |

**Why a multiplier and not a component.** A component would let strong sales
*rescue* a weak earnings score, which is not what either system claims. Both
treat sales as *confirmation* of an earnings signal. The multiplier can only
discount, never inflate, and it caps at the current score.

The falling-sales-rising-profit case deserves the note text spelled out on the
card — "profit up on sales down 8%: margin-led, check whether it is cost
cutting" — because that is the single most useful sentence this dimension could
say and it currently cannot say it.

**Expected impact:** unknown until run. Measure before shipping, same as the
persistence term (which moved the shortlist a mean of 0.86 points).

---

## 2. Split FII from DII in `smart_money` — READY, recommend building first

### The measurement that settles the design

Current code: `change = (fii_now − fii_then) + (dii_now − dii_then)`, one sum.

Across the 290 scored names with all four values:

| | names |
|---|---|
| both buying | 59 |
| both selling | 20 |
| **moving in opposite directions** | **152** |

**52% of the universe has the two legs fighting each other**, and the sum
reports the residue as if it were a consensus. The worst cases are not marginal:

| | FII Δ | DII Δ | sum the score sees |
|---|---|---|---|
| AAVAS | −13.03 | +10.62 | −2.41 |
| FEDFINA | +8.13 | −8.47 | −0.34 |
| CUB | −7.31 | +8.09 | +0.78 |
| VIJAYA | −6.62 | +6.27 | −0.35 |

AAVAS had a 13-point foreign exit absorbed by a 10-point domestic entry — a
complete change in who owns the company — and the dimension scored it as
"roughly flat".

### What the research says about the two legs

They are not interchangeable in India. FII flows are the stronger *short-term
momentum* indicator and are driven substantially by global risk conditions
rather than India-specific fundamentals — dollar strength and US rates move them
regardless of the company. DII flows are structural and systematic (SIP-driven),
absorb FII volatility, and are the better read on sustained direction
([HDFC MF](https://www.hdfcfund.com/learn/blog/what-fii-and-dii-meaning-full-forms-and-role-indian-stock-market),
[MNCL](https://www.mnclgroup.com/how-fiis-drive-momentum-in-indian-stocks)).

O'Neil's **I** is a third thing again: the *number of institutional holders
rising*, and the quality of the sponsors — not the percentage held, which drifts
with price even when nobody trades.

### Proposed design

Score the two legs separately, then combine on **agreement**:

```
fii_score = clip01(0.5 + fii_delta / 6)     # ±3pp saturates
dii_score = clip01(0.5 + dii_delta / 6)
agree     = sign(fii_delta) == sign(dii_delta) and both |Δ| > 0.2

if agree:      score = mean(fii, dii), then pushed 15% toward the extreme
elif diverge:  score = 0.5 + 0.35 * (dii_score - 0.5) + 0.25 * (fii_score - 0.5)
else:          score = mean(fii, dii)
```

Two deliberate asymmetries, both defensible from the research:

* **Agreement is worth more than either leg alone.** Two independent pools of
  capital moving the same way is the closest thing to O'Neil's "increasing
  number of sponsors" that this data can express.
* **On divergence, DII gets the larger weight.** FII moves are contaminated by
  global risk-on/risk-off that says nothing about the company; DII flows are
  the domestic, structural read. This is the one judgement call in the design
  and it should be labelled as such on the card.

The note text must name both legs and the verdict: *"FII 7.5→15.7% buying, DII
13.6→10.9% selling — foreign accumulation into domestic distribution"*. Today
it prints both numbers and then a score that reflects neither.

**Also fold in promoter buying**, currently sitting in `governance` at +0.1.
A promoter adding to their own stake is the highest-conviction insider signal
available and it belongs in smart money, not in a governance hygiene check.

**Recommend building this first** of the five: the defect is the largest
(52% of names), the fix is contained, and no new data is needed.

---

## 3. Governance from the filings archive — CORRECTED, build as a FLAG not a score

### The audit was too optimistic; here is the measurement

27,115 filings, roughly three weeks of archive, classified and matched to
universe symbols:

| signal | filings | **universe names** |
|---|---|---|
| auditor resignation | 11 | **1** |
| CFO/CEO/MD resignation | 13 | 4 |
| qualified / adverse audit opinion | 11 | 2 |
| pledge creation or invocation | 3 | 1 |
| related-party transaction | 2 | 0 |
| rating downgrade | 0 | 0 |
| default / payment delay | 57 | **0** (all outside the universe) |
| all negative classes combined | 42 | 35, of which 33 are routine director changes |

**Roughly 8 genuinely governance-relevant events across 651 names per three
weeks.** A scoring component built on that would leave 643 names unchanged and
is not a measurement of anything. The audit's claim that it "would be a real
measurement of something the card currently declares pending" was wrong at the
density the data actually has.

### What it IS good for

Sparse-but-real is the exact profile of a **ruin-avoidance signal**, and this
project already treats those differently from scoring inputs: vetoes optimise a
different objective than expectancy and survived the matrix rejections for that
reason.

The research agrees on which signal matters most: a **statutory auditor
resigning mid-term** is the strongest single governance red flag available,
because no auditor walks away before signing unless compelled
([Business Standard](https://www.business-standard.com/article/pf/investors-backing-off-as-auditors-continue-to-resign-from-leading-firms-118060601254_1.html)).
Related-party transactions above ~10% of revenue and promoter pledge above ~20%
are the other two standard screens
([forensic red-flag toolkit](https://multibaggershares.com/forensic-accounting-red-flags-how-the-beneish-m-score-and-8-warning-signs-help-indian-investors-detect-earnings-manipulation-before-it-destroys-their-portfolio/)).

### Proposed design

Not a dimension component. A `governance_flags` list on the card, sourced from
`announcements_archive.csv` over a 180-day window:

* **auditor resignation** → hard flag, and a candidate for veto after it has
  been observed enough times to know its false-positive rate
* **qualified / adverse / modified audit opinion, emphasis of matter** → hard flag
* **pledge creation or invocation** → hard flag (complements the static
  `pledge_pct`, which only sees a level and never an *event*)
* **CFO / CEO / MD / statutory-auditor exit** → soft flag, shown with the date,
  never scored — the DEEP_DIVE analyst already correctly distinguished a routine
  superannuation from a governance event once, and a keyword cannot

The governance dimension's note changes from a permanent
"auditor/SEBI/related-party checks pending (Phase C)" — which has been false
comfort for a month — to either the flags found or "no adverse filing in 180
days", which is a **statement the archive can actually support**.

**Do not veto on this yet.** A veto that has never been observed firing is an
untested gate, and this codebase has fifteen rejected overlays teaching that
lesson. Ship it as a flag, count how often it fires and on what, and revisit.

---

## 4. Bank-specific financial strength — CORRECTED, the recommended metrics do not exist

### The data check that killed the original proposal

What a bank's screener.in page carries versus a manufacturer's:

| | manufacturer (HFCL) | bank (DCBBANK, KTKBANK) |
|---|---|---|
| quarterly rows | Sales, Operating Profit, **OPM %**, Net Profit, EPS | Revenue, Financing Profit, **Financing Margin %**, Net Profit, EPS |
| balance sheet | Equity Capital, Reserves, **Borrowings** | Equity Capital, Reserves — **no borrowings, no deposits, no advances** |
| top ratios | Market Cap, P/E, **Book Value**, ROCE, ROE | same |

**There is no NIM, no GNPA/NNPA, no CASA, no provision coverage, no capital
adequacy and no cost-to-income on the free page.** The audit recommended all of
those. They would need a paid feed or RBI/bank-disclosure scraping, which is a
different project.

29 of the 291 scored names are bank-shaped.

### What IS available, and what the research says matters

The literature on Indian banks is consistent that **NIM is a strong positive
determinant of valuation and NPAs a strong negative one**, and that **P/B and
ROE together explain much of relative stock performance**
([MDPI, asset quality and valuation in Indian
banks](https://www.mdpi.com/2227-9091/14/1/16),
[ICICI Direct on bank ratios](https://www.icicidirect.com/ilearn/stocks/articles/key-financial-ratios-to-access-banking-stocks)).

We cannot see NPAs. We can see three of the four:

* **Financing Margin %** — 13 quarters of it. This is the closest available
  proxy for NIM, and critically we have its *trend*, which is what the
  dimension is supposed to measure.
* **ROE** — from top ratios.
* **Book value compounding** — Reserves series, annual. A bank that grows book
  value per share consistently is doing the thing banks are supposed to do.
* **Equity Capital series** — dilution. Banks raise equity constantly and it is
  the single most under-appreciated drag on per-share returns.

### Proposed design

Replace the flat `0.5` for financials with a bank-shaped score:

```
margin_trend  0.35   Financing Margin % now vs 4 quarters ago, and its streak
roe_level     0.25   ROE, saturating around 15-18%
bv_compound   0.25   reserves CAGR over available years, per-share adjusted
dilution      0.15   equity capital growth — penalise heavy issuance
```

with the note stating the limitation out loud: *"bank read from margin trend,
ROE and book-value compounding; asset quality (GNPA, provisions, CASA) is not
published on the free source and is NOT in this score."* That sentence is the
important part — a bank score that silently omits asset quality is more
dangerous than a flat 0.5, because 0.5 at least *looks* like an abstention.

**Recommend building this fourth**, after 1–3. It affects 29 names and it
carries a real epistemic risk (a bank scoring well on margins while its loan
book rots is precisely how bank investors get hurt), so the honest note matters
as much as the arithmetic.

---

## 5. A pre-registered test of the `theme_tailwind` weight — DESIGN READY, UNDERPOWERED TODAY

### The question, stated so it can be answered

Weight 15 rides on theme_tailwind, and the closest tested analogue — matrix v2
config E, sector-heat gating — was rejected at +0.22R/+0.11R against an ungated
+1.27R baseline. But that test asked whether sector heat should **gate an
entry**. This dimension does not gate anything. So config E does not actually
answer it, and saying "15 points rest on a rejected idea" was rhetorically
strong and technically loose.

The score's only falsifiable claim is: **a higher conviction score should
correspond to better forward outcomes.** The journal already shows the composite
does this (bands monotonic, <50 → −0.06R, 70+ → +0.68R). So the test is a
leave-one-out on that relationship.

### Proposed test

Pre-register before running, per project discipline:

1. Take every alert in `journal/journal_outcomes.csv` with a forward R
   (**157 rows today**) joined to its frozen dimension scores.
2. For each dimension *d*, recompute the composite with *d*'s weight set to 0
   and the remainder renormalised — the same coverage-renormalisation `assess`
   already does, so no new maths.
3. Compare **Spearman rank correlation** between score and forward R, full model
   versus each leave-one-out.
4. **Decision rule, fixed in advance:** a dimension whose removal *improves*
   rank correlation by more than the bootstrap 90% CI is a candidate for weight
   reduction. A dimension whose removal changes nothing is decoration at its
   current weight. Neither result changes a weight automatically — it
   authorises a pre-registered weight matrix, nothing more.

Run it over **all eight dimensions at once**, not just theme_tailwind. Singling
out one dimension is how a post-hoc story gets confirmed.

### Why not today

The frozen-column record is the binding constraint. `entry_signals.csv` has 167
rows but only **33 carry a frozen `news_catalyst`** — the news dimensions only
started freezing on 2026-07-28. A leave-one-out on theme_tailwind and catalyst
would today be measuring 33 observations, and 0 of 199 outcome rows have hit a
stop, so the R distribution is still one-sided and immature.

**Recommend: build the harness now, run it when the frozen-news cohort reaches
~100 alerts** (roughly 2–3 months at the current rate). Writing the script early
is free and it forces the decision rule to be fixed before any number is
visible — which is the specific failure `PREREG_2026-07-29.md` disclosed about
itself.

---

## Recommended order

| | item | why this position | new data needed |
|---|---|---|---|
| 1 | **FII/DII split** | largest measured defect (52% of names), fully contained | none |
| 2 | **Sales acceleration** | closes the O'Neil/Minervini gap, data already cached | none |
| 3 | **Governance flags** | cheap, honest, replaces a month-old false "pending" | none |
| 4 | **Bank financial strength** | 29 names, and needs its limitation stated carefully | none |
| 5 | **Leave-one-out harness** | write now, run in 2–3 months | time, not data |

Items 1–4 are all buildable from data already on disk with no network calls.
Each should be measured before/after on the live shortlist the way the
persistence term was, and each should be shippable and revertible on its own.

## Sources

- [AAII — How to Use the CAN SLIM Approach to Screen for Growth Stocks](https://www.aaii.com/journal/article/how-to-use-the-can-slim-approach-to-screen-for-growth-stocks)
- [AAII — O'Neil's CAN SLIM Revised 3rd Edition Screen](https://www.aaii.com/stocks/screens/78)
- [QuantVPS — Mark Minervini's Step-by-Step Guide to Finding Winning Stocks](https://www.quantvps.com/blog/mark-minervinis-guide-to-finding-winning-stocks)
- [HDFC Mutual Fund — FII & DII: meaning and role in the Indian stock market](https://www.hdfcfund.com/learn/blog/what-fii-and-dii-meaning-full-forms-and-role-indian-stock-market)
- [MNCL — How FIIs drive momentum in Indian stocks](https://www.mnclgroup.com/how-fiis-drive-momentum-in-indian-stocks)
- [MDPI Risks — Asset Quality, Financial Ratios and Market Valuation in Indian Banks](https://www.mdpi.com/2227-9091/14/1/16)
- [ICICI Direct — Key financial ratios to assess banking stocks](https://www.icicidirect.com/ilearn/stocks/articles/key-financial-ratios-to-access-banking-stocks)
- [Business Standard — Investors backing off as auditors continue to resign](https://www.business-standard.com/article/pf/investors-backing-off-as-auditors-continue-to-resign-from-leading-firms-118060601254_1.html)
- [Multibagger Shares — Forensic accounting red flags and the Beneish M-Score](https://multibaggershares.com/forensic-accounting-red-flags-how-the-beneish-m-score-and-8-warning-signs-help-indian-investors-detect-earnings-manipulation-before-it-destroys-their-portfolio/)
