# Gate reference curve — audit

Source: `SZ2_B_equity_cap15_r1.25, 91 entries replayed through backtest/engine.py with next-open fills, gap-aware stops, equity sizing and costs; measured 2026-07-27, frozen at cohort n=0`

| age | frozen in config | recomputed now | drift | n |
|---|---|---|---|---|
| 30d | +0.533 | +0.533 | -0.000 | 91 |
| 60d | +0.679 | +0.679 | -0.000 | 91 |
| 90d | +0.724 | +0.724 | +0.000 | 91 |
| 180d | +0.961 | +0.961 | -0.000 | 91 |
| 365d | +1.492 | +1.492 | -0.000 | 91 |
| full | — | +1.811 | — | 91 |

Frozen curve reproduces — gate reference is sound.

## Power: how often does the gate pass a system that IS working?

| age at judgment | pool mean R | bar | P(all conditions pass) at n=40 |
|---|---|---|---|
| 30d | +0.533 | +0.267 | 83% |
| 60d | +0.679 | +0.340 | 80% |
| 90d | +0.724 | +0.362 | 77% |
| 180d | +0.961 | +0.480 | 81% |
| 365d | +1.492 | +0.746 | 71% |
| full | +1.811 | +0.746 | 61% |
