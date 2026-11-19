# Penny / nano-cap screen — 2026-11-19 14:16

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 183 names that survived the hard tradability gates
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
| 1 | **KESORAMIND** | PRICE+MCAP | 80 | 100% | CONFIRMED | 98 | Rs1.75 Cr | Rs446 Cr | Turnaround (margin-confirmed) + Deleveraging + Momentum | — |
| 2 | **DBOL** | MCAP | 77 | 100% | CONFIRMED | 96 | Rs2.82 Cr | Rs936 Cr | Turnaround (margin-confirmed) + Deleveraging + Momentum | — |
| 3 | **AMANTA** | MCAP | 76 | 100% | EXTENDED | 99 | Rs2.67 Cr | Rs758 Cr | — | — |
| 4 | **MODIS** | MCAP | 74 | 100% | YOUNG | — | Rs2.07 Cr | Rs903 Cr | Hyper-growth | — |
| 5 | **KAMDHENU** | PRICE | 74 | 100% | CONFIRMED | 94 | Rs3.14 Cr | Rs1029 Cr | Hyper-growth + Momentum | — |
| 6 | **MANALIPETC** | PRICE | 72 | 100% | WATCH | 85 | Rs6.76 Cr | Rs1300 Cr | Hyper-growth | — |
| 7 | **CONFIPET** | PRICE | 72 | 100% | BROKEN | 91 | Rs14.03 Cr | Rs2205 Cr | Hyper-growth | — |
| 8 | **MOLDTECH** | PRICE+MCAP | 72 | 100% | WATCH | 86 | Rs1.31 Cr | Rs512 Cr | Hyper-growth + Deleveraging | — |
| 9 | **SYNCOMF** | PRICE | 72 | 100% | CONFIRMED | 94 | Rs16.29 Cr | Rs1905 Cr | Deleveraging + Momentum | — |
| 10 | **SEJALLTD** | MCAP | 72 | 100% | CONFIRMED | 80 | Rs4.31 Cr | Rs989 Cr | Hyper-growth + Momentum | 1 |
| 11 | **BALAJITELE** | PRICE | 70 | 100% | ANTICIPATION | 67 | Rs0.97 Cr | Rs1149 Cr | Turnaround (margin-confirmed) + Hyper-growth + Deleveraging | — |
| 12 | **TIRUPATIFL** | PRICE | 69 | 90% | CONFIRMED | 99 | Rs4.09 Cr | — | Momentum | — |
| 13 | **ORIENTBELL** | MCAP | 69 | 100% | WATCH | 84 | Rs0.76 Cr | Rs584 Cr | Deleveraging | — |
| 14 | **UNITEDPOLY** | PRICE | 69 | 100% | CONFIRMED | 93 | Rs1.52 Cr | Rs1222 Cr | Momentum | — |
| 15 | **EMKAY** | MCAP | 69 | 100% | WATCH | 71 | Rs1.16 Cr | Rs712 Cr | Hyper-growth | — |
| 16 | **ARIHANTCAP** | PRICE | 68 | 100% | CONFIRMED | 82 | Rs3.33 Cr | Rs1012 Cr | Momentum | — |
| 17 | **PNBGILTS** | PRICE | 68 | 90% | BROKEN | 72 | Rs3.94 Cr | — | Turnaround (margin-confirmed) | — |
| 18 | **ARFIN** | PRICE | 67 | 100% | WATCH | 86 | Rs14.30 Cr | Rs1589 Cr | Hyper-growth | — |
| 19 | **ATL** | PRICE+MCAP | 67 | 100% | CONFIRMED | 68 | Rs0.51 Cr | Rs774 Cr | Momentum | — |
| 20 | **PARACABLES** | PRICE | 66 | 100% | BROKEN | 87 | Rs19.61 Cr | Rs2183 Cr | — | 1 |

## Vetoed (50) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 41.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 93% in 3 years — serial issuance di |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 39.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 125% in 3 years — serial issuance di |
| DBREALTY | promoter pledge 32.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| UTKARSHBNK | share capital up 62% in 3 years — serial issuance dilutes every rupee of future earnings |
| VIKRAN | share capital up 7779% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 66.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| MTNL | negative net worth (Rs-31602 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| SHALPAINTS | promoter pledge 70.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| UGROCAP | promoter holding only 2.88% and institutions hold just 9.1% — nobody with size is accountable for this company; share capital up 66% in 3 years — seri |
| GKENERGY | share capital up 4000% in 3 years — serial issuance dilutes every rupee of future earnings |
| OMAXE | negative net worth (Rs-925 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| MCLOUD | promoter pledge 59.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 53.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 251% in 3 years — serial issuance di |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SOLARWORLD | share capital up 13338% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GREENPOWER | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
