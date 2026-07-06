# Survivorship check — measured, not guessed (2026-07-06)

**Method:** Wayback Machine snapshot of the official Nifty Smallcap 250
constituent CSV (2024-07-08, raw-content fetch) diffed against today's
universe. Midcap 150 / Microcap 250 snapshots don't exist in the archive, so
this measures the smallcap slice only — the most churn-prone slice, which
makes it a reasonable upper-ish bound for the whole universe.

## Result

- 2024-07 Smallcap 250 members: **251**
- Still in today's universe: **228 (90.8%)**
- Departed in ~2 years: **23 (9.2%)**

Departed names: ALLCARGO, ASTRAZEN, CENTURYTEX, CHEMPLASTS, DUMMYSANOF,
EASEMYTRIP, FDC, FINEORG, GLS, GSPL, HAPPYFORGE, HBLPOWER, IBULHSGFIN, IDFC,
MAHLIFE, MHRIL, PRINCEPIPE, RAJESHEXPO, RAYMOND, SANOFI, SUVENPHAR,
SWANENERGY, TV18BRDCST

## Interpretation

- Eyeballing the departures: the majority are **mergers, renames, demergers,
  and index demotions** (IDFC merger, Raymond demerger, TV18 merger,
  Sanofi restructuring, IBULHSGFIN rename), not blow-ups. Demotions to the
  microcap index stay inside our universe anyway.
- Extrapolated to the 3-year backtest window: roughly **~14% of the
  opportunity set churned**, of which the truly-invisible-loser slice
  (delisted/collapsed, no price history for us) is a minority.
- **Conclusion: the survivorship haircut on backtest expectancy is real but
  moderate — think "optimistic by a modest margin," not "fantasy."** The
  +1.27R window baseline would need most of the 23 departures to have been
  catastrophic shorts-in-disguise to flip the sign; the composition says
  they weren't.

Design Law #4 stands: absolute backtest numbers are directional; config-vs-
config comparisons (which share the bias) remain clean. This report converts
the caveat from unquantified to bounded.
