"""
scripts/multibagger_radar.py — the whole-market multibagger radar.

WHY (the user's goal, 2026-09-26: "identify quality multibaggers early, with
multifold returns"). The 20-hypothesis study on the survivorship-free NSE
panel (PREREG_2026-09-26_multibagger_research.md, research/out/event_study.md)
found three signals that raised the chance of a stock tripling within a year
by >= 1.5x in BOTH 2005-2015 and 2016-2026:

  power play   (H7)  up 90%+ within 40 sessions with no pullback deeper than 25%,
                     closing at a new high (often the surge itself, as coded and
                     measured — not only the classic flag breakout after it)
  RS leader    (H9)  6- AND 12-month return both in the top 10% of the market
  discovery    (H14) traded value rising from the market's bottom half to its
                     top quarter within 60 sessions

and that the system's own VCP breakout barely moves that chance. Multibaggers
are born mostly among smaller names the live price cache does not hold, so the
radar does not use the cache: it rebuilds the WHOLE market's last ~14 months
from NSE's own daily files every night (~300 files, a minute or two), adjusts
splits/bonuses the same way the research panel does, and applies the research
code (research/hypotheses.py) unchanged — the measured signal and the live one
cannot drift apart.

It is a research signal under forward test, not a buy instruction: even the
best of them was followed by a triple only ~1 time in 10.

    python scripts/multibagger_radar.py            # build + scan -> state/multibagger_radar.json
    python scripts/multibagger_radar.py --no-build # scan the existing recent panel
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data import nse_history as H  # noqa: E402

LOOKBACK_DAYS = 800            # calendar days -> ~540 sessions: the 2-year breakout in the
                               # value signal needs 500 prior closes (the universe needs 250)
RADAR_PANEL = H.HIST_DIR / "panel_recent.npz"
STATE = os.path.join(ROOT, "state", "multibagger_radar.json")
STUDY = os.path.join(ROOT, "research", "out", "event_study.json")
ACTIVE_WINDOW = 10             # a signal stays on the radar for 10 sessions after it fires
SIGNALS = {"H7": "power play", "H9": "RS leader", "H14": "discovery", "H20": "value breakout",
           "H25": "promoter buying + momentum"}
INSIDER_STUDY = os.path.join(ROOT, "research", "out", "insider_study.json")
INSIDER_ARCHIVE = os.path.join(ROOT, "insider_archive.csv")
FUND_STUDY = os.path.join(ROOT, "research", "out", "fundamental_study.json")
VALUE_TABLE = os.path.join(ROOT, "value_fundamentals.csv")


def latest_session(today: date, probes: int = 7) -> date | None:
    """The most recent session NSE has published a bhavcopy for (a local file,
    or one HEAD-sized fetch per day walking back). None when nothing answers."""
    d = today
    for _ in range(probes):
        if H.bhav_path(d).exists():
            return d
        status, _blob = H._get(H.bhav_url(d), H._Gate())
        if status == "ok":
            return d
        d -= timedelta(days=1)
    return None


def already_current(today: date) -> bool:
    """daily.yml runs up to six catch-up slots a day; only the first one that
    finds a new session should download ~300 exchange files."""
    try:
        with open(STATE, encoding="utf-8") as f:
            asof = json.load(f).get("asof")
    except (OSError, ValueError):
        return False
    last = latest_session(today)
    return bool(asof and last and asof >= str(last))


def build_recent(today: date) -> None:
    start = today - timedelta(days=LOOKBACK_DAYS)
    H.download(start, today, workers=4, kinds=("bhav",))
    H.build(start=start, end=today, out=RADAR_PANEL)


def research_stats() -> dict:
    """Confirmation-period (2016-2026) numbers for each signal, from the
    committed event study — shown beside every name so a flag is never read
    as a promise."""
    try:
        with open(STUDY, encoding="utf-8") as f:
            res = json.load(f)["results"]
    except (OSError, ValueError, KeyError):
        return {}
    for extra in (FUND_STUDY, INSIDER_STUDY):
        try:
            with open(extra, encoding="utf-8") as f:
                res.update(json.load(f)["results"])
        except (OSError, ValueError, KeyError):
            pass
    out = {}
    for key in SIGNALS:
        name = next((n for n in res if n.split()[0] == key), None)
        c = (res.get(name) or {}).get("confirmation") or {}
        mb = c.get("MB3_1y") or {}
        r12 = c.get("r252") or {}
        out[key] = {"tripled_within_1y_pct": mb.get("rate"), "universe_pct": mb.get("base"),
                    "lift": mb.get("lift"), "events": c.get("n"),
                    "median_12m_pct": r12.get("median")}
    return out


def scan(g) -> dict:
    from research.grid import xrank
    from research.hypotheses import h7_power_play, h9_rs_leader, h14_discovery
    U = g.universe()
    t = g.T - 1
    lo = max(0, t - ACTIVE_WINDOW + 1)
    raw = {"H7": h7_power_play(g) & U, "H9": h9_rs_leader(g) & U, "H14": h14_discovery(g) & U}
    # H20, cheap + new uptrend (PREREG_2026-09-27_value_breakout.md): the SAME
    # computation as the research (parity checked: zero cells differ), from
    # the committed annual table the weekly job refreshes
    if os.path.exists(VALUE_TABLE):
        import pandas as pd
        from research import fundamentals as F
        from research.hypotheses import h2_multi_year_base_breakout, h5_stage2_start
        fg = F.grids_from_table(g, pd.read_csv(VALUE_TABLE))
        raw["H20"] = F.h20_cheap_new_uptrend(g, fg, h2_multi_year_base_breakout(g), h5_stage2_start(g)) & U
    # H25, a promoter market purchase in the prior 60 sessions + an RS leader or
    # trend-template pass (PREREG_2026-09-27_promoter_buying.md, the survivor):
    # the research function itself, on the committed insider archive
    insider_asof = None
    if os.path.exists(INSIDER_ARCHIVE):
        import pandas as pd
        from data.nse_history import _symbol_chain
        from research.insider_study import h25_grid
        tr = pd.read_csv(INSIDER_ARCHIVE, parse_dates=["disclosed_at"])
        if len(tr):
            chain = _symbol_chain()
            tr["symbol"] = tr["symbol"].astype(str).str.strip().map(lambda s: chain.get(s, s))
            raw["H25"] = h25_grid(g, tr) & U
            insider_asof = str(tr["disclosed_at"].max())[:16]
    # the research EVENT: the first firing per stock per 120 sessions
    # (research/event_study.DEDUPE). A persistent state — an RS leader stays in
    # the top 10% for months — is one event on the day it began, not a fresh
    # signal every day; that is exactly what was measured.
    import pandas as pd
    from research.event_study import DEDUPE
    fired = {}
    for k, gsig in raw.items():
        prior = pd.DataFrame(gsig.astype("float32")).shift(1).rolling(DEDUPE, min_periods=1).max()
        fired[k] = gsig & ~(prior.to_numpy() > 0)
    rs6 = xrank(g.ret(126), U)
    hi52 = np.nanmax(g.c[max(0, t - 249):t + 1], axis=0)
    rows = []
    for j in range(g.N):
        sigs = {}
        for k, grid in fired.items():
            hits = np.nonzero(grid[lo:t + 1, j])[0]
            if len(hits):
                sigs[k] = str(g.dates[lo + hits[-1]].date())
        if not sigs or not U[t, j]:
            continue
        c = float(g.c[t, j])
        rows.append({
            "sym": g.symbols[j].split("~")[0], "signals": sigs,
            "fresh": any(v == str(g.dates[t].date()) for v in sigs.values()),
            "close": round(c, 2),
            "ret_6m_pct": round(float(g.ret(126)[t, j]) * 100, 1) if np.isfinite(g.ret(126)[t, j]) else None,
            "ret_12m_pct": round(float(g.ret(250)[t, j]) * 100, 1) if np.isfinite(g.ret(250)[t, j]) else None,
            "rs_pct": round(float(rs6[t, j]) * 100, 1) if np.isfinite(rs6[t, j]) else None,
            "off_52w_high_pct": round((c / float(hi52[j]) - 1) * 100, 1) if np.isfinite(hi52[j]) else None,
            "traded_value_cr": round(float(np.nanmedian(g.tv[max(0, t - 19):t + 1, j])) / 1e7, 2),
        })
    rows.sort(key=lambda r: (-len(r["signals"]), -(r["rs_pct"] or 0)))
    # the liquid universe tonight: the weekly fundamentals refresh
    # (scripts/value_fundamentals.py) keeps exactly these companies current
    uni = sorted({g.symbols[j].split("~")[0] for j in np.nonzero(U[t])[0]})
    return {"asof": str(g.dates[t].date()), "universe_size": int(U[t].sum()), "rows": rows,
            "universe": uni, "insider_asof": insider_asof}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-build", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    if not a.no_build:
        if already_current(date.today()):
            print("radar already current for the latest session — nothing to do")
            return 0
        build_recent(date.today())
    from research.grid import load_grid
    g = load_grid(path=RADAR_PANEL)
    out = scan(g)
    out.update(generated=datetime.now().strftime("%Y-%m-%d %H:%M"), signals=SIGNALS,
               research=research_stats(), window_sessions=ACTIVE_WINDOW,
               note=("Signals that raised the odds of a stock tripling within a year in both halves "
                     "of 2005-2026 on the survivorship-free NSE panel. Even the best one was followed "
                     "by a triple roughly 1 time in 10: a watchlist to research, not a buy list."))
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    by = {k: sum(1 for r in out["rows"] if k in r["signals"]) for k in SIGNALS}
    print(f"radar {out['asof']}: {len(out['rows'])} names on the radar (universe {out['universe_size']}); "
          f"{by}; fresh today {sum(r['fresh'] for r in out['rows'])} ({time.time() - t0:.0f}s)")
    for r in out["rows"][:12]:
        print(f"  {r['sym']:12} {','.join(SIGNALS[k] for k in r['signals']):32} 6m {r['ret_6m_pct']}% "
              f"RS {r['rs_pct']} off-high {r['off_52w_high_pct']}% value Rs{r['traded_value_cr']}cr")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
