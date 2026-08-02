# Penny / nano-cap screen — 2026-08-02 07:27

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 113 names that survived the hard tradability gates
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
| 1 | **PREMIERPOL** | PRICE+MCAP | 79 | 100% | CONFIRMED | 96 | Rs2.20 Cr | Rs831 Cr | Deleveraging + Momentum | — |
| 2 | **ESAFSFB** | PRICE | 78 | 100% | EXTENDED | 95 | Rs5.06 Cr | Rs1996 Cr | Turnaround (margin-confirmed) | — |
| 3 | **ATALREAL** | PRICE+MCAP | 75 | 100% | CONFIRMED | 96 | Rs23.72 Cr | Rs387 Cr | Hyper-growth + Momentum | 1 |
| 4 | **FILATEX** | PRICE | 71 | 100% | EXTENDED | 97 | Rs25.38 Cr | Rs3278 Cr | Deleveraging | — |
| 5 | **SHRIRAMPPS** | PRICE | 69 | 100% | WATCH | 71 | Rs3.96 Cr | Rs1451 Cr | Hyper-growth | — |
| 6 | **VISAKAIND** | PRICE+MCAP | 67 | 100% | WATCH | 85 | Rs1.39 Cr | Rs690 Cr | — | — |
| 7 | **ANDHRSUGAR** | PRICE | 66 | 100% | WATCH | 81 | Rs2.42 Cr | Rs1170 Cr | Deleveraging | — |
| 8 | **HMVL** | PRICE+MCAP | 65 | 100% | CONFIRMED | 86 | Rs0.53 Cr | Rs697 Cr | Momentum | — |
| 9 | **UYFINCORP** | PRICE+MCAP | 64 | 100% | EXTENDED | 93 | Rs0.73 Cr | Rs353 Cr | Hyper-growth | — |
| 10 | **SINDHUTRAD** | PRICE | 64 | 100% | WATCH | 82 | Rs1.87 Cr | Rs3770 Cr | Turnaround (margin-confirmed) + Deleveraging | — |
| 11 | **KALAMANDIR** | PRICE | 64 | 100% | BROKEN | 6 | Rs6.80 Cr | Rs1356 Cr | Hyper-growth | — |
| 12 | **GATEWAY** | PRICE | 64 | 100% | WATCH | 59 | Rs4.12 Cr | Rs2817 Cr | Turnaround (margin-confirmed) + Hyper-growth | — |
| 13 | **TPLPLASTEH** | PRICE+MCAP | 63 | 100% | WATCH | 84 | Rs1.04 Cr | Rs600 Cr | Deleveraging | — |
| 14 | **3IINFOLTD** | PRICE+MCAP | 62 | 100% | EXTENDED | 89 | Rs0.88 Cr | Rs409 Cr | Deleveraging | — |
| 15 | **MUNJALAU** | MCAP | 62 | 100% | WATCH | 94 | Rs3.53 Cr | Rs998 Cr | — | — |
| 16 | **BESTAGRO** | PRICE+MCAP | 61 | 100% | WATCH | 16 | Rs0.62 Cr | Rs678 Cr | — | — |
| 17 | **RTNPOWER** | PRICE | 61 | 100% | BROKEN | 43 | Rs8.29 Cr | Rs4634 Cr | Turnaround (margin-confirmed) + Deleveraging | 1 |
| 18 | **JAGRAN** | PRICE | 60 | 100% | BROKEN | 52 | Rs1.23 Cr | Rs1368 Cr | Turnaround (margin-confirmed) + Deleveraging | — |
| 19 | **INDORAMA** | PRICE | 60 | 100% | WATCH | 88 | Rs0.82 Cr | Rs1265 Cr | — | — |
| 20 | **MANALIPETC** | PRICE | 60 | 100% | WATCH | 75 | Rs1.41 Cr | Rs1148 Cr | — | — |

## Vetoed (38) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| HARDWYN | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| RENUKA | negative net worth (Rs-2677 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| OMAXE | negative net worth (Rs-901 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| ROTO | share capital up 533% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| NARMADA | share capital up 180% in 3 years — serial issuance dilutes every rupee of future earnings |
| ALLCARGO | share capital up 512% in 3 years — serial issuance dilutes every rupee of future earnings |
| JINDWORLD | share capital up 400% in 3 years — serial issuance dilutes every rupee of future earnings |
| MTNL | negative net worth (Rs-29960 Cr) — accumulated losses have eaten the equity; recovery requires dilution |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
