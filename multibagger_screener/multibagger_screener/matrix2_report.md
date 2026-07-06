# Matrix v2 — sector heat, core-lot modulation, execution stress

## A_baseline
- positions: 108
- blended: {'num_trades': 216, 'win_rate_pct': 27.78, 'avg_win_r': np.float64(6.66), 'avg_loss_r': np.float64(-0.8), 'payoff_ratio': np.float64(8.3), 'expectancy_r': np.float64(1.27), 'total_pnl': np.float64(733053.81), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 151, 'trend_break_50dma': 31, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 6}}
- core lot: {'num_trades': 108, 'win_rate_pct': 22.22, 'avg_win_r': np.float64(12.47), 'avg_loss_r': np.float64(-0.75), 'payoff_ratio': np.float64(16.58), 'expectancy_r': np.float64(2.186), 'total_pnl': np.float64(661663.11), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 76, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 4}, 'trades_ge_5r': 6}
- cohorts: {'P1': {'num_trades': 112, 'win_rate_pct': 38.39, 'payoff_ratio': np.float64(8.81), 'expectancy_r': np.float64(2.313), 'total_pnl': np.float64(752080.91)}, 'P2': {'num_trades': 104, 'win_rate_pct': 16.35, 'payoff_ratio': np.float64(6.28), 'expectancy_r': np.float64(0.147), 'total_pnl': np.float64(-19027.1)}}
- equity (window): {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1765464.78), 'total_return_pct': np.float64(76.55), 'cagr_pct': np.float64(21.48), 'max_drawdown_pct': np.float64(-12.88)}

## E40_sector_heat
- positions: 113
- blended: {'num_trades': 226, 'win_rate_pct': 25.22, 'avg_win_r': np.float64(3.34), 'avg_loss_r': np.float64(-0.84), 'payoff_ratio': np.float64(3.99), 'expectancy_r': np.float64(0.216), 'total_pnl': np.float64(173760.72), 'best_trade_r': np.float64(36.5), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 164, 'trend_break_50dma': 29, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 5}}
- core lot: {'num_trades': 113, 'win_rate_pct': 20.35, 'avg_win_r': np.float64(5.1), 'avg_loss_r': np.float64(-0.78), 'payoff_ratio': np.float64(6.51), 'expectancy_r': np.float64(0.414), 'total_pnl': np.float64(171163.02), 'best_trade_r': np.float64(36.5), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 82, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 3}, 'trades_ge_5r': 3}
- cohorts: {'P1': {'num_trades': 130, 'win_rate_pct': 30.77, 'payoff_ratio': np.float64(3.61), 'expectancy_r': np.float64(0.384), 'total_pnl': np.float64(223656.12)}, 'P2': {'num_trades': 96, 'win_rate_pct': 17.71, 'payoff_ratio': np.float64(4.57), 'expectancy_r': np.float64(-0.01), 'total_pnl': np.float64(-49895.4)}}
- equity (window): {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1200939.88), 'total_return_pct': np.float64(20.09), 'cagr_pct': np.float64(6.47), 'max_drawdown_pct': np.float64(-15.01)}

## E60_sector_heat
- positions: 106
- blended: {'num_trades': 212, 'win_rate_pct': 19.81, 'avg_win_r': np.float64(3.89), 'avg_loss_r': np.float64(-0.83), 'payoff_ratio': np.float64(4.68), 'expectancy_r': np.float64(0.105), 'total_pnl': np.float64(26516.09), 'best_trade_r': np.float64(36.5), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 166, 'trend_break_50dma': 23, 'weekly_close_below_30wk_ma': 21, 'backtest_end': 2}}
- core lot: {'num_trades': 106, 'win_rate_pct': 16.04, 'avg_win_r': np.float64(6.36), 'avg_loss_r': np.float64(-0.79), 'payoff_ratio': np.float64(8.05), 'expectancy_r': np.float64(0.356), 'total_pnl': np.float64(93132.97), 'best_trade_r': np.float64(36.5), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 84, 'weekly_close_below_30wk_ma': 21, 'backtest_end': 1}, 'trades_ge_5r': 5}
- cohorts: {'P1': {'num_trades': 132, 'win_rate_pct': 21.97, 'payoff_ratio': np.float64(5.49), 'expectancy_r': np.float64(0.368), 'total_pnl': np.float64(146654.85)}, 'P2': {'num_trades': 80, 'win_rate_pct': 16.25, 'payoff_ratio': np.float64(2.54), 'expectancy_r': np.float64(-0.331), 'total_pnl': np.float64(-120138.76)}}
- equity (window): {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1052203.3), 'total_return_pct': np.float64(5.22), 'cagr_pct': np.float64(1.76), 'max_drawdown_pct': np.float64(-21.13)}

