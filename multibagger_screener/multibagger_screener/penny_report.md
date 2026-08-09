# Penny / nano-cap screen — 2026-08-09 05:55

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 114 names that survived the hard tradability gates
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
| 1 | **ESAFSFB** | PRICE | 79 | 100% | CONFIRMED | 90 | Rs6.33 Cr | Rs1996 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 2 | **PREMIERPOL** | PRICE+MCAP | 79 | 100% | CONFIRMED | 93 | Rs1.99 Cr | Rs831 Cr | Deleveraging + Momentum | — |
| 3 | **ATALREAL** | PRICE+MCAP | 73 | 100% | EXTENDED | 96 | Rs27.90 Cr | Rs387 Cr | Hyper-growth | 1 |
| 4 | **FILATEX** | PRICE | 71 | 100% | EXTENDED | 97 | Rs28.06 Cr | Rs3278 Cr | Deleveraging | — |
| 5 | **VISAKAIND** | PRICE+MCAP | 71 | 100% | EXTENDED | 94 | Rs1.66 Cr | Rs690 Cr | — | — |
| 6 | **ANDHRSUGAR** | PRICE | 69 | 100% | CONFIRMED | 84 | Rs2.34 Cr | Rs1170 Cr | Deleveraging + Momentum | — |
| 7 | **SHRIRAMPPS** | PRICE | 68 | 100% | WATCH | 71 | Rs3.53 Cr | Rs1451 Cr | Hyper-growth | — |
| 8 | **3IINFOLTD** | PRICE+MCAP | 66 | 100% | EXTENDED | 95 | Rs3.03 Cr | Rs409 Cr | Deleveraging | — |
| 9 | **GATEWAY** | PRICE | 66 | 100% | WATCH | 46 | Rs4.12 Cr | Rs2817 Cr | Turnaround (margin-confirmed) + Hyper-growth | — |
| 10 | **UYFINCORP** | PRICE+MCAP | 64 | 100% | EXTENDED | 89 | Rs0.81 Cr | Rs353 Cr | Hyper-growth | — |
| 11 | **KALAMANDIR** | PRICE | 64 | 100% | BROKEN | 6 | Rs5.27 Cr | Rs1356 Cr | Hyper-growth | — |
| 12 | **TPLPLASTEH** | PRICE+MCAP | 64 | 100% | WATCH | 81 | Rs1.08 Cr | Rs600 Cr | Deleveraging | — |
| 13 | **SINDHUTRAD** | PRICE | 63 | 100% | WATCH | 74 | Rs1.22 Cr | Rs3770 Cr | Turnaround (margin-confirmed) + Deleveraging | — |
| 14 | **DBOL** | MCAP | 62 | 100% | CONFIRMED | 86 | Rs0.93 Cr | Rs650 Cr | Turnaround (unconfirmed) + Momentum | — |
| 15 | **RTNPOWER** | PRICE | 60 | 100% | BROKEN | 34 | Rs8.71 Cr | Rs4634 Cr | Turnaround (margin-confirmed) + Deleveraging | 1 |
| 16 | **JAGRAN** | PRICE | 60 | 100% | BROKEN | 54 | Rs1.23 Cr | Rs1368 Cr | Turnaround (margin-confirmed) + Deleveraging | — |
| 17 | **MUNJALAU** | MCAP | 60 | 100% | CONFIRMED | 92 | Rs3.22 Cr | Rs998 Cr | Momentum | — |
| 18 | **MANALIPETC** | PRICE | 60 | 100% | WATCH | 66 | Rs1.75 Cr | Rs1148 Cr | — | — |
| 19 | **NAVKARCORP** | PRICE | 58 | 100% | WATCH | 50 | Rs4.50 Cr | Rs1499 Cr | — | — |
| 20 | **BCLIND** | PRICE | 58 | 100% | WATCH | 80 | Rs2.10 Cr | Rs1055 Cr | — | — |

## Vetoed (43) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| JINDWORLD | share capital up 400% in 3 years — serial issuance dilutes every rupee of future earnings |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| RENUKA | negative net worth (Rs-2677 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| HARDWYN | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| OMAXE | negative net worth (Rs-901 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| NARMADA | share capital up 180% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
