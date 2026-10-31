# Penny / nano-cap screen — 2026-10-31 11:17

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 216 names that survived the hard tradability gates
(EQ series only · no GSM/ASM · band >= 10% · liquidity + circuit floors ·
listed >= 1 year). Rejects and their reasons: `penny_excluded.csv`.

Suggested exposure discipline: <= 5% of the book in
this class in total, <= 1% in any one name.

The **arm** column matters: PRICE means only that the share costs under
Rs100 — a Rs40 share of a Rs9,000 Cr bank is not a small company. MCAP is
the one that means genuinely small. Read the MCAP rows first.

## Top 20

| # | Symbol | Arm | Score | Cov | Stage | RS | Turnover | Cap | Archetype | Risk flags |
|--:|--------|-----|------:|----:|-------|---:|---------:|----:|-----------|-----------|
| 1 | **PASUPTAC** | PRICE+MCAP | 82 | 100% | WATCH | 95 | Rs1.70 Cr | Rs608 Cr | Hyper-growth | — |
| 2 | **AVTNPL** | PRICE | 75 | 100% | WATCH | 93 | Rs3.93 Cr | Rs1342 Cr | Hyper-growth | — |
| 3 | **PARACABLES** | PRICE | 74 | 100% | CONFIRMED | 96 | Rs11.08 Cr | Rs2011 Cr | Momentum | 1 |
| 4 | **KESORAMIND** | PRICE+MCAP | 73 | 100% | CONFIRMED | 99 | Rs1.08 Cr | Rs374 Cr | Deleveraging + Momentum | — |
| 5 | **EMKAY** | MCAP | 72 | 100% | WATCH | 73 | Rs1.49 Cr | Rs702 Cr | Hyper-growth | — |
| 6 | **DMCC** | MCAP | 71 | 100% | WATCH | 59 | Rs4.71 Cr | Rs721 Cr | Hyper-growth | — |
| 7 | **CONFIPET** | PRICE | 71 | 100% | WATCH | 89 | Rs13.82 Cr | Rs1979 Cr | Hyper-growth | — |
| 8 | **UNITEDPOLY** | PRICE | 70 | 100% | CONFIRMED | 97 | Rs3.42 Cr | Rs1246 Cr | Momentum | — |
| 9 | **PONNIERODE** | MCAP | 70 | 100% | WATCH | 84 | Rs1.78 Cr | Rs275 Cr | Hyper-growth | — |
| 10 | **EMAMIPAP** | MCAP | 70 | 100% | CONFIRMED | 94 | Rs0.51 Cr | Rs709 Cr | Momentum | — |
| 11 | **MAZDA** | MCAP | 70 | 100% | CONFIRMED | 88 | Rs0.98 Cr | Rs559 Cr | Deleveraging + Momentum | — |
| 12 | **MANBA** | MCAP | 69 | 100% | CONFIRMED | 91 | Rs1.52 Cr | Rs730 Cr | Hyper-growth + Momentum | — |
| 13 | **IVP** | MCAP | 68 | 100% | WATCH | 91 | Rs0.52 Cr | Rs187 Cr | Deleveraging | — |
| 14 | **SYNCOMF** | PRICE | 67 | 100% | WATCH | 93 | Rs32.18 Cr | Rs1914 Cr | Deleveraging | — |
| 15 | **ARFIN** | PRICE | 67 | 100% | BROKEN | 92 | Rs15.85 Cr | Rs1541 Cr | — | — |
| 16 | **MANALIPETC** | PRICE | 67 | 100% | WATCH | 87 | Rs9.35 Cr | Rs1176 Cr | — | — |
| 17 | **ANDHRSUGAR** | PRICE | 67 | 100% | WATCH | 58 | Rs2.77 Cr | Rs1106 Cr | Deleveraging | — |
| 18 | **VETO** | MCAP | 67 | 100% | WATCH | 81 | Rs0.63 Cr | Rs248 Cr | Hyper-growth + Deleveraging | — |
| 19 | **KAMDHENU** | PRICE+MCAP | 66 | 100% | WATCH | 95 | Rs3.01 Cr | Rs998 Cr | Hyper-growth | — |
| 20 | **GLOBAL** | MCAP | 66 | 100% | CONFIRMED | 100 | Rs1.34 Cr | Rs732 Cr | Hyper-growth + Momentum | — |

## Vetoed (60) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 41.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DBREALTY | promoter pledge 32.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 54% in 3 years — serial issuance dil |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 109% in 3 years — serial issuance di |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| PATELENG | promoter pledge 66.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| OMAXE | negative net worth (Rs-901 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 59.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 53.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MTNL | negative net worth (Rs-29960 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| PATELRMART | share capital up 725% in 3 years — serial issuance dilutes every rupee of future earnings |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
