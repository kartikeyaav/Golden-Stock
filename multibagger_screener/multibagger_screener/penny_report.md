# Penny / nano-cap screen — 2026-11-25 15:25

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 179 names that survived the hard tradability gates
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
| 1 | **KESORAMIND** | PRICE+MCAP | 80 | 100% | CONFIRMED | 96 | Rs1.60 Cr | Rs446 Cr | Turnaround (margin-confirmed) + Deleveraging + Momentum | — |
| 2 | **AVTNPL** | PRICE | 78 | 100% | CONFIRMED | 92 | Rs3.35 Cr | Rs1471 Cr | Hyper-growth + Momentum | — |
| 3 | **DBOL** | MCAP | 77 | 100% | CONFIRMED | 97 | Rs2.82 Cr | Rs936 Cr | Turnaround (margin-confirmed) + Deleveraging + Momentum | — |
| 4 | **MODIS** | MCAP | 74 | 100% | YOUNG | 86 | Rs2.15 Cr | Rs903 Cr | Hyper-growth | — |
| 5 | **SYNCOMF** | PRICE | 73 | 100% | CONFIRMED | 95 | Rs19.58 Cr | Rs1905 Cr | Deleveraging + Momentum | — |
| 6 | **MOLDTECH** | PRICE+MCAP | 72 | 100% | WATCH | 87 | Rs1.37 Cr | Rs512 Cr | Hyper-growth + Deleveraging | — |
| 7 | **SEJALLTD** | MCAP | 72 | 100% | CONFIRMED | 80 | Rs3.22 Cr | Rs989 Cr | Hyper-growth + Momentum | — |
| 8 | **ARFIN** | PRICE | 72 | 100% | CONFIRMED | 89 | Rs14.15 Cr | Rs1557 Cr | Hyper-growth + Momentum | — |
| 9 | **SUBEXLTD** | PRICE+MCAP | 71 | 100% | CONFIRMED | 98 | Rs7.88 Cr | Rs900 Cr | Momentum | — |
| 10 | **NIVABUPA** | PRICE | 71 | 90% | ANTICIPATION | 64 | Rs7.34 Cr | — | — | — |
| 11 | **HITECH** | PRICE | 70 | 100% | WATCH | 59 | Rs4.57 Cr | Rs1525 Cr | Hyper-growth | — |
| 12 | **CONFIPET** | PRICE | 70 | 100% | BROKEN | 89 | Rs14.03 Cr | Rs2205 Cr | Hyper-growth | — |
| 13 | **EMKAY** | MCAP | 70 | 100% | WATCH | 78 | Rs1.16 Cr | Rs712 Cr | Hyper-growth | — |
| 14 | **TIRUPATIFL** | PRICE | 70 | 90% | CONFIRMED | 99 | Rs3.77 Cr | — | Momentum | — |
| 15 | **MANALIPETC** | PRICE | 69 | 100% | BROKEN | 79 | Rs6.09 Cr | Rs1300 Cr | Hyper-growth | — |
| 16 | **BALAJITELE** | PRICE | 69 | 100% | WATCH | 71 | Rs1.18 Cr | Rs1149 Cr | Turnaround (margin-confirmed) + Hyper-growth + Deleveraging | — |
| 17 | **UNITEDPOLY** | PRICE | 69 | 100% | CONFIRMED | 93 | Rs1.47 Cr | Rs1222 Cr | Momentum | — |
| 18 | **PNBGILTS** | PRICE | 68 | 90% | BROKEN | 72 | Rs4.21 Cr | — | Turnaround (margin-confirmed) | — |
| 19 | **KAMDHENU** | PRICE | 68 | 100% | WATCH | 93 | Rs2.91 Cr | Rs1058 Cr | Hyper-growth | — |
| 20 | **AARTISURF** | MCAP | 67 | 100% | CONFIRMED | 90 | Rs1.19 Cr | Rs456 Cr | Hyper-growth + Momentum | 1 |

## Vetoed (48) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 41.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 93% in 3 years — serial issuance di |
| ONEPOINT | promoter pledge 39.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 64% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 125% in 3 years — serial issuance di |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DBREALTY | promoter pledge 32.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| UTKARSHBNK | share capital up 62% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 66.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| VIKRAN | share capital up 7779% in 3 years — serial issuance dilutes every rupee of future earnings |
| UGROCAP | promoter holding only 2.88% and institutions hold just 9.1% — nobody with size is accountable for this company; share capital up 66% in 3 years — seri |
| SHALPAINTS | promoter pledge 70.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MTNL | negative net worth (Rs-31602 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 59.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 53.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 251% in 3 years — serial issuance di |
| GKENERGY | share capital up 4000% in 3 years — serial issuance dilutes every rupee of future earnings |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SOLARWORLD | share capital up 13338% in 3 years — serial issuance dilutes every rupee of future earnings |
| OMAXE | negative net worth (Rs-925 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
