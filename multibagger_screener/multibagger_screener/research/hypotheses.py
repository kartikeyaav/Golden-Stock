"""
research/hypotheses.py — H1..H17 of PREREG_2026-09-26_multibagger_research.md,
coded exactly as registered. Each returns a bool grid (sessions x companies):
True where the signal FIRES at t's close, using only data up to t.

H18..H20 (fundamental) live in research/fundamentals.py: they need data the
price panel does not have, and they carry a survivorship caveat these do not.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.grid import Grid, roll, shift, xrank


def _b(x) -> np.ndarray:
    return np.nan_to_num(x, nan=0.0).astype(bool) if x.dtype != bool else x


# ---------------------------------------------------------------------------
# price and trend
# ---------------------------------------------------------------------------

def h1_new_52w_high(g: Grid) -> np.ndarray:
    return _b(g.c > g.hmax_prior(250))


def h2_multi_year_base_breakout(g: Grid) -> np.ndarray:
    return _b(g.c > g.hmax_prior(500))


def h3_all_time_high(g: Grid) -> np.ndarray:
    cm = np.fmax.accumulate(np.nan_to_num(g.c, nan=-np.inf), axis=0)
    prior = shift(cm.astype("float32"), 1)
    return _b((g.c > prior) & (g.history() >= 750))


def h4_trend_template(g: Grid) -> np.ndarray:
    s50, s150, s200 = g.sma(50), g.sma(150), g.sma(200)
    lo52 = roll(g.c, 250, "min")
    hi52 = roll(g.c, 250, "max")
    r6 = xrank(g.ret(126), g.universe())
    ok = ((g.c > s50) & (s50 > s150) & (s150 > s200) & (s200 > shift(s200, 20))
          & (g.c >= 1.3 * lo52) & (g.c >= 0.75 * hi52) & (r6 >= 0.70))
    return _b(ok)


def h5_stage2_start(g: Grid) -> np.ndarray:
    s150 = g.sma(150)                                   # the 30-week average
    flat_before = shift(s150, 5) <= shift(s150, 135) * 1.02
    turning_up = s150 > shift(s150, 5)
    return _b(flat_before & turning_up & (g.c > s150))


def h6_vcp_breakout(g: Grid) -> np.ndarray:
    rng = roll(g.h, 20, "max") / roll(g.l, 20, "min") - 1          # 20-day range
    at_low = rng <= roll(rng, 250, "min", minp=200) * 1.0001
    recent_low = roll(at_low.astype("float32"), 10, "max", minp=1) > 0
    hi50 = shift(roll(g.h, 50, "max"), 1)
    return _b(shift(recent_low.astype("float32"), 1).astype(bool)
              & (g.c > hi50) & (g.v >= 1.5 * g.vavg(50)))


def h7_power_play(g: Grid) -> np.ndarray:
    # the run: some close in the prior 25 sessions stood >= 90% above the lowest
    # close of the 40 sessions before it (+90% in <= 40 sessions)
    run = g.c / roll(g.c, 40, "min")
    ran = shift(roll(run, 25, "max"), 1) >= 1.9
    # the flag: over those 25 sessions no close fell > 25% below its trailing peak
    dd = g.c / roll(g.c, 25, "max")
    tight = shift(roll(dd, 25, "min"), 1) >= 0.75
    flag_hi = shift(roll(g.c, 25, "max"), 1)
    return _b(ran & tight & (g.c > flag_hi))


def h8_episodic_pivot(g: Grid) -> np.ndarray:
    prev_c = shift(g.c, 1)
    return _b((g.o >= 1.08 * prev_c) & (g.c >= g.o) & (g.v >= 3 * g.vavg(50)))


def h9_rs_leader(g: Grid) -> np.ndarray:
    U = g.universe()
    return _b((xrank(g.ret(126), U) >= 0.90) & (xrank(g.ret(250), U) >= 0.90))


def h10_near_52w_high(g: Grid) -> np.ndarray:
    return _b(g.c >= 0.95 * roll(g.c, 250, "max"))


# ---------------------------------------------------------------------------
# volume and smart money
# ---------------------------------------------------------------------------

def h11_volume_surge(g: Grid) -> np.ndarray:
    v20 = roll(g.v, 20, "mean", minp=15)
    v200_prior = shift(roll(g.v, 200, "mean", minp=150), 20)
    return _b((v20 >= 3 * v200_prior) & (g.ret(20) > 0))


def h12_delivery_accumulation(g: Grid) -> np.ndarray:
    dval = g.dq * g.c                                    # delivered value
    d20 = roll(dval, 20, "mean", minp=15)
    d200 = roll(dval, 200, "mean", minp=150)
    with np.errstate(divide="ignore", invalid="ignore"):
        dp = g.dq / g.v
    dp20 = roll(dp, 20, "mean", minp=15)
    dp200 = roll(dp, 200, "mean", minp=150)
    return _b((d20 >= 2 * d200) & (dp20 > dp200))


def h13_up_down_volume(g: Grid) -> np.ndarray:
    up = g.c > shift(g.c, 1)
    dn = g.c < shift(g.c, 1)
    vu = roll(np.where(up, g.v, 0).astype("float32"), 50, "sum", minp=40)
    vd = roll(np.where(dn, g.v, 0).astype("float32"), 50, "sum", minp=40)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = vu / vd
    return _b(ratio >= 1.8)


def h14_discovery(g: Grid) -> np.ndarray:
    med = roll(g.tv, 60, "median", minp=30)
    # rank across every listed stock (not only the universe: the point is a
    # stock that was NOT liquid enough to matter becoming one that is)
    listed = ~np.isnan(g.c) & (g.history() >= 250)
    r = xrank(med, listed)
    return _b((shift(r, 60) < 0.5) & (r >= 0.75))


# ---------------------------------------------------------------------------
# ICT / smart-money concepts, mechanical, on WEEKLY bars
# ---------------------------------------------------------------------------

def _weekly(g: Grid):
    """Weekly OHLC (Friday weeks) and the daily row of each week's last session."""
    wk = g.dates.to_period("W-FRI")
    codes, uniq = pd.factorize(wk)
    last_row = pd.Series(np.arange(g.T)).groupby(codes).max().to_numpy()
    first_row = pd.Series(np.arange(g.T)).groupby(codes).min().to_numpy()
    O = pd.DataFrame(g.o).groupby(codes).first().to_numpy(dtype="float32")
    H = pd.DataFrame(g.h).groupby(codes).max().to_numpy(dtype="float32")
    L = pd.DataFrame(g.l).groupby(codes).min().to_numpy(dtype="float32")
    C = pd.DataFrame(g.c).groupby(codes).last().to_numpy(dtype="float32")
    return O, H, L, C, last_row, first_row


