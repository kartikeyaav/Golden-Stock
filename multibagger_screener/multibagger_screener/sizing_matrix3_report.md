# Sizing matrix v3 — breadth + progressive-exposure overlays (pre-registered 2026-07-19)

Entries identical in every cell (sizing only — evidence lock
untouched). Equity basis / cap 15 / risk 1.25 everywhere.
Incumbent = B_live_nifty150 (the adopted V3b rule).

| config | pos | exp/R | CAGR(w) | maxDD | MAR | P2 R |
|---|---|---|---|---|---|---|
| A_SZ2B_repro | 96 | 1.667 | 47.0% | -18.46% | 2.55 | 0.311 |
| B_live_nifty150 | 96 | 1.653 | 47.7% | -17.64% | 2.7 | 0.312 |
| C_breadth_graded | 100 | 1.557 | 46.2% | -14.76% | 3.13 | 0.214 |
| D_breadth_binary | 100 | 1.575 | 49.5% | -14.79% | 3.35 | 0.235 |
| E_breadth_and_nifty | 101 | 1.556 | 46.6% | -14.74% | 3.16 | 0.239 |
| F_pe_trades | 108 | 1.234 | 44.0% | -14.71% | 2.99 | 0.221 |
| G_pe_equity | 101 | 1.551 | 43.9% | -14.27% | 3.08 | 0.201 |
| H_combo | 112 | 1.175 | 42.0% | -14.32% | 2.93 | 0.174 |

## Adoption rule (pre-registered)
- vs B: MAR >= incumbent AND maxDD not >1pp worse AND CAGR not
  >1pp lower AND P2 expectancy not worse than -0.05R.
- Ties -> simplest rule. A must reproduce SZ2 B within noise.