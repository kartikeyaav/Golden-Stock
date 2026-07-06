# Marginal-value matrix — PIT fundamentals vs technical baseline

Window: entries 2023-08-01 onward; costs 0.15%/side; walk-forward cohorts split at 2025-01-01.

## A_technical_baseline
- positions: 108
- cagr_pct: 7.87
- max_dd_pct: -12.88
- blended: {'num_trades': 216, 'win_rate_pct': 27.78, 'avg_win_r': np.float64(6.66), 'avg_loss_r': np.float64(-0.8), 'payoff_ratio': np.float64(8.3), 'expectancy_r': np.float64(1.27), 'total_pnl': np.float64(733053.81), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 151, 'trend_break_50dma': 31, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 6}}
- core lot: {'num_trades': 108, 'win_rate_pct': 22.22, 'avg_win_r': np.float64(12.47), 'avg_loss_r': np.float64(-0.75), 'payoff_ratio': np.float64(16.58), 'expectancy_r': np.float64(2.186), 'total_pnl': np.float64(661663.11), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 76, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 4}, 'trades_ge_5r': 6}
- cohorts: {'P1_2023-08_to_2025-01': {'num_trades': 112, 'win_rate_pct': 38.39, 'payoff_ratio': np.float64(8.81), 'expectancy_r': np.float64(2.313), 'total_pnl': np.float64(752080.91)}, 'P2_2025-01_onward': {'num_trades': 104, 'win_rate_pct': 16.35, 'payoff_ratio': np.float64(6.28), 'expectancy_r': np.float64(0.147), 'total_pnl': np.float64(-19027.1)}}

## B1_pit_gate_failopen
- positions: 105
- cagr_pct: 2.17
- max_dd_pct: -12.2
- blended: {'num_trades': 210, 'win_rate_pct': 25.71, 'avg_win_r': np.float64(3.81), 'avg_loss_r': np.float64(-0.79), 'payoff_ratio': np.float64(4.8), 'expectancy_r': np.float64(0.391), 'total_pnl': np.float64(149425.35), 'best_trade_r': np.float64(26.4), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 149, 'trend_break_50dma': 30, 'weekly_close_below_30wk_ma': 25, 'backtest_end': 6}}
- core lot: {'num_trades': 105, 'win_rate_pct': 19.05, 'avg_win_r': np.float64(6.49), 'avg_loss_r': np.float64(-0.73), 'payoff_ratio': np.float64(8.9), 'expectancy_r': np.float64(0.646), 'total_pnl': np.float64(116236.22), 'best_trade_r': np.float64(26.4), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 76, 'weekly_close_below_30wk_ma': 25, 'backtest_end': 4}, 'trades_ge_5r': 5}
- cohorts: {'P1_2023-08_to_2025-01': {'num_trades': 120, 'win_rate_pct': 30.0, 'payoff_ratio': np.float64(4.1), 'expectancy_r': np.float64(0.437), 'total_pnl': np.float64(119880.1)}, 'P2_2025-01_onward': {'num_trades': 90, 'win_rate_pct': 20.0, 'payoff_ratio': np.float64(6.15), 'expectancy_r': np.float64(0.328), 'total_pnl': np.float64(29545.25)}}

## B2_pit_gate_failclosed
- positions: 104
- cagr_pct: 2.23
- max_dd_pct: -12.22
- blended: {'num_trades': 208, 'win_rate_pct': 25.48, 'avg_win_r': np.float64(3.87), 'avg_loss_r': np.float64(-0.8), 'payoff_ratio': np.float64(4.84), 'expectancy_r': np.float64(0.39), 'total_pnl': np.float64(154731.35), 'best_trade_r': np.float64(26.4), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 147, 'trend_break_50dma': 30, 'weekly_close_below_30wk_ma': 25, 'backtest_end': 6}}
- core lot: {'num_trades': 104, 'win_rate_pct': 19.23, 'avg_win_r': np.float64(6.49), 'avg_loss_r': np.float64(-0.74), 'payoff_ratio': np.float64(8.8), 'expectancy_r': np.float64(0.653), 'total_pnl': np.float64(122252.65), 'best_trade_r': np.float64(26.4), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 75, 'weekly_close_below_30wk_ma': 25, 'backtest_end': 4}, 'trades_ge_5r': 5}
- cohorts: {'P1_2023-08_to_2025-01': {'num_trades': 118, 'win_rate_pct': 29.66, 'payoff_ratio': np.float64(4.14), 'expectancy_r': np.float64(0.438), 'total_pnl': np.float64(124999.79)}, 'P2_2025-01_onward': {'num_trades': 90, 'win_rate_pct': 20.0, 'payoff_ratio': np.float64(6.15), 'expectancy_r': np.float64(0.328), 'total_pnl': np.float64(29731.56)}}

