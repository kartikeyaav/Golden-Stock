# Penny / nano-cap screen — 2026-08-19 05:42

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 123 names that survived the hard tradability gates
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
| 1 | **PREMIERPOL** | PRICE+MCAP | 79 | 100% | EXTENDED | 98 | Rs2.48 Cr | Rs770 Cr | Deleveraging | — |
| 2 | **FILATEX** | PRICE | 72 | 100% | EXTENDED | 96 | Rs33.42 Cr | Rs3614 Cr | Deleveraging | — |
| 3 | **MAWANASUG** | MCAP | 71 | 100% | CONFIRMED | 94 | Rs5.47 Cr | Rs505 Cr | Momentum | — |
| 4 | **ATALREAL** | PRICE+MCAP | 71 | 100% | CONFIRMED | 95 | Rs29.90 Cr | Rs444 Cr | Momentum | 1 |
| 5 | **LAXMIINDIA** | MCAP | 70 | 100% | YOUNG | 88 | Rs5.18 Cr | Rs659 Cr | Hyper-growth | — |
| 6 | **TNPETRO** | MCAP | 69 | 100% | WATCH | 86 | Rs1.14 Cr | Rs998 Cr | — | — |
| 7 | **VISAKAIND** | PRICE+MCAP | 68 | 100% | WATCH | 89 | Rs2.67 Cr | Rs825 Cr | — | — |
| 8 | **MANALIPETC** | PRICE | 68 | 100% | WATCH | 83 | Rs2.37 Cr | Rs1191 Cr | — | — |
| 9 | **TPLPLASTEH** | PRICE+MCAP | 68 | 100% | CONFIRMED | 79 | Rs1.00 Cr | Rs603 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 10 | **SYNCOMF** | PRICE | 67 | 100% | WATCH | 70 | Rs1.69 Cr | Rs1402 Cr | Deleveraging | — |
| 11 | **LATTEYS** | PRICE+MCAP | 67 | 100% | WATCH | 77 | Rs0.93 Cr | Rs131 Cr | Hyper-growth | 1 |
| 12 | **DBOL** | MCAP | 66 | 100% | CONFIRMED | 92 | Rs1.06 Cr | Rs795 Cr | Turnaround (unconfirmed) + Momentum | — |
| 13 | **UGARSUGAR** | PRICE+MCAP | 66 | 100% | WATCH | 91 | Rs0.86 Cr | Rs542 Cr | Hyper-growth + Deleveraging | 1 |
| 14 | **SUBEXLTD** | PRICE+MCAP | 66 | 100% | EXTENDED | 94 | Rs38.00 Cr | Rs924 Cr | — | — |
| 15 | **ESTER** | PRICE | 66 | 100% | WATCH | 68 | Rs0.56 Cr | Rs1012 Cr | Turnaround (margin-confirmed) | — |
| 16 | **MOL** | PRICE | 65 | 100% | WATCH | 64 | Rs7.31 Cr | Rs1608 Cr | — | — |
| 17 | **SARLAPOLY** | MCAP | 63 | 100% | CONFIRMED | 80 | Rs0.51 Cr | Rs852 Cr | Momentum | — |
| 18 | **KALAMANDIR** | PRICE | 63 | 100% | BROKEN | 5 | Rs4.33 Cr | Rs1335 Cr | Hyper-growth | — |
| 19 | **HMAAGRO** | PRICE | 62 | 100% | BROKEN | 24 | Rs1.54 Cr | Rs1214 Cr | Hyper-growth | 1 |
| 20 | **SINDHUTRAD** | PRICE | 61 | 100% | WATCH | 69 | Rs1.22 Cr | Rs3645 Cr | Deleveraging | — |

## Vetoed (41) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| JINDWORLD | share capital up 400% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| RENUKA | negative net worth (Rs-2677 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| SALSTEEL | share capital up 71% in 3 years — serial issuance dilutes every rupee of future earnings |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
