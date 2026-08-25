# Penny / nano-cap screen — 2026-08-25 05:43

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 160 names that survived the hard tradability gates
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
| 1 | **ANDHRSUGAR** | PRICE | 83 | 100% | CONFIRMED | 90 | Rs4.54 Cr | Rs1340 Cr | Deleveraging + Momentum | — |
| 2 | **PONNIERODE** | MCAP | 75 | 100% | EXTENDED | 96 | Rs0.92 Cr | Rs351 Cr | — | — |
| 3 | **VISAKAIND** | PRICE+MCAP | 72 | 100% | CONFIRMED | 91 | Rs2.67 Cr | Rs825 Cr | Momentum | — |
| 4 | **MAWANASUG** | MCAP | 71 | 100% | EXTENDED | 99 | Rs10.39 Cr | Rs505 Cr | — | — |
| 5 | **MANALIPETC** | PRICE | 71 | 100% | WATCH | 86 | Rs3.60 Cr | Rs1191 Cr | — | — |
| 6 | **ATALREAL** | PRICE+MCAP | 71 | 100% | CONFIRMED | 94 | Rs36.11 Cr | Rs444 Cr | Momentum | 1 |
| 7 | **TNPETRO** | MCAP | 70 | 100% | WATCH | 81 | Rs2.28 Cr | Rs998 Cr | — | — |
| 8 | **DMCC** | MCAP | 70 | 100% | WATCH | 70 | Rs1.51 Cr | Rs714 Cr | Hyper-growth | — |
| 9 | **AMBIKCO** | MCAP | 69 | 100% | WATCH | 83 | Rs2.03 Cr | Rs940 Cr | — | — |
| 10 | **SYNCOMF** | PRICE | 69 | 100% | WATCH | 79 | Rs2.52 Cr | Rs1402 Cr | Deleveraging | — |
| 11 | **TPLPLASTEH** | PRICE+MCAP | 69 | 100% | CONFIRMED | 80 | Rs1.00 Cr | Rs603 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 12 | **LAXMIINDIA** | MCAP | 68 | 100% | WATCH | 76 | Rs2.94 Cr | Rs659 Cr | Hyper-growth | — |
| 13 | **AUTOIND** | PRICE+MCAP | 68 | 100% | CONFIRMED | 87 | Rs3.17 Cr | Rs401 Cr | Hyper-growth + Momentum | — |
| 14 | **DBOL** | MCAP | 68 | 100% | CONFIRMED | 93 | Rs1.79 Cr | Rs795 Cr | Turnaround (unconfirmed) + Momentum | — |
| 15 | **SIGMA** | PRICE+MCAP | 67 | 100% | WATCH | 84 | Rs0.90 Cr | Rs500 Cr | Deleveraging | 1 |
| 16 | **MUKKA** | PRICE+MCAP | 66 | 100% | WATCH | 65 | Rs0.56 Cr | Rs798 Cr | Hyper-growth | — |
| 17 | **SOUTHWEST** | MCAP | 65 | 100% | BROKEN | 92 | Rs2.57 Cr | Rs712 Cr | Hyper-growth | 1 |
| 18 | **GOKUL** | PRICE+MCAP | 65 | 100% | WATCH | 79 | Rs0.59 Cr | Rs385 Cr | — | — |
| 19 | **MOL** | PRICE | 64 | 100% | WATCH | 69 | Rs8.30 Cr | Rs1608 Cr | — | — |
| 20 | **ESTER** | PRICE | 64 | 100% | WATCH | 55 | Rs0.62 Cr | Rs1012 Cr | Turnaround (margin-confirmed) | — |

## Vetoed (50) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| JINDWORLD | share capital up 400% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| ALLCARGO | share capital up 512% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| RENUKA | negative net worth (Rs-2677 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| KECL | promoter pledge 75.3% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
