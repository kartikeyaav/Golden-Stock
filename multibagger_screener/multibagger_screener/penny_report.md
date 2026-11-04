# Penny / nano-cap screen — 2026-11-04 12:55

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 208 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 86 | 100% | CONFIRMED | 96 | Rs1.70 Cr | Rs608 Cr | Hyper-growth + Momentum | — |
| 2 | **AVTNPL** | PRICE | 80 | 100% | CONFIRMED | 95 | Rs4.15 Cr | Rs1342 Cr | Hyper-growth + Momentum | — |
| 3 | **PARACABLES** | PRICE | 75 | 100% | CONFIRMED | 96 | Rs12.13 Cr | Rs2011 Cr | Momentum | 1 |
| 4 | **ARFIN** | PRICE | 74 | 100% | CONFIRMED | 91 | Rs19.67 Cr | Rs1541 Cr | Momentum | — |
| 5 | **KESORAMIND** | PRICE+MCAP | 74 | 100% | CONFIRMED | 99 | Rs1.09 Cr | Rs374 Cr | Deleveraging + Momentum | — |
| 6 | **EMKAY** | MCAP | 72 | 100% | WATCH | 74 | Rs1.49 Cr | Rs702 Cr | Hyper-growth | — |
| 7 | **PONNIERODE** | MCAP | 72 | 100% | WATCH | 83 | Rs1.60 Cr | Rs275 Cr | Hyper-growth | — |
| 8 | **UNITEDPOLY** | PRICE | 71 | 100% | CONFIRMED | 95 | Rs2.62 Cr | Rs1246 Cr | Momentum | — |
| 9 | **MAZDA** | MCAP | 71 | 100% | CONFIRMED | 89 | Rs1.20 Cr | Rs559 Cr | Deleveraging + Momentum | — |
| 10 | **ANDHRSUGAR** | PRICE | 71 | 100% | ANTICIPATION | 63 | Rs2.74 Cr | Rs1106 Cr | Deleveraging | — |
| 11 | **CONFIPET** | PRICE | 70 | 100% | BROKEN | 90 | Rs13.88 Cr | Rs1979 Cr | Hyper-growth | — |
| 12 | **EMAMIPAP** | MCAP | 70 | 100% | CONFIRMED | 93 | Rs0.67 Cr | Rs709 Cr | Momentum | — |
| 13 | **PNBGILTS** | PRICE | 68 | 100% | WATCH | 76 | Rs4.05 Cr | Rs1351 Cr | Turnaround (margin-confirmed) | — |
| 14 | **MANBA** | MCAP | 68 | 100% | CONFIRMED | 86 | Rs1.37 Cr | Rs730 Cr | Hyper-growth + Momentum | — |
| 15 | **KAMDHENU** | PRICE+MCAP | 68 | 100% | WATCH | 97 | Rs3.20 Cr | Rs998 Cr | Hyper-growth | — |
| 16 | **MANALIPETC** | PRICE | 68 | 100% | WATCH | 85 | Rs8.99 Cr | Rs1176 Cr | — | — |
| 17 | **SYNCOMF** | PRICE | 67 | 100% | WATCH | 94 | Rs31.40 Cr | Rs1914 Cr | Deleveraging | — |
| 18 | **SEJALLTD** | MCAP | 67 | 100% | WATCH | 64 | Rs3.00 Cr | Rs882 Cr | Hyper-growth | 1 |
| 19 | **DBOL** | MCAP | 67 | 100% | CONFIRMED | 91 | Rs2.84 Cr | Rs779 Cr | Turnaround (unconfirmed) + Momentum | — |
| 20 | **DMCC** | MCAP | 67 | 100% | WATCH | 46 | Rs4.71 Cr | Rs721 Cr | Hyper-growth | — |

## Vetoed (62) — capped at 25, momentum cannot outvote these

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
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 109% in 3 years — serial issuance di |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| PATELENG | promoter pledge 66.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| OMAXE | negative net worth (Rs-901 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 53.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| MCLOUD | promoter pledge 59.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MTNL | negative net worth (Rs-29960 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| PATELRMART | share capital up 725% in 3 years — serial issuance dilutes every rupee of future earnings |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
