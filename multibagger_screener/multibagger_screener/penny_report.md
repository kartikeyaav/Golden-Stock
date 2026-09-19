# Penny / nano-cap screen — 2026-09-19 09:17

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 193 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 81 | 100% | CONFIRMED | 96 | Rs1.31 Cr | Rs605 Cr | Hyper-growth + Momentum | — |
| 2 | **PONNIERODE** | MCAP | 78 | 100% | CONFIRMED | 85 | Rs1.52 Cr | Rs313 Cr | Momentum | — |
| 3 | **MANALIPETC** | PRICE | 77 | 100% | CONFIRMED | 92 | Rs18.30 Cr | Rs1413 Cr | Momentum | — |
| 4 | **ANDHRSUGAR** | PRICE | 77 | 100% | CONFIRMED | 87 | Rs4.83 Cr | Rs1344 Cr | Deleveraging + Momentum | — |
| 5 | **AVTNPL** | PRICE | 77 | 100% | CONFIRMED | 86 | Rs1.97 Cr | Rs1305 Cr | Hyper-growth + Momentum | — |
| 6 | **SAHYADRI** | MCAP | 75 | 100% | CONFIRMED | 95 | Rs0.56 Cr | Rs428 Cr | Deleveraging + Momentum | — |
| 7 | **UGARSUGAR** | PRICE+MCAP | 74 | 100% | CONFIRMED | 89 | Rs6.60 Cr | Rs597 Cr | Hyper-growth + Deleveraging + Momentum | 1 |
| 8 | **MGEL** | PRICE+MCAP | 73 | 100% | CONFIRMED | 88 | Rs1.74 Cr | Rs532 Cr | Hyper-growth + Momentum | — |
| 9 | **KANPRPLA** | MCAP | 73 | 100% | CONFIRMED | 90 | Rs0.70 Cr | Rs650 Cr | Deleveraging + Momentum | — |
| 10 | **PREMIERPOL** | PRICE+MCAP | 73 | 100% | CONFIRMED | 93 | Rs2.31 Cr | Rs857 Cr | Momentum | — |
| 11 | **ORIENTBELL** | MCAP | 72 | 100% | CONFIRMED | 90 | Rs1.56 Cr | Rs591 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 12 | **MAWANASUG** | MCAP | 71 | 100% | CONFIRMED | 94 | Rs4.47 Cr | Rs502 Cr | Momentum | — |
| 13 | **LAXMIINDIA** | MCAP | 71 | 100% | WATCH | 80 | Rs2.77 Cr | Rs665 Cr | Hyper-growth | — |
| 14 | **HMAAGRO** | PRICE | 69 | 100% | WATCH | 36 | Rs6.61 Cr | Rs1157 Cr | Hyper-growth | 1 |
| 15 | **ARFIN** | PRICE | 68 | 100% | CONFIRMED | 96 | Rs8.89 Cr | Rs1603 Cr | Momentum | — |
| 16 | **GLOBAL** | MCAP | 68 | 100% | CONFIRMED | 95 | Rs1.57 Cr | Rs646 Cr | Hyper-growth + Momentum | — |
| 17 | **VISAKAIND** | PRICE+MCAP | 68 | 100% | CONFIRMED | 92 | Rs1.94 Cr | Rs756 Cr | Momentum | — |
| 18 | **DMCC** | MCAP | 67 | 100% | WATCH | 65 | Rs1.52 Cr | Rs729 Cr | Hyper-growth | — |
| 19 | **KAMATHOTEL** | MCAP | 66 | 100% | WATCH | 52 | Rs2.37 Cr | Rs661 Cr | Deleveraging | — |
| 20 | **ALBERTDAVD** | MCAP | 66 | 100% | CONFIRMED | 77 | Rs0.55 Cr | Rs482 Cr | Momentum | — |

## Vetoed (59) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
