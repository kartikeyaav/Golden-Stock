# Penny / nano-cap screen — 2026-09-25 10:07

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 191 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 80 | 100% | EXTENDED | 95 | Rs2.44 Cr | Rs605 Cr | Hyper-growth | — |
| 2 | **PREMIERPOL** | MCAP | 78 | 100% | CONFIRMED | 98 | Rs2.31 Cr | Rs857 Cr | Momentum | — |
| 3 | **AVTNPL** | PRICE | 78 | 100% | CONFIRMED | 89 | Rs1.97 Cr | Rs1305 Cr | Hyper-growth + Momentum | — |
| 4 | **MANALIPETC** | PRICE | 78 | 100% | CONFIRMED | 94 | Rs18.18 Cr | Rs1413 Cr | Momentum | — |
| 5 | **VETO** | MCAP | 75 | 100% | CONFIRMED | 88 | Rs2.45 Cr | Rs265 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 6 | **SYNCOMF** | PRICE | 74 | 100% | CONFIRMED | 91 | Rs20.29 Cr | Rs1887 Cr | Deleveraging + Momentum | — |
| 7 | **PONNIERODE** | MCAP | 74 | 100% | CONFIRMED | 86 | Rs1.51 Cr | Rs342 Cr | Momentum | — |
| 8 | **UGARSUGAR** | PRICE+MCAP | 74 | 100% | CONFIRMED | 88 | Rs4.25 Cr | Rs597 Cr | Hyper-growth + Deleveraging + Momentum | 1 |
| 9 | **DMCC** | MCAP | 74 | 100% | CONFIRMED | 75 | Rs1.38 Cr | Rs761 Cr | Hyper-growth + Momentum | — |
| 10 | **MGEL** | PRICE+MCAP | 73 | 100% | CONFIRMED | 85 | Rs2.22 Cr | Rs528 Cr | Hyper-growth + Momentum | — |
| 11 | **ANDHRSUGAR** | PRICE | 73 | 100% | WATCH | 81 | Rs4.44 Cr | Rs1275 Cr | Deleveraging | — |
| 12 | **KANPRPLA** | MCAP | 71 | 100% | CONFIRMED | 85 | Rs0.70 Cr | Rs650 Cr | Deleveraging + Momentum | — |
| 13 | **ORIENTBELL** | MCAP | 71 | 100% | CONFIRMED | 87 | Rs1.56 Cr | Rs591 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 14 | **UNIDT** | MCAP | 71 | 100% | CONFIRMED | 92 | Rs0.71 Cr | Rs447 Cr | Hyper-growth + Momentum | — |
| 15 | **HMAAGRO** | PRICE | 69 | 100% | WATCH | 41 | Rs4.61 Cr | Rs1157 Cr | Hyper-growth | 1 |
| 16 | **LAXMIINDIA** | MCAP | 69 | 100% | WATCH | 74 | Rs2.08 Cr | Rs665 Cr | Hyper-growth | — |
| 17 | **ARFIN** | PRICE | 69 | 100% | CONFIRMED | 93 | Rs8.89 Cr | Rs1504 Cr | Momentum | — |
| 18 | **MAWANASUG** | MCAP | 68 | 100% | CONFIRMED | 93 | Rs3.69 Cr | Rs502 Cr | Momentum | — |
| 19 | **KAMDHENU** | PRICE | 67 | 100% | CONFIRMED | 95 | Rs7.16 Cr | Rs1165 Cr | Hyper-growth + Momentum | — |
| 20 | **VISAKAIND** | PRICE+MCAP | 67 | 100% | CONFIRMED | 90 | Rs1.80 Cr | Rs756 Cr | Momentum | — |

## Vetoed (56) — capped at 25, momentum cannot outvote these

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
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
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