## F1_core_patience
- positions: 106
- blended: {'num_trades': 212, 'win_rate_pct': 27.83, 'avg_win_r': np.float64(6.54), 'avg_loss_r': np.float64(-0.79), 'payoff_ratio': np.float64(8.26), 'expectancy_r': np.float64(1.248), 'total_pnl': np.float64(704185.47), 'best_trade_r': np.float64(143.58), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 152, 'trend_break_50dma': 31, 'weekly_close_below_30wk_ma': 23, 'backtest_end': 6}}
- core lot: {'num_trades': 106, 'win_rate_pct': 21.7, 'avg_win_r': np.float64(12.4), 'avg_loss_r': np.float64(-0.74), 'payoff_ratio': np.float64(16.85), 'expectancy_r': np.float64(2.115), 'total_pnl': np.float64(625575.92), 'best_trade_r': np.float64(143.58), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 79, 'weekly_close_below_30wk_ma': 23, 'backtest_end': 4}, 'trades_ge_5r': 6}
- cohorts: {'P1': {'num_trades': 110, 'win_rate_pct': 38.18, 'payoff_ratio': np.float64(8.92), 'expectancy_r': np.float64(2.254), 'total_pnl': np.float64(717758.23)}, 'P2': {'num_trades': 102, 'win_rate_pct': 16.67, 'payoff_ratio': np.float64(6.26), 'expectancy_r': np.float64(0.163), 'total_pnl': np.float64(-13572.76)}}
- equity (window): {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1735606.23), 'total_return_pct': np.float64(73.56), 'cagr_pct': np.float64(20.77), 'max_drawdown_pct': np.float64(-13.16)}

## F2_fund_split
- positions: 108
- blended: {'num_trades': 216, 'win_rate_pct': 27.78, 'avg_win_r': np.float64(6.66), 'avg_loss_r': np.float64(-0.8), 'payoff_ratio': np.float64(8.3), 'expectancy_r': np.float64(1.271), 'total_pnl': np.float64(587854.93), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 151, 'trend_break_50dma': 31, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 6}}
- core lot: {'num_trades': 108, 'win_rate_pct': 22.22, 'avg_win_r': np.float64(12.47), 'avg_loss_r': np.float64(-0.75), 'payoff_ratio': np.float64(16.58), 'expectancy_r': np.float64(2.186), 'total_pnl': np.float64(481809.04), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 76, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 4}, 'trades_ge_5r': 6}
- cohorts: {'P1': {'num_trades': 112, 'win_rate_pct': 38.39, 'payoff_ratio': np.float64(8.82), 'expectancy_r': np.float64(2.315), 'total_pnl': np.float64(609161.67)}, 'P2': {'num_trades': 104, 'win_rate_pct': 16.35, 'payoff_ratio': np.float64(6.28), 'expectancy_r': np.float64(0.147), 'total_pnl': np.float64(-21306.74)}}
- equity (window): {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1619060.04), 'total_return_pct': np.float64(61.91), 'cagr_pct': np.float64(17.93), 'max_drawdown_pct': np.float64(-13.22)}

