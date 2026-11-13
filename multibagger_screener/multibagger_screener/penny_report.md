# Penny / nano-cap screen — 2026-11-13 13:01

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 189 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 82 | 100% | CONFIRMED | 91 | Rs1.76 Cr | Rs608 Cr | Hyper-growth + Momentum | — |
| 2 | **AVTNPL** | PRICE | 77 | 100% | CONFIRMED | 93 | Rs4.34 Cr | Rs1518 Cr | Hyper-growth + Momentum | — |
| 3 | **AMANTA** | MCAP | 76 | 100% | EXTENDED | 100 | Rs2.26 Cr | Rs758 Cr | — | — |
| 4 | **KESORAMIND** | PRICE+MCAP | 75 | 100% | CONFIRMED | 99 | Rs1.30 Cr | Rs374 Cr | Deleveraging + Momentum | — |
| 5 | **PARACABLES** | PRICE | 74 | 100% | CONFIRMED | 87 | Rs16.84 Cr | Rs2011 Cr | Momentum | 1 |
| 6 | **SEJALLTD** | MCAP | 74 | 100% | CONFIRMED | 80 | Rs3.22 Cr | Rs882 Cr | Hyper-growth + Momentum | 1 |
| 7 | **ARFIN** | PRICE | 72 | 100% | CONFIRMED | 88 | Rs15.46 Cr | Rs1589 Cr | Hyper-growth + Momentum | — |
| 8 | **CONFIPET** | PRICE | 70 | 100% | BROKEN | 86 | Rs13.33 Cr | Rs1979 Cr | Hyper-growth | — |
| 9 | **MAZDA** | MCAP | 70 | 100% | CONFIRMED | 84 | Rs1.13 Cr | Rs559 Cr | Deleveraging + Momentum | — |
| 10 | **EMKAY** | MCAP | 70 | 100% | WATCH | 72 | Rs1.16 Cr | Rs702 Cr | Hyper-growth | — |
| 11 | **ARIHANTCAP** | PRICE+MCAP | 69 | 100% | CONFIRMED | 82 | Rs3.85 Cr | Rs935 Cr | Momentum | — |
| 12 | **KAMDHENU** | PRICE | 69 | 100% | WATCH | 94 | Rs2.91 Cr | Rs1029 Cr | Hyper-growth | — |
| 13 | **UNITEDPOLY** | PRICE | 68 | 100% | CONFIRMED | 93 | Rs1.71 Cr | Rs1246 Cr | Momentum | — |
| 14 | **MANALIPETC** | PRICE | 68 | 100% | WATCH | 85 | Rs7.55 Cr | Rs1176 Cr | — | — |
| 15 | **MANBA** | MCAP | 67 | 100% | CONFIRMED | 83 | Rs1.36 Cr | Rs730 Cr | Hyper-growth + Momentum | — |
| 16 | **DBOL** | MCAP | 66 | 100% | CONFIRMED | 96 | Rs2.82 Cr | Rs779 Cr | Turnaround (unconfirmed) + Momentum | — |
| 17 | **ORIENTBELL** | MCAP | 66 | 100% | CONFIRMED | 90 | Rs0.76 Cr | Rs511 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 18 | **SYNCOMF** | PRICE | 66 | 100% | WATCH | 92 | Rs16.29 Cr | Rs1905 Cr | Deleveraging | — |
| 19 | **HMAAGRO** | PRICE | 65 | 100% | WATCH | 71 | Rs3.77 Cr | Rs1245 Cr | Hyper-growth | 1 |
| 20 | **EMAMIPAP** | MCAP | 65 | 100% | WATCH | 89 | Rs0.51 Cr | Rs709 Cr | — | — |

## Vetoed (62) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| SBC | promoter pledge 41.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 93% in 3 years — serial issuance di |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 39.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| RTNPOWER | promoter pledge 43.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DBREALTY | promoter pledge 32.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | promoter pledge 25.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 109% in 3 years — serial issuance di |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 66.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| MTNL | negative net worth (Rs-29960 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| GKENERGY | share capital up 4000% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 59.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 53.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 251% in 3 years — serial issuance di |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
