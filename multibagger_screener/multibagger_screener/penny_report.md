# Penny / nano-cap screen — 2026-08-22 05:38

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 126 names that survived the hard tradability gates
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
| 1 | **ANDHRSUGAR** | PRICE | 82 | 100% | CONFIRMED | 90 | Rs3.40 Cr | Rs1340 Cr | Deleveraging + Momentum | — |
| 2 | **VISAKAIND** | PRICE+MCAP | 72 | 100% | CONFIRMED | 91 | Rs2.67 Cr | Rs825 Cr | Momentum | — |
| 3 | **MANALIPETC** | PRICE | 71 | 100% | WATCH | 86 | Rs3.60 Cr | Rs1191 Cr | — | — |
| 4 | **MAWANASUG** | MCAP | 71 | 100% | EXTENDED | 99 | Rs9.20 Cr | Rs505 Cr | — | — |
| 5 | **ATALREAL** | PRICE+MCAP | 71 | 100% | CONFIRMED | 95 | Rs34.29 Cr | Rs444 Cr | Momentum | 1 |
| 6 | **TNPETRO** | MCAP | 70 | 100% | WATCH | 84 | Rs2.04 Cr | Rs998 Cr | — | — |
| 7 | **TPLPLASTEH** | PRICE+MCAP | 69 | 100% | CONFIRMED | 82 | Rs1.00 Cr | Rs603 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 8 | **LAXMIINDIA** | MCAP | 68 | 100% | YOUNG | 74 | Rs2.78 Cr | Rs659 Cr | Hyper-growth | — |
| 9 | **DBOL** | MCAP | 68 | 100% | CONFIRMED | 96 | Rs1.48 Cr | Rs795 Cr | Turnaround (unconfirmed) + Momentum | — |
| 10 | **UGARSUGAR** | PRICE+MCAP | 68 | 100% | EXTENDED | 94 | Rs1.06 Cr | Rs542 Cr | Hyper-growth + Deleveraging | 1 |
| 11 | **SYNCOMF** | PRICE | 67 | 100% | WATCH | 67 | Rs2.13 Cr | Rs1402 Cr | Deleveraging | — |
| 12 | **MUKKA** | PRICE+MCAP | 66 | 100% | WATCH | 72 | Rs0.54 Cr | Rs798 Cr | Hyper-growth | — |
| 13 | **SUBEXLTD** | PRICE+MCAP | 66 | 100% | EXTENDED | 98 | Rs33.83 Cr | Rs924 Cr | — | — |
| 14 | **ESTER** | PRICE | 65 | 100% | WATCH | 64 | Rs0.62 Cr | Rs1012 Cr | Turnaround (margin-confirmed) | — |
| 15 | **SIGMA** | PRICE+MCAP | 65 | 100% | WATCH | 76 | Rs0.58 Cr | Rs500 Cr | Deleveraging | 1 |
| 16 | **DJML** | MCAP | 64 | 100% | WATCH | 78 | Rs3.97 Cr | Rs390 Cr | Hyper-growth | — |
| 17 | **MOL** | PRICE | 64 | 100% | WATCH | 62 | Rs8.30 Cr | Rs1608 Cr | — | — |
| 18 | **GOKUL** | PRICE+MCAP | 63 | 100% | WATCH | 79 | Rs0.58 Cr | Rs385 Cr | — | — |
| 19 | **KALAMANDIR** | PRICE | 62 | 100% | BROKEN | 4 | Rs3.81 Cr | Rs1335 Cr | Hyper-growth | — |
| 20 | **DWARKESH** | PRICE+MCAP | 62 | 100% | EXTENDED | 93 | Rs5.29 Cr | Rs796 Cr | — | — |

## Vetoed (43) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| JINDWORLD | share capital up 400% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| RENUKA | negative net worth (Rs-2677 Cr) — accumulated losses have eaten the equity; recovery requires dilution |
| FISCHER | share capital up 38135% in 3 years — serial issuance dilutes every rupee of future earnings |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
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
