# Penny / nano-cap screen — 2026-08-17 06:12

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 116 names that survived the hard tradability gates
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
| 1 | **PREMIERPOL** | PRICE+MCAP | 79 | 100% | CONFIRMED | 94 | Rs1.99 Cr | Rs770 Cr | Deleveraging + Momentum | — |
| 2 | **FILATEX** | PRICE | 72 | 100% | EXTENDED | 96 | Rs33.42 Cr | Rs3614 Cr | Deleveraging | — |
| 3 | **ATALREAL** | PRICE+MCAP | 68 | 100% | EXTENDED | 97 | Rs29.88 Cr | Rs444 Cr | — | 1 |
| 4 | **VISAKAIND** | PRICE+MCAP | 68 | 100% | WATCH | 91 | Rs2.56 Cr | Rs825 Cr | — | — |
| 5 | **TPLPLASTEH** | PRICE+MCAP | 68 | 100% | CONFIRMED | 84 | Rs1.00 Cr | Rs603 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 6 | **TNPETRO** | MCAP | 67 | 100% | WATCH | 86 | Rs0.88 Cr | Rs998 Cr | — | — |
| 7 | **MANALIPETC** | PRICE | 67 | 100% | WATCH | 83 | Rs2.17 Cr | Rs1191 Cr | — | — |
| 8 | **SYNCOMF** | PRICE | 65 | 100% | WATCH | 66 | Rs1.66 Cr | Rs1402 Cr | Deleveraging | — |
| 9 | **DBOL** | MCAP | 65 | 100% | CONFIRMED | 93 | Rs1.00 Cr | Rs795 Cr | Turnaround (unconfirmed) + Momentum | — |
| 10 | **MOL** | PRICE | 65 | 100% | WATCH | 68 | Rs7.12 Cr | Rs1608 Cr | — | — |
| 11 | **UGARSUGAR** | PRICE+MCAP | 64 | 100% | WATCH | 90 | Rs0.58 Cr | Rs542 Cr | Hyper-growth + Deleveraging | 1 |
| 12 | **HMAAGRO** | PRICE | 63 | 100% | WATCH | 44 | Rs1.36 Cr | Rs1214 Cr | Hyper-growth | 1 |
| 13 | **KALAMANDIR** | PRICE | 63 | 100% | BROKEN | 6 | Rs4.92 Cr | Rs1335 Cr | Hyper-growth | — |
| 14 | **SARLAPOLY** | MCAP | 63 | 100% | CONFIRMED | 81 | Rs0.51 Cr | Rs852 Cr | Momentum | — |
| 15 | **BESTAGRO** | PRICE+MCAP | 61 | 100% | WATCH | 38 | Rs1.38 Cr | Rs666 Cr | — | 1 |
| 16 | **RTNPOWER** | PRICE | 60 | 100% | BROKEN | 33 | Rs8.27 Cr | Rs4538 Cr | Turnaround (margin-confirmed) + Deleveraging | 1 |
| 17 | **MEDICO** | PRICE+MCAP | 60 | 100% | WATCH | 75 | Rs1.98 Cr | Rs378 Cr | Hyper-growth | — |
| 18 | **RUSHIL** | PRICE+MCAP | 60 | 100% | WATCH | 23 | Rs1.34 Cr | Rs505 Cr | Turnaround (margin-confirmed) | — |
| 19 | **NARMADA** | PRICE+MCAP | 60 | 70% | WATCH | 79 | Rs2.72 Cr | Rs115 Cr | — | — |
| 20 | **GATEWAY** | PRICE | 59 | 100% | ANTICIPATION | 43 | Rs4.15 Cr | Rs2741 Cr | — | — |

## Vetoed (43) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| JINDWORLD | share capital up 400% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RENUKA | negative net worth (Rs-2677 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| DHANBANK | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| HARDWYN | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| OMAXE | negative net worth (Rs-901 Cr) — accumulated losses have eaten the equity; recovery requires dilution |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
