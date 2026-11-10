# Penny / nano-cap screen — 2026-11-10 13:24

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 204 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 81 | 100% | WATCH | 93 | Rs1.76 Cr | Rs608 Cr | Hyper-growth | — |
| 2 | **AMANTA** | MCAP | 77 | 100% | CONFIRMED | 98 | Rs2.18 Cr | Rs758 Cr | Momentum | — |
| 3 | **KESORAMIND** | PRICE+MCAP | 74 | 100% | CONFIRMED | 99 | Rs1.24 Cr | Rs374 Cr | Deleveraging + Momentum | — |
| 4 | **PARACABLES** | PRICE | 74 | 100% | CONFIRMED | 90 | Rs14.93 Cr | Rs2011 Cr | Momentum | 1 |
| 5 | **ARFIN** | PRICE | 74 | 100% | CONFIRMED | 91 | Rs19.67 Cr | Rs1589 Cr | Hyper-growth + Momentum | — |
| 6 | **SEJALLTD** | MCAP | 72 | 100% | CONFIRMED | 77 | Rs3.01 Cr | Rs882 Cr | Hyper-growth + Momentum | 1 |
| 7 | **MAZDA** | MCAP | 71 | 100% | CONFIRMED | 88 | Rs1.20 Cr | Rs559 Cr | Deleveraging + Momentum | — |
| 8 | **EMKAY** | MCAP | 70 | 100% | WATCH | 76 | Rs1.28 Cr | Rs702 Cr | Hyper-growth | — |
| 9 | **ARIHANTCAP** | PRICE+MCAP | 70 | 100% | CONFIRMED | 85 | Rs4.77 Cr | Rs935 Cr | Momentum | — |
| 10 | **UNITEDPOLY** | PRICE | 70 | 100% | CONFIRMED | 97 | Rs1.71 Cr | Rs1246 Cr | Momentum | — |
| 11 | **KALAMANDIR** | PRICE+MCAP | 70 | 100% | BROKEN | 13 | Rs3.07 Cr | Rs996 Cr | Hyper-growth | — |
| 12 | **EMAMIPAP** | MCAP | 70 | 100% | CONFIRMED | 93 | Rs0.56 Cr | Rs709 Cr | Momentum | — |
| 13 | **ANDHRSUGAR** | PRICE | 69 | 100% | ANTICIPATION | 58 | Rs2.69 Cr | Rs1106 Cr | Deleveraging | — |
| 14 | **CONFIPET** | PRICE | 69 | 100% | BROKEN | 89 | Rs13.33 Cr | Rs1979 Cr | Hyper-growth | — |
| 15 | **KAMDHENU** | PRICE | 69 | 100% | WATCH | 94 | Rs3.14 Cr | Rs1029 Cr | Hyper-growth | — |
| 16 | **MANALIPETC** | PRICE | 68 | 100% | WATCH | 87 | Rs8.70 Cr | Rs1176 Cr | — | — |
| 17 | **PONNIERODE** | MCAP | 68 | 100% | WATCH | 82 | Rs1.12 Cr | Rs275 Cr | Hyper-growth | — |
| 18 | **PNBGILTS** | PRICE | 67 | 100% | WATCH | 72 | Rs4.05 Cr | Rs1351 Cr | Turnaround (margin-confirmed) | — |
| 19 | **MANBA** | MCAP | 67 | 100% | CONFIRMED | 86 | Rs1.22 Cr | Rs730 Cr | Hyper-growth + Momentum | — |
| 20 | **DBOL** | MCAP | 66 | 100% | CONFIRMED | 95 | Rs2.84 Cr | Rs779 Cr | Turnaround (unconfirmed) + Momentum | — |

## Vetoed (64) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 41.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 39.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DBREALTY | promoter pledge 32.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 109% in 3 years — serial issuance di |
| PATELENG | promoter pledge 66.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| MTNL | negative net worth (Rs-29960 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| GKENERGY | share capital up 4000% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 59.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 98.7% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 9.38% and institutions hold jus |
| NITCO | promoter pledge 53.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RAJOOENG | share capital up 200% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
