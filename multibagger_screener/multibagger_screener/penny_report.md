# Penny / nano-cap screen — 2026-10-01 11:32

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 190 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 82 | 100% | CONFIRMED | 90 | Rs1.66 Cr | Rs623 Cr | Hyper-growth + Momentum | — |
| 2 | **AVTNPL** | PRICE | 78 | 100% | CONFIRMED | 88 | Rs2.25 Cr | Rs1305 Cr | Hyper-growth + Momentum | — |
| 3 | **PREMIERPOL** | PRICE+MCAP | 76 | 100% | CONFIRMED | 93 | Rs2.53 Cr | Rs950 Cr | Momentum | — |
| 4 | **VETO** | MCAP | 76 | 100% | CONFIRMED | 87 | Rs1.71 Cr | Rs265 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 5 | **DMCC** | MCAP | 76 | 100% | CONFIRMED | 81 | Rs2.29 Cr | Rs761 Cr | Hyper-growth + Momentum | — |
| 6 | **PONNIERODE** | MCAP | 74 | 100% | CONFIRMED | 82 | Rs1.40 Cr | Rs342 Cr | Momentum | — |
| 7 | **ANDHRSUGAR** | PRICE | 72 | 100% | WATCH | 77 | Rs3.50 Cr | Rs1293 Cr | Deleveraging | — |
| 8 | **SYNCOMF** | PRICE | 72 | 100% | EXTENDED | 97 | Rs22.74 Cr | Rs1887 Cr | Deleveraging | — |
| 9 | **MANALIPETC** | PRICE | 72 | 100% | CONFIRMED | 92 | Rs14.14 Cr | Rs1346 Cr | Momentum | — |
| 10 | **MGEL** | PRICE+MCAP | 72 | 100% | CONFIRMED | 70 | Rs1.34 Cr | Rs528 Cr | Hyper-growth + Momentum | — |
| 11 | **UNIDT** | MCAP | 70 | 100% | CONFIRMED | 87 | Rs0.96 Cr | Rs487 Cr | Hyper-growth + Momentum | — |
| 12 | **LAXMIINDIA** | MCAP | 70 | 100% | WATCH | 73 | Rs1.74 Cr | Rs665 Cr | Hyper-growth | — |
| 13 | **KANPRPLA** | MCAP | 69 | 100% | CONFIRMED | 85 | Rs0.58 Cr | Rs622 Cr | Deleveraging + Momentum | — |
| 14 | **ORIENTBELL** | MCAP | 69 | 100% | CONFIRMED | 88 | Rs1.40 Cr | Rs580 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 15 | **HMAAGRO** | PRICE | 68 | 100% | WATCH | 33 | Rs4.54 Cr | Rs1178 Cr | Hyper-growth | 1 |
| 16 | **MAWANASUG** | MCAP | 68 | 100% | CONFIRMED | 89 | Rs3.65 Cr | Rs502 Cr | Momentum | — |
| 17 | **INDOAMIN** | MCAP | 68 | 100% | CONFIRMED | 83 | Rs6.58 Cr | Rs998 Cr | Momentum | — |
| 18 | **GLOBAL** | MCAP | 68 | 100% | EXTENDED | 94 | Rs2.23 Cr | Rs680 Cr | Hyper-growth | — |
| 19 | **SUBEXLTD** | PRICE | 68 | 100% | CONFIRMED | 100 | Rs20.43 Cr | Rs1096 Cr | Momentum | — |
| 20 | **NIITLTD** | PRICE | 67 | 100% | WATCH | 80 | Rs1.66 Cr | Rs1193 Cr | Deleveraging | — |

## Vetoed (55) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| SBC | promoter pledge 40.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 129% in 3 years — serial issuance di |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| SEPC | promoter pledge 79.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold; promoter holding only 11.67% and institutions hold ju |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| SCODATUBES | share capital up 5900% in 3 years — serial issuance dilutes every rupee of future earnings |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
