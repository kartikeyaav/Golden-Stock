# P6 trailing speed + P5b slot count — pre-registered 2026-07-27

Reading rules are fixed in `PREREG_2026-07-27.md`, committed before
this ran. Entries identical in every cell (evidence lock).
Window-corrected CAGR (active window from 2023-08). Survivor bias
applies to all cells equally — compare cells, not the outside world.

## P6 — trading-lot trailing MA

| config | trail | pos | exp/R | trading lot | core lot | CAGR(w) | maxDD | MAR | P2 R |
|---|---|---|---|---|---|---|---|---|---|
| P6_trail50_control | 50 | 96 | 1.681 | 0.538 | 2.874 | 47.2% | -18.46% | 2.56 | 0.342 |
| P6_trail30 | 30 | 100 | 1.627 | 0.548 | 2.717 | 48.0% | -18.55% | 2.59 | 0.28 |
| P6_trail20 | 20 | 108 | 1.342 | 0.358 | 2.346 | 47.8% | -18.34% | 2.61 | 0.345 |
| P6_trail10 | 10 | 106 | 1.357 | 0.309 | 2.436 | 48.5% | -17.46% | 2.78 | 0.356 |

### VERDICT: REJECTED

The registered bar was **blended expectancy ≥ +0.10R better than control**. Every
faster cell is **worse**: −0.05R (30), −0.34R (20), −0.32R (10). The trading lot
alone — the only lot the rule touches — degrades from 0.538R to 0.309R. There is
nothing here to adopt.

**Control reproduces**: 96 positions and +1.681R vs the canonical `SZ2_B`
+1.667R, inside the ±0.05R tolerance.

*(Correction to the pre-registration: `PREREG_2026-07-27.md` quoted the control
target as "+1.612R". That was the wrong statistic — it came from an equal-weighted
per-entry probe, not the canonical lot-level figure the matrix reports. The
control is checked against the published +1.667R. Recorded rather than silently
amended.)*

### The isolation clause was mis-specified — my error, not a finding

The pre-registration said the run is void if the core lot's R moves. It moved
(2.874 → 2.717 → 2.346 → 2.436), so by the letter of the rule this is void.
That clause was impossible to satisfy and should never have been written that way:
in a **portfolio** backtest, changing any exit alters slot timing, which alters
which later positions are opened at all (96 → 108 here), which changes the *set*
of core lots. Composition moves even when the rule governing the core lot never does.

The mechanism the clause was meant to protect was tested directly instead, with a
single-position replay that has no slot contention and therefore no composition
effect:

| symbol | trail 50 | trail 30 | trail 20 | trail 10 |
|---|---|---|---|---|
| TARIL core R | 113.782 | 113.782 | 113.782 | 113.782 |
| NEULANDLAB core R | 3.079 | 3.079 | 3.079 | 3.079 |
| TARIL trading R | 2.854 | 2.854 | 2.214 | 2.346 |
| NEULANDLAB trading R | 5.518 | 4.135 | 4.099 | 4.386 |

**`trail_ma` does not reach the core lot.** The isolation is sound; the clause was
not. The rejection above stands on the primary criterion regardless.

### Observed but NOT adopted

MAR rises monotonically as the trail speeds up (2.56 → 2.59 → 2.61 → 2.78) and
trail-10 has the lowest drawdown (−17.5% vs −18.5%). Faster trails recycle capital
sooner (96 → 106 positions) and give up per-trade edge to do it.

This is **not** the registered criterion and does not authorize anything. Re-reading
the result to make MAR the winner is precisely the post-hoc threshold selection
`CAPITAL_GATE.md` §8 forbids, and the same argument was available for several of
the 13 previously rejected overlays and was not accepted for them either. The gaps
are also ~1pp on one survivor-biased window, and confounded by the composition
change above. If it is ever pursued it needs its own pre-registration naming MAR as
the primary metric in advance, plus a walk-forward split.

---

## P5b — slot count, equity-basis sizing

| config | slots | pos | exp/R | trading lot | core lot | CAGR(w) | maxDD | MAR | P2 R |
|---|---|---|---|---|---|---|---|---|---|
| P5b_slots12_control | 12 | 96 | 1.681 | 0.538 | 2.874 | 47.2% | -18.46% | 2.56 | 0.342 |
| P5b_slots08 | 8 | 74 | 1.98 | 0.622 | 3.337 | 46.2% | -18.44% | 2.51 | 0.43 |
| P5b_slots16 | 16 | 116 | 1.564 | 0.51 | 2.729 | 46.1% | -18.46% | 2.5 | 0.304 |
| P5b_slots20 | 20 | 127 | 1.661 | 0.543 | 2.895 | 45.8% | -18.47% | 2.48 | 0.307 |

### VERDICT: REJECTED — 12 slots stands, and it is a genuine local optimum

The registered bar was **MAR strictly better by ≥ 0.15**. MAR *falls* in every
direction: 2.51 (8 slots), 2.50 (16), 2.48 (20), against the control's 2.56.
Twelve is not an inherited default that survived by neglect — it is a peak, and
the run tested both sides of it.

### But the OLD rejection's stated mechanism was a cash-sizing artifact

This is why the re-test was worth running even though the conclusion is unchanged.
The 2026-07-11 matrix reported a clean **monotonic** expectancy collapse and read
it as "extra slots admit progressively weaker breakouts":

| slots | expectancy, CASH basis (2026-07-11) | expectancy, EQUITY basis (today) |
|---|---|---|
| 12 | 1.294 | 1.681 |
| 16 | 1.145 | 1.564 |
| 20 | 0.892 | **1.661** |

**The monotonicity does not reproduce.** Under correct sizing, 20 slots recovers
to ~the control's expectancy; the marginal breakouts admitted at 16–20 are not
progressively worse in the way the old report concluded. Dose-response was the
evidence that made that rejection credible, and it was an artifact of measuring
size off remaining cash.

The conclusion survives on a different and cleaner mechanism: **CAGR falls
monotonically with more slots (47.2 → 46.1 → 45.8) while drawdown stays flat.**
More positions spread the same equity thinner without buying any risk reduction.

### The most useful thing in this table is the drawdown column

maxDD is essentially **constant** at −18.44% to −18.47% across 74, 96, 116 and 127
positions. Position count buys **no** drawdown protection here. These are Indian
small/mid-cap momentum names; in a selloff they move together, so "diversify by
holding more names" does not work in this strategy and should not be assumed as a
risk lever in future work. Drawdown control has to come from exposure (the adopted
breadth-regime halving), not from breadth of holdings.

Fewer slots (8) is the mirror image and equally instructive: expectancy jumps to
+1.98R and P2 chop-cohort R to +0.43R — concentration genuinely picks better
trades — but CAGR still falls to 46.2% because capital sits idle. The system is
capacity-limited by its signal rate, exactly as the 2026-07-11 read concluded.

