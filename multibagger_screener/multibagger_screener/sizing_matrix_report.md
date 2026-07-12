# Sizing matrix — pre-registered 2026-07-10

Same signals/window/costs as A_baseline; ONLY risk%% and the
position cap vary. Entries untouched (evidence lock).

| config | positions | exp/R | CAGR%% | maxDD%% | MAR | P1 R | P2 R |
|---|---|---|---|---|---|---|---|
| risk1.25_slots12 | 109 | 1.294 | 8.26 | -12.88 | 0.64 | 2.313 | 0.218 |
| risk1.25_slots16 | 132 | 1.145 | 7.99 | -12.55 | 0.64 | 1.837 | 0.234 |
| risk1.25_slots20 | 160 | 0.892 | 7.76 | -12.63 | 0.61 | 1.308 | 0.198 |
| risk1.75_slots12 | 109 | 1.295 | 8.95 | -13.07 | 0.68 | 2.315 | 0.218 |
| risk1.75_slots16 | 132 | 1.145 | 8.63 | -12.86 | 0.67 | 1.837 | 0.234 |
| risk1.75_slots20 | 160 | 0.892 | 8.4 | -12.94 | 0.65 | 1.308 | 0.199 |
| risk2.5_slots12 | 109 | 1.295 | 8.98 | -13.07 | 0.69 | 2.314 | 0.218 |
| risk2.5_slots16 | 132 | 1.145 | 8.68 | -12.85 | 0.68 | 1.837 | 0.234 |
| risk2.5_slots20 | 160 | 0.892 | 8.44 | -12.93 | 0.65 | 1.308 | 0.198 |

## Reading rules (pre-registered)
- Baseline cell is risk1.25_slots12; it must reproduce ~A_baseline.
- Adopt a cell only if it does NOT reduce MAR (CAGR/|maxDD|) and
  keeps maxDD inside the -25% circuit breaker with margin.
- Expectancy/R should be ~flat across cells (sizing must not
  change per-trade edge much; big drops = crowding-out effects).
- P2 (chop cohort) must not get materially worse.
- Survivor bias applies equally to all cells; compare cells,
  don't trust absolutes. Next-open-fill stress kept ~75% of edge;
  apply that haircut mentally to every CAGR here.
## Window-corrected CAGR + VERDICT (recorded 2026-07-11)

Equity clock includes ~4.3 idle pre-window years; corrected via the canonical
anchor (diluted 8.26% = corrected 21.5%). DD and expectancy unaffected.

| config | exp/R | CAGR corrected | maxDD | MAR |
|---|---|---|---|---|
| risk1.25_slots12 | 1.294 | 21.5% | -12.88% | 1.67 |
| risk1.25_slots16 | 1.145 | 20.8% | -12.55% | 1.65 |
| risk1.25_slots20 | 0.892 | 20.1% | -12.63% | 1.59 |
| risk1.75_slots12 | 1.295 | 23.4% | -13.07% | 1.79 |
| risk1.75_slots16 | 1.145 | 22.5% | -12.86% | 1.75 |
| risk1.75_slots20 | 0.892 | 21.9% | -12.94% | 1.69 |
| risk2.5_slots12 | 1.295 | 23.5% | -13.07% | 1.80 |
| risk2.5_slots16 | 1.145 | 22.7% | -12.85% | 1.76 |
| risk2.5_slots20 | 0.892 | 22.0% | -12.93% | 1.70 |

### Verdict (per the pre-registered reading rules)
1. SLOT EXPANSION REJECTED: monotonic expectancy decline 1.29R -> 1.15R (16)
   -> 0.89R (20) and LOWER corrected CAGR. The volume-ranked entry queue
   already takes the strongest same-day breakouts; extra slots admit only
   weaker ones. Same dose-response failure shape as every rejected gate.
2. RISK%% SATURATES AT THE VALUE CAP: identical trades at 12 slots; 1.75%%
   risk lifts corrected CAGR 21.5 -> ~23.4%% (+0.2pp DD, MAR 1.67 -> 1.79);
   2.5%% adds nothing further (15%% position-value cap truncates sizing).
   The +2pp is within survivor-bias noise -> treated as a USER CHOICE, not
   an adoption: each losing trade would cost 1.75%% of capital instead of
   1.25%% (7 of 10 trades lose). DEFAULT UNCHANGED at 1.25%%; revisit after
   the forward journal matures.
3. Untested residual lever: the 15%% position-value cap itself. Relaxing it
   concentrates single-name gap risk (the cap exists to stop tight-stop
   monster positions) - would need its own pre-registered run.
4. CONCLUSION for the "21%% feels low" question: both obvious throttles are
   now tested. More slots = worse. More risk = +2pp then saturation. The
   system is capacity-limited BY ITS OWN DISCIPLINE; the remaining paths to
   more absolute return are more capital or accepting more drawdown.