# Penny / nano-cap screen — 2026-09-22 09:43

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 195 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 81 | 100% | CONFIRMED | 94 | Rs1.10 Cr | Rs605 Cr | Hyper-growth + Momentum | — |
| 2 | **MANALIPETC** | PRICE | 78 | 100% | CONFIRMED | 96 | Rs18.30 Cr | Rs1413 Cr | Momentum | — |
| 3 | **ANDHRSUGAR** | PRICE | 77 | 100% | CONFIRMED | 85 | Rs4.82 Cr | Rs1275 Cr | Deleveraging + Momentum | — |
| 4 | **AVTNPL** | PRICE | 77 | 100% | CONFIRMED | 89 | Rs1.97 Cr | Rs1305 Cr | Hyper-growth + Momentum | — |
| 5 | **PONNIERODE** | MCAP | 75 | 100% | CONFIRMED | 83 | Rs1.51 Cr | Rs313 Cr | Momentum | — |
| 6 | **UGARSUGAR** | PRICE+MCAP | 75 | 100% | CONFIRMED | 90 | Rs6.10 Cr | Rs597 Cr | Hyper-growth + Deleveraging + Momentum | 1 |
| 7 | **SAHYADRI** | MCAP | 74 | 100% | CONFIRMED | 92 | Rs0.51 Cr | Rs428 Cr | Deleveraging + Momentum | — |
| 8 | **VETO** | MCAP | 74 | 100% | EXTENDED | 90 | Rs5.28 Cr | Rs265 Cr | Hyper-growth + Deleveraging | — |
| 9 | **DMCC** | MCAP | 72 | 100% | CONFIRMED | 72 | Rs1.38 Cr | Rs729 Cr | Hyper-growth + Momentum | — |
| 10 | **MGEL** | PRICE+MCAP | 72 | 100% | CONFIRMED | 87 | Rs1.14 Cr | Rs532 Cr | Hyper-growth + Momentum | — |
| 11 | **ORIENTBELL** | MCAP | 71 | 100% | CONFIRMED | 88 | Rs1.56 Cr | Rs591 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 12 | **KANPRPLA** | MCAP | 71 | 100% | CONFIRMED | 86 | Rs0.70 Cr | Rs650 Cr | Deleveraging + Momentum | — |
| 13 | **LAXMIINDIA** | MCAP | 70 | 100% | WATCH | 79 | Rs2.76 Cr | Rs665 Cr | Hyper-growth | — |
| 14 | **HMAAGRO** | PRICE | 70 | 100% | WATCH | 35 | Rs6.61 Cr | Rs1157 Cr | Hyper-growth | 1 |
| 15 | **ARFIN** | PRICE | 69 | 100% | CONFIRMED | 94 | Rs8.89 Cr | Rs1504 Cr | Momentum | — |
| 16 | **PREMIERPOL** | PRICE+MCAP | 68 | 100% | WATCH | 91 | Rs2.41 Cr | Rs857 Cr | — | — |
| 17 | **GLOBAL** | MCAP | 68 | 100% | CONFIRMED | 95 | Rs1.74 Cr | Rs646 Cr | Hyper-growth + Momentum | — |
| 18 | **KAMDHENU** | PRICE | 68 | 100% | CONFIRMED | 98 | Rs12.91 Cr | Rs1165 Cr | Hyper-growth + Momentum | — |
| 19 | **KAMATHOTEL** | MCAP | 68 | 100% | WATCH | 66 | Rs2.30 Cr | Rs661 Cr | Deleveraging | — |
| 20 | **SUBEXLTD** | PRICE | 68 | 100% | CONFIRMED | 99 | Rs17.84 Cr | Rs1107 Cr | Momentum | — |

## Vetoed (61) — capped at 25, momentum cannot outvote these

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
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |
| REGAAL | share capital up 410% in 3 years — serial issuance dilutes every rupee of future earnings |
| SCODATUBES | share capital up 5900% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
