# Penny / nano-cap screen — 2026-11-16 13:47

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 194 names that survived the hard tradability gates
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
| 1 | **KESORAMIND** | PRICE+MCAP | 80 | 100% | CONFIRMED | 100 | Rs1.30 Cr | Rs446 Cr | Turnaround (margin-confirmed) + Deleveraging + Momentum | — |
| 2 | **AMANTA** | MCAP | 78 | 100% | CONFIRMED | 99 | Rs2.28 Cr | Rs758 Cr | Momentum | — |
| 3 | **DBOL** | MCAP | 77 | 100% | CONFIRMED | 96 | Rs2.82 Cr | Rs936 Cr | Turnaround (margin-confirmed) + Deleveraging + Momentum | — |
| 4 | **AVTNPL** | PRICE | 76 | 100% | CONFIRMED | 92 | Rs4.15 Cr | Rs1518 Cr | Hyper-growth + Momentum | — |
| 5 | **PARACABLES** | PRICE | 74 | 100% | CONFIRMED | 88 | Rs17.28 Cr | Rs2183 Cr | Momentum | 1 |
| 6 | **MAGADSUGAR** | MCAP | 74 | 90% | CONFIRMED | 78 | Rs1.73 Cr | — | Turnaround (margin-confirmed) + Deleveraging + Momentum | — |
| 7 | **MODIS** | MCAP | 74 | 100% | YOUNG | — | Rs2.23 Cr | Rs903 Cr | Hyper-growth | — |
| 8 | **ORIENTBELL** | MCAP | 73 | 100% | CONFIRMED | 86 | Rs0.76 Cr | Rs584 Cr | Deleveraging + Momentum | — |
| 9 | **MAZDA** | MCAP | 73 | 90% | WATCH | 85 | Rs1.09 Cr | — | — | — |
| 10 | **MANALIPETC** | PRICE | 72 | 100% | WATCH | 85 | Rs7.34 Cr | Rs1300 Cr | Hyper-growth | — |
| 11 | **ARFIN** | PRICE | 72 | 100% | CONFIRMED | 88 | Rs15.46 Cr | Rs1589 Cr | Hyper-growth + Momentum | — |
| 12 | **SEJALLTD** | MCAP | 71 | 100% | CONFIRMED | 73 | Rs3.87 Cr | Rs989 Cr | Hyper-growth + Momentum | 1 |
| 13 | **SYNCOMF** | PRICE | 71 | 100% | CONFIRMED | 94 | Rs16.29 Cr | Rs1905 Cr | Deleveraging + Momentum | — |
| 14 | **CONFIPET** | PRICE | 71 | 100% | BROKEN | 88 | Rs13.33 Cr | Rs2205 Cr | Hyper-growth | — |
| 15 | **EMKAY** | MCAP | 70 | 100% | WATCH | 76 | Rs1.20 Cr | Rs712 Cr | Hyper-growth | — |
| 16 | **PNBGILTS** | PRICE | 69 | 90% | ANTICIPATION | 58 | Rs3.94 Cr | — | Turnaround (margin-confirmed) | — |
| 17 | **PASUPTAC** | PRICE+MCAP | 69 | 90% | CONFIRMED | 90 | Rs1.76 Cr | — | Momentum | — |
| 18 | **UNITEDPOLY** | PRICE | 69 | 100% | CONFIRMED | 94 | Rs1.71 Cr | Rs1222 Cr | Momentum | — |
| 19 | **KAMDHENU** | PRICE | 69 | 100% | WATCH | 92 | Rs2.80 Cr | Rs1029 Cr | Hyper-growth | — |
| 20 | **ARIHANTCAP** | PRICE | 68 | 100% | CONFIRMED | 83 | Rs3.44 Cr | Rs1012 Cr | Momentum | — |

## Vetoed (52) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 41.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 93% in 3 years — serial issuance di |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 39.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 64% in 3 years — serial issuance dilutes every rupee of future earnings |
| DBREALTY | promoter pledge 32.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 125% in 3 years — serial issuance di |
| UTKARSHBNK | share capital up 62% in 3 years — serial issuance dilutes every rupee of future earnings |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 66.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| MTNL | negative net worth (Rs-31602 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| GKENERGY | share capital up 4000% in 3 years — serial issuance dilutes every rupee of future earnings |
| OMAXE | negative net worth (Rs-925 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| MCLOUD | promoter pledge 59.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 53.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 251% in 3 years — serial issuance di |
| SHALPAINTS | promoter pledge 70.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| UGROCAP | promoter holding only 2.88% and institutions hold just 9.1% — nobody with size is accountable for this company; share capital up 66% in 3 years — seri |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