## S1_next_open_fill
- positions: 111
- blended: {'num_trades': 222, 'win_rate_pct': 23.87, 'avg_win_r': np.float64(6.54), 'avg_loss_r': np.float64(-0.8), 'payoff_ratio': np.float64(8.22), 'expectancy_r': np.float64(0.955), 'total_pnl': np.float64(533397.16), 'best_trade_r': np.float64(126.39), 'worst_trade_r': np.float64(-1.07), 'exit_reason_breakdown': {'stop_loss': 163, 'trend_break_50dma': 28, 'weekly_close_below_30wk_ma': 25, 'backtest_end': 6}}
- core lot: {'num_trades': 111, 'win_rate_pct': 18.02, 'avg_win_r': np.float64(13.17), 'avg_loss_r': np.float64(-0.75), 'payoff_ratio': np.float64(17.56), 'expectancy_r': np.float64(1.758), 'total_pnl': np.float64(527725.37), 'best_trade_r': np.float64(126.39), 'worst_trade_r': np.float64(-1.07), 'exit_reason_breakdown': {'stop_loss': 82, 'weekly_close_below_30wk_ma': 25, 'backtest_end': 4}, 'trades_ge_5r': 7}
- cohorts: {'P1': {'num_trades': 112, 'win_rate_pct': 33.04, 'payoff_ratio': np.float64(9.27), 'expectancy_r': np.float64(1.959), 'total_pnl': np.float64(626053.99)}, 'P2': {'num_trades': 110, 'win_rate_pct': 14.55, 'payoff_ratio': np.float64(5.27), 'expectancy_r': np.float64(-0.068), 'total_pnl': np.float64(-92656.83)}}
- equity (window): {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1566359.85), 'total_return_pct': np.float64(56.64), 'cagr_pct': np.float64(16.6), 'max_drawdown_pct': np.float64(-14.59)}

## S3_gap_aware_stops
- positions: 108
- blended: {'num_trades': 216, 'win_rate_pct': 27.78, 'avg_win_r': np.float64(6.66), 'avg_loss_r': np.float64(-0.86), 'payoff_ratio': np.float64(7.75), 'expectancy_r': np.float64(1.228), 'total_pnl': np.float64(695524.52), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-5.2), 'exit_reason_breakdown': {'stop_loss': 151, 'trend_break_50dma': 31, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 6}}
- core lot: {'num_trades': 108, 'win_rate_pct': 22.22, 'avg_win_r': np.float64(12.47), 'avg_loss_r': np.float64(-0.8), 'payoff_ratio': np.float64(15.49), 'expectancy_r': np.float64(2.145), 'total_pnl': np.float64(641537.31), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-5.2), 'exit_reason_breakdown': {'stop_loss': 76, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 4}, 'trades_ge_5r': 6}
- cohorts: {'P1': {'num_trades': 112, 'win_rate_pct': 38.39, 'payoff_ratio': np.float64(7.64), 'expectancy_r': np.float64(2.233), 'total_pnl': np.float64(714314.92)}, 'P2': {'num_trades': 104, 'win_rate_pct': 16.35, 'payoff_ratio': np.float64(6.27), 'expectancy_r': np.float64(0.146), 'total_pnl': np.float64(-18790.41)}}
- equity (window): {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1727376.25), 'total_return_pct': np.float64(72.74), 'cagr_pct': np.float64(20.58), 'max_drawdown_pct': np.float64(-12.89)}

## S2_heavy_costs_0.40 (derived from A)
- blended: {'num_trades': 216, 'win_rate_pct': 26.39, 'avg_win_r': np.float64(6.93), 'avg_loss_r': np.float64(-0.85), 'payoff_ratio': np.float64(8.16), 'expectancy_r': np.float64(1.203), 'total_pnl': np.float64(679035.52), 'best_trade_r': np.float64(146.69), 'worst_trade_r': np.float64(-1.17), 'exit_reason_breakdown': {'stop_loss': 151, 'trend_break_50dma': 31, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 6}}

## Pre-registered reading rules
- E: improve expectancy in BOTH cohorts or reject.
- F1/F2: judged on core-lot stats; blended must not degrade materially.
- S1/S2/S3: baseline must stay > +0.5R under every stress.
- Survivor bias applies equally to all rows; compare, don't worship.