def _to_daily(g: Grid, weekly_sig: np.ndarray, last_row: np.ndarray) -> np.ndarray:
    out = np.zeros((g.T, g.N), dtype=bool)
    out[last_row] = weekly_sig
    return out


def _first_within(trigger: np.ndarray, armed_at: np.ndarray, window: int) -> np.ndarray:
    """True at w if `trigger` holds at w and an arming event happened in the
    `window` weeks before w, and no trigger fired since that arming event.
    Column-wise loop over weeks (weekly grids are small)."""
    W, N = trigger.shape
    out = np.zeros_like(trigger, dtype=bool)
    since = np.full(N, 10**9)            # weeks since last arming
    for w in range(W):
        since = np.where(armed_at[w], 0, since + 1)
        fire = trigger[w] & (since >= 1) & (since <= window)
        out[w] = fire
        since = np.where(fire, 10**9, since)      # disarm after firing once
    return out


def h15_sweep_and_shift(g: Grid) -> np.ndarray:
    O, H, L, C, last_row, _ = _weekly(g)
    lo26 = shift(roll(L, 26, "min"), 1)
    sweep = (L < lo26) & (C > lo26)
    level = roll(H, 5, "max")                        # swing high at the sweep week
    # carry the level forward from the most recent sweep
    lvl = pd.DataFrame(np.where(sweep, level, np.nan)).ffill().to_numpy(dtype="float32")
    trig = C > shift(lvl, 1)
    return _to_daily(g, _first_within(_b(trig), _b(sweep), 8), last_row)


def h16_fair_value_gap(g: Grid) -> np.ndarray:
    O, H, L, C, last_row, _ = _weekly(g)
    disp = (shift(C, 1) / shift(O, 1) - 1) >= 0.15     # the middle bar is the displacement
    gap = L > shift(H, 2)
    fvg = _b(disp & gap)
    top = pd.DataFrame(np.where(fvg, L, np.nan)).ffill().to_numpy(dtype="float32")
    bot = pd.DataFrame(np.where(fvg, shift(H, 2), np.nan)).ffill().to_numpy(dtype="float32")
    retest = (L <= shift(top, 1)) & (C >= shift(bot, 1))
    return _to_daily(g, _first_within(_b(retest), fvg, 26), last_row)


def h17_order_block(g: Grid) -> np.ndarray:
    O, H, L, C, last_row, _ = _weekly(g)
    down = C < O
    disp_after = (shift(C, -2) / C - 1) >= 0.20        # the 2 weeks AFTER a down week
    # an order block is only KNOWN two weeks later, once the displacement printed
    ob_known = shift((down & (disp_after >= 1)).astype("float32"), 2) > 0
    ob_hi = pd.DataFrame(np.where(ob_known, shift(H, 2), np.nan)).ffill().to_numpy(dtype="float32")
    ob_lo = pd.DataFrame(np.where(ob_known, shift(L, 2), np.nan)).ffill().to_numpy(dtype="float32")
    retest = (L <= shift(ob_hi, 1)) & (C >= shift(ob_lo, 1))
    return _to_daily(g, _first_within(_b(retest), ob_known, 26), last_row)


HYPOTHESES = {
    "H1 new 52-week high": h1_new_52w_high,
    "H2 2-year base breakout": h2_multi_year_base_breakout,
    "H3 all-time high": h3_all_time_high,
    "H4 trend template": h4_trend_template,
    "H5 stage-2 start": h5_stage2_start,
    "H6 volatility-contraction breakout": h6_vcp_breakout,
    "H7 power play": h7_power_play,
    "H8 episodic pivot": h8_episodic_pivot,
    "H9 RS leader": h9_rs_leader,
    "H10 near 52-week high": h10_near_52w_high,
    "H11 volume surge": h11_volume_surge,
    "H12 delivery accumulation": h12_delivery_accumulation,
    "H13 up/down volume": h13_up_down_volume,
    "H14 discovery": h14_discovery,
    "H15 ICT sweep + structure shift": h15_sweep_and_shift,
    "H16 ICT fair-value gap": h16_fair_value_gap,
    "H17 ICT order block": h17_order_block,
}
