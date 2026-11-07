# Penny / nano-cap screen — 2026-11-07 11:38

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 207 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 86 | 100% | CONFIRMED | 97 | Rs1.76 Cr | Rs608 Cr | Hyper-growth + Momentum | — |
| 2 | **AVTNPL** | PRICE | 80 | 100% | CONFIRMED | 95 | Rs4.15 Cr | Rs1518 Cr | Hyper-growth + Momentum | — |
| 3 | **AMANTA** | MCAP | 76 | 100% | CONFIRMED | 98 | Rs2.18 Cr | Rs758 Cr | Momentum | — |
| 4 | **PARACABLES** | PRICE | 74 | 100% | CONFIRMED | 94 | Rs14.93 Cr | Rs2011 Cr | Momentum | 1 |
| 5 | **ARFIN** | PRICE | 74 | 100% | CONFIRMED | 91 | Rs19.67 Cr | Rs1589 Cr | Hyper-growth + Momentum | — |
| 6 | **KESORAMIND** | PRICE+MCAP | 73 | 100% | CONFIRMED | 99 | Rs1.10 Cr | Rs374 Cr | Deleveraging + Momentum | — |
| 7 | **SEJALLTD** | MCAP | 73 | 100% | CONFIRMED | 81 | Rs3.01 Cr | Rs882 Cr | Hyper-growth + Momentum | 1 |
| 8 | **EMKAY** | MCAP | 71 | 100% | WATCH | 70 | Rs1.34 Cr | Rs702 Cr | Hyper-growth | — |
| 9 | **MAZDA** | MCAP | 71 | 100% | CONFIRMED | 90 | Rs1.30 Cr | Rs559 Cr | Deleveraging + Momentum | — |
| 10 | **UNITEDPOLY** | PRICE | 71 | 100% | CONFIRMED | 96 | Rs2.27 Cr | Rs1246 Cr | Momentum | — |
| 11 | **CONFIPET** | PRICE | 71 | 100% | WATCH | 88 | Rs13.88 Cr | Rs1979 Cr | Hyper-growth | — |
| 12 | **ANDHRSUGAR** | PRICE | 71 | 100% | ANTICIPATION | 64 | Rs2.77 Cr | Rs1106 Cr | Deleveraging | — |
| 13 | **PONNIERODE** | MCAP | 70 | 100% | WATCH | 82 | Rs1.60 Cr | Rs275 Cr | Hyper-growth | — |
| 14 | **ARIHANTCAP** | PRICE+MCAP | 70 | 100% | CONFIRMED | 83 | Rs4.77 Cr | Rs935 Cr | Momentum | — |
| 15 | **KALAMANDIR** | PRICE+MCAP | 70 | 100% | BROKEN | 9 | Rs3.07 Cr | Rs996 Cr | Hyper-growth | — |
| 16 | **PNBGILTS** | PRICE | 69 | 100% | WATCH | 79 | Rs4.05 Cr | Rs1351 Cr | Turnaround (margin-confirmed) | — |
| 17 | **KAMDHENU** | PRICE | 69 | 100% | WATCH | 94 | Rs3.28 Cr | Rs1029 Cr | Hyper-growth | — |
| 18 | **MANALIPETC** | PRICE | 68 | 100% | WATCH | 88 | Rs8.99 Cr | Rs1176 Cr | — | — |
| 19 | **MANBA** | MCAP | 67 | 100% | CONFIRMED | 86 | Rs1.22 Cr | Rs730 Cr | Hyper-growth + Momentum | — |
| 20 | **SYNCOMF** | PRICE | 66 | 100% | WATCH | 92 | Rs23.85 Cr | Rs1914 Cr | Deleveraging | — |

## Vetoed (64) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 41.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 39.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| DBREALTY | promoter pledge 32.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 54% in 3 years — serial issuance dil |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 109% in 3 years — serial issuance di |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 66.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| GKENERGY | share capital up 4000% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MTNL | negative net worth (Rs-29960 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| NITCO | promoter pledge 53.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| MCLOUD | promoter pledge 59.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 98.7% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 9.38% and institutions hold jus |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
