# Sizing matrix v2 — sizing basis + value cap (pre-registered 2026-07-12)

Entries identical in every cell (evidence lock). Window-corrected
CAGR (active window from 2023-08). Survivor-bias caveat applies to
all cells equally; next-open-fill stress kept ~75% of edge — apply
that haircut mentally.

| config | pos | exp/R | CAGR(w) | maxDD | MAR | P2 R |
|---|---|---|---|---|---|---|
| A_cash_cap15_r1.25 | 109 | 1.294 | 22.5% | -12.88% | 1.75 | 0.218 |
| B_equity_cap15_r1.25 | 96 | 1.667 | 47.4% | -18.46% | 2.57 | 0.312 |
| C_equity_cap20_r1.25 | 102 | 1.513 | 47.0% | -18.15% | 2.59 | 0.245 |
| D_equity_cap25_r1.25 | 100 | 1.569 | 44.5% | -18.39% | 2.42 | 0.206 |
| E_equity_cap20_r1.75 | 96 | 1.485 | 50.0% | -21.04% | 2.38 | -0.026 |
| F_equity_cap25_r1.75 | 90 | 1.86 | 58.0% | -22.16% | 2.62 | 0.319 |
| G_equity_cap20_r2.50 | 96 | 1.451 | 53.8% | -22.67% | 2.37 | -0.069 |

## Reading rules (pre-registered)
- A must reproduce ~21.5% window CAGR / -12.9% DD / +1.29R.
- B vs A isolates the sizing-basis effect alone.
- Adopt only if MAR does not degrade AND maxDD stays inside -20%
  (5pp buffer to the -25% circuit breaker) AND P2 expectancy is
  not materially worse.
- Expectancy/R may shift slightly (bigger fills exhaust cash and
  can skip late same-day candidates) — judge economics via CAGR,
  DD, MAR, and end equity together, not expectancy alone.
## VERDICT (recorded 2026-07-12, after the run + deployment stress)

ADOPTED: equity-basis sizing (config B) as the canonical baseline read.

- B vs A isolates the fix: same rules, sizing measured off marked-to-market
  equity instead of leftover cash -> window CAGR 22.5% -> 47.4%, maxDD
  -12.9% -> -18.5%, MAR 1.75 -> 2.57, P2 cohort IMPROVED (+0.218 -> +0.312R).
  Cash-basis was an implementation artifact that undersized every late entry
  (~0.3% real risk); the LIVE system already sizes off configured capital,
  so the backtest was underreporting the live rules, not vice versa.
- Value-cap relaxation adds nothing at 1.25% risk (C/D vs B) — cap stays 15%.
- Higher risk% REJECTED again: E/G turn the P2 chop cohort negative and
  breach the -20% DD bound; F breaches DD too. Risk stays 1.25%.
- DEPLOYMENT STRESS on B (next-open fills + gap-aware stops + costs):
  CAGR 32.5%, maxDD -20.7%, MAR 1.57, exp +1.10R, P2 +0.312R. This is the
  honest planning number; the -25% circuit breaker has ~4pp margin under
  stress — regime half-sizing (already live) is the mitigant.
- Caveats unchanged: survivor-biased universe (directional), single ~2.9y
  window with a strong 2023-24 cohort, and position sizes that compound with
  equity will eventually meet microcap liquidity limits (fine at current
  capital; revisit past ~1 Cr).
- LIVE ACTION REQUIRED: none in code (live plans already size off
  RISK.capital). For true fixed-fractional behavior the user should update
  RISK.capital to actual account equity periodically (monthly is enough).