## B3_pit_gate_050
- positions: 110
- cagr_pct: 3.68
- max_dd_pct: -13.84
- blended: {'num_trades': 220, 'win_rate_pct': 25.0, 'avg_win_r': np.float64(4.61), 'avg_loss_r': np.float64(-0.82), 'payoff_ratio': np.float64(5.62), 'expectancy_r': np.float64(0.537), 'total_pnl': np.float64(283206.78), 'best_trade_r': np.float64(36.5), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 159, 'trend_break_50dma': 29, 'weekly_close_below_30wk_ma': 26, 'backtest_end': 6}}
- core lot: {'num_trades': 110, 'win_rate_pct': 19.09, 'avg_win_r': np.float64(8.03), 'avg_loss_r': np.float64(-0.77), 'payoff_ratio': np.float64(10.47), 'expectancy_r': np.float64(0.912), 'total_pnl': np.float64(257176.02), 'best_trade_r': np.float64(36.5), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 80, 'weekly_close_below_30wk_ma': 26, 'backtest_end': 4}, 'trades_ge_5r': 6}
- cohorts: {'P1_2023-08_to_2025-01': {'num_trades': 124, 'win_rate_pct': 29.84, 'payoff_ratio': np.float64(5.22), 'expectancy_r': np.float64(0.749), 'total_pnl': np.float64(261291.53)}, 'P2_2025-01_onward': {'num_trades': 96, 'win_rate_pct': 18.75, 'payoff_ratio': np.float64(6.19), 'expectancy_r': np.float64(0.263), 'total_pnl': np.float64(21915.25)}}

## D_pit_entry_ranking
- positions: 105
- cagr_pct: 1.97
- max_dd_pct: -12.18
- blended: {'num_trades': 210, 'win_rate_pct': 25.71, 'avg_win_r': np.float64(3.82), 'avg_loss_r': np.float64(-0.81), 'payoff_ratio': np.float64(4.73), 'expectancy_r': np.float64(0.382), 'total_pnl': np.float64(132652.57), 'best_trade_r': np.float64(26.4), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 149, 'trend_break_50dma': 30, 'weekly_close_below_30wk_ma': 25, 'backtest_end': 6}}
- core lot: {'num_trades': 105, 'win_rate_pct': 19.05, 'avg_win_r': np.float64(6.49), 'avg_loss_r': np.float64(-0.74), 'payoff_ratio': np.float64(8.76), 'expectancy_r': np.float64(0.637), 'total_pnl': np.float64(106339.78), 'best_trade_r': np.float64(26.4), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 76, 'weekly_close_below_30wk_ma': 25, 'backtest_end': 4}, 'trades_ge_5r': 5}
- cohorts: {'P1_2023-08_to_2025-01': {'num_trades': 120, 'win_rate_pct': 30.0, 'payoff_ratio': np.float64(3.99), 'expectancy_r': np.float64(0.421), 'total_pnl': np.float64(102472.48)}, 'P2_2025-01_onward': {'num_trades': 90, 'win_rate_pct': 20.0, 'payoff_ratio': np.float64(6.16), 'expectancy_r': np.float64(0.329), 'total_pnl': np.float64(30180.09)}}

## Reading rules (pre-registered)
- A config beats baseline only if expectancy improves in BOTH cohorts.
- P1-only improvement = fit to the bull phase -> reject.
- If B-variants trade far fewer positions, judge total P&L and
  drawdown alongside expectancy (a gate that only removes trades
  must remove BAD trades to earn its place).
- Survivor-bias caveat applies to every row equally; comparisons
  between configs are the point, absolute numbers are not.