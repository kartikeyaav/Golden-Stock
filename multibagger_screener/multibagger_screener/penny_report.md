# Penny / nano-cap screen — 2026-09-28 11:34

**Research surface. Zero capital. Not backtested.** The main system's
evidence (+1.67R, walk-forward, 13 rejected overlays) says nothing about
this screen. Every name below is journaled to `journal/penny_journal.csv`
so the question 'does this add anything?' gets an out-of-sample answer
instead of an argument.

Universe: 192 names that survived the hard tradability gates
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
| 1 | **PASUPTAC** | PRICE+MCAP | 82 | 100% | CONFIRMED | 93 | Rs1.89 Cr | Rs605 Cr | Hyper-growth + Momentum | — |
| 2 | **MANALIPETC** | PRICE | 77 | 100% | CONFIRMED | 93 | Rs14.14 Cr | Rs1413 Cr | Momentum | — |
| 3 | **VETO** | MCAP | 77 | 100% | CONFIRMED | 88 | Rs3.56 Cr | Rs265 Cr | Hyper-growth + Deleveraging + Momentum | — |
| 4 | **PREMIERPOL** | PRICE+MCAP | 77 | 100% | CONFIRMED | 97 | Rs2.41 Cr | Rs857 Cr | Momentum | — |
| 5 | **ANDHRSUGAR** | PRICE | 77 | 100% | CONFIRMED | 82 | Rs4.33 Cr | Rs1293 Cr | Deleveraging + Momentum | — |
| 6 | **AVTNPL** | PRICE | 77 | 100% | CONFIRMED | 86 | Rs1.97 Cr | Rs1305 Cr | Hyper-growth + Momentum | — |
| 7 | **PONNIERODE** | MCAP | 75 | 100% | CONFIRMED | 87 | Rs1.51 Cr | Rs342 Cr | Momentum | — |
| 8 | **UGARSUGAR** | PRICE+MCAP | 74 | 100% | CONFIRMED | 92 | Rs4.25 Cr | Rs597 Cr | Hyper-growth + Deleveraging + Momentum | 1 |
| 9 | **DMCC** | MCAP | 74 | 100% | CONFIRMED | 78 | Rs1.81 Cr | Rs761 Cr | Hyper-growth + Momentum | — |
| 10 | **SYNCOMF** | PRICE | 73 | 100% | EXTENDED | 94 | Rs20.36 Cr | Rs1887 Cr | Deleveraging | — |
| 11 | **MGEL** | PRICE+MCAP | 73 | 100% | CONFIRMED | 73 | Rs2.22 Cr | Rs528 Cr | Hyper-growth + Momentum | — |
| 12 | **ORIENTBELL** | MCAP | 70 | 100% | CONFIRMED | 86 | Rs1.40 Cr | Rs580 Cr | Turnaround (margin-confirmed) + Momentum | — |
| 13 | **KANPRPLA** | MCAP | 70 | 100% | CONFIRMED | 83 | Rs0.62 Cr | Rs622 Cr | Deleveraging + Momentum | — |
| 14 | **MAWANASUG** | MCAP | 70 | 100% | CONFIRMED | 95 | Rs3.69 Cr | Rs502 Cr | Momentum | — |
| 15 | **GLOBAL** | MCAP | 70 | 100% | CONFIRMED | 94 | Rs2.23 Cr | Rs680 Cr | Hyper-growth + Momentum | — |
| 16 | **LAXMIINDIA** | MCAP | 70 | 100% | WATCH | 67 | Rs1.99 Cr | Rs665 Cr | Hyper-growth | — |
| 17 | **HMAAGRO** | PRICE | 70 | 100% | WATCH | 40 | Rs4.96 Cr | Rs1157 Cr | Hyper-growth | 1 |
| 18 | **UNIDT** | MCAP | 69 | 100% | CONFIRMED | 81 | Rs0.86 Cr | Rs447 Cr | Hyper-growth + Momentum | — |
| 19 | **SUBEXLTD** | PRICE | 68 | 100% | CONFIRMED | 100 | Rs17.84 Cr | Rs1107 Cr | Momentum | — |
| 20 | **NIITLTD** | PRICE | 68 | 100% | WATCH | 78 | Rs2.53 Cr | Rs1193 Cr | Deleveraging | — |

## Vetoed (56) — capped at 25, momentum cannot outvote these

| Symbol | Reason |
|--------|--------|
| MOTISONS | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BAJAJHIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 91% in 3 years — serial issuance di |
| SBC | promoter pledge 40.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 129% in 3 years — serial issuance di |
| CONFIPET | promoter pledge 41.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JTLIND | share capital up 129% in 3 years — serial issuance dilutes every rupee of future earnings |
| ASIANTILES | share capital up 133% in 3 years — serial issuance dilutes every rupee of future earnings |
| UTKARSHBNK | share capital up 99% in 3 years — serial issuance dilutes every rupee of future earnings |
| PARACABLES | share capital up 56% in 3 years — serial issuance dilutes every rupee of future earnings |
| GRMOVER | share capital up 242% in 3 years — serial issuance dilutes every rupee of future earnings |
| EASEMYTRIP | share capital up 109% in 3 years — serial issuance dilutes every rupee of future earnings |
| SMCGLOBAL | share capital up 100% in 3 years — serial issuance dilutes every rupee of future earnings |
| JISLJALEQS | promoter pledge 40.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| TEMBO | promoter pledge 40.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 73% in 3 years — serial issuance dil |
| STEELXIND | promoter pledge 100.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| PATELENG | promoter pledge 86.6% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| ONEPOINT | promoter pledge 36.0% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| JYOTISTRUC | share capital up 88% in 3 years — serial issuance dilutes every rupee of future earnings |
| NITCO | promoter pledge 67.1% (> 10%) — the lender, not the promoter, decides when this stock gets sold; share capital up 235% in 3 years — serial issuance di |
| IRISDOREME | share capital up 138% in 3 years — serial issuance dilutes every rupee of future earnings |
| HITECH | share capital up 54% in 3 years — serial issuance dilutes every rupee of future earnings |
| BLKASHYAP | promoter pledge 94.4% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MCLOUD | promoter pledge 46.8% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| MSPL | promoter pledge 63.5% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| WANBURY | promoter pledge 62.2% (> 10%) — the lender, not the promoter, decides when this stock gets sold |
| DENTA | share capital up 440% in 3 years — serial issuance dilutes every rupee of future earnings |

---

### What would make this trustworthy
A pre-registered backtest of this screen on the penny universe, run
through `backtest/engine.py` with the same two-lot rules and costs,
compared against the technical-only baseline. Until that exists these
are ideas with a liquidity check, not signals.
