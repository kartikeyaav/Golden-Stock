# EP matrix — episodic-pivot entry class (pre-registered 2026-07-19)

Stop = EP-day low (floor 0.75*ATR); two-lot management identical
to baseline; equity basis / cap 15 / risk 1.25 / NIFTY regime.

| config | pos | exp/R | core/R | win% | CAGR(w) | maxDD | MAR | P2 R |
|---|---|---|---|---|---|---|---|---|
| EP_A_gap8_vol3 | 83 | 1.377 | 1.888 | 36.97 | 38.2% | -20.92% | 1.83 | 0.76 |
| EP_B_neglect | 53 | 1.169 | 1.458 | 38.1 | 17.0% | -9.97% | 1.71 | 0.711 |
| EP_C_gap10_vol4 | 43 | 1.868 | 2.627 | 38.37 | 24.8% | -18.57% | 1.34 | 1.033 |
| BASE_vcp_only | 96 | 1.653 | 2.821 | 31.22 | 47.7% | -17.64% | 2.7 | 0.312 |
| COMBINED_vcp_plus_epA | 142 | 1.337 | 2.203 | 31.27 | 54.5% | -15.22% | 3.58 | 0.527 |

## Adoption rule (pre-registered)
- Standalone validates: >=30 pos, exp >= +0.5R, P2 >= 0, DD < 25%.
- Capital-bearing only if COMBINED > BASE on MAR, DD not >1pp worse.
- Standalone-valid + COMBINED-neutral -> alert-only tier (V3a logic).