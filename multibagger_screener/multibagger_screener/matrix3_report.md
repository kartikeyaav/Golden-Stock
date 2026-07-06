# Matrix v3 — anticipation tier + regime sizing

## A_baseline_ref
- positions: 108
- blended: {'num_trades': 216, 'win_rate_pct': 27.78, 'avg_win_r': np.float64(6.66), 'avg_loss_r': np.float64(-0.8), 'payoff_ratio': np.float64(8.3), 'expectancy_r': np.float64(1.27), 'total_pnl': np.float64(733053.81), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 151, 'trend_break_50dma': 31, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 6}}
- core: {'num_trades': 108, 'win_rate_pct': 22.22, 'avg_win_r': np.float64(12.47), 'avg_loss_r': np.float64(-0.75), 'payoff_ratio': np.float64(16.58), 'expectancy_r': np.float64(2.186), 'total_pnl': np.float64(661663.11), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 76, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 4}, 'trades_ge_5r': 6}
- cohorts: {'P1': {'num_trades': 112, 'expectancy_r': np.float64(2.313), 'win_rate_pct': 38.39}, 'P2': {'num_trades': 104, 'expectancy_r': np.float64(0.147), 'win_rate_pct': 16.35}}
- equity: {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1765464.78), 'total_return_pct': np.float64(76.55), 'cagr_pct': np.float64(21.48), 'max_drawdown_pct': np.float64(-12.88)}

## V3a_anticipation_fund
- positions: 133
- blended: {'num_trades': 266, 'win_rate_pct': 40.6, 'avg_win_r': np.float64(1.97), 'avg_loss_r': np.float64(-0.66), 'payoff_ratio': np.float64(3.01), 'expectancy_r': np.float64(0.412), 'total_pnl': np.float64(348037.7), 'best_trade_r': np.float64(18.8), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'weekly_close_below_30wk_ma': 105, 'stop_loss': 103, 'trend_break_50dma': 43, 'backtest_end': 15}}
- core: {'num_trades': 133, 'win_rate_pct': 42.11, 'avg_win_r': np.float64(1.21), 'avg_loss_r': np.float64(-0.43), 'payoff_ratio': np.float64(2.8), 'expectancy_r': np.float64(0.26), 'total_pnl': np.float64(109775.08), 'best_trade_r': np.float64(10.97), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'weekly_close_below_30wk_ma': 105, 'stop_loss': 23, 'backtest_end': 5}, 'trades_ge_5r': 5}
- cohorts: {'P1': {'num_trades': 124, 'expectancy_r': np.float64(0.815), 'win_rate_pct': 47.58}, 'P2': {'num_trades': 142, 'expectancy_r': np.float64(0.06), 'win_rate_pct': 34.51}}
- equity: {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1384430.88), 'total_return_pct': np.float64(38.44), 'cagr_pct': np.float64(11.78), 'max_drawdown_pct': np.float64(-9.82)}

## V3a_anticipation_priceonly
- positions: 167
- blended: {'num_trades': 334, 'win_rate_pct': 32.34, 'avg_win_r': np.float64(1.53), 'avg_loss_r': np.float64(-0.65), 'payoff_ratio': np.float64(2.36), 'expectancy_r': np.float64(0.056), 'total_pnl': np.float64(19480.0), 'best_trade_r': np.float64(16.96), 'worst_trade_r': np.float64(-1.07), 'exit_reason_breakdown': {'stop_loss': 150, 'weekly_close_below_30wk_ma': 127, 'trend_break_50dma': 41, 'backtest_end': 16}}
- core: {'num_trades': 167, 'win_rate_pct': 34.13, 'avg_win_r': np.float64(1.09), 'avg_loss_r': np.float64(-0.44), 'payoff_ratio': np.float64(2.46), 'expectancy_r': np.float64(0.08), 'total_pnl': np.float64(21466.18), 'best_trade_r': np.float64(16.96), 'worst_trade_r': np.float64(-1.07), 'exit_reason_breakdown': {'weekly_close_below_30wk_ma': 127, 'stop_loss': 35, 'backtest_end': 5}, 'trades_ge_5r': 4}
- cohorts: {'P1': {'num_trades': 154, 'expectancy_r': np.float64(0.262), 'win_rate_pct': 33.12}, 'P2': {'num_trades': 180, 'expectancy_r': np.float64(-0.121), 'win_rate_pct': 31.67}}
- equity: {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1058668.96), 'total_return_pct': np.float64(5.87), 'cagr_pct': np.float64(1.97), 'max_drawdown_pct': np.float64(-17.18)}

## V3b_regime_sized
- positions: 108
- blended: {'num_trades': 216, 'win_rate_pct': 27.78, 'avg_win_r': np.float64(6.66), 'avg_loss_r': np.float64(-0.8), 'payoff_ratio': np.float64(8.3), 'expectancy_r': np.float64(1.271), 'total_pnl': np.float64(777296.18), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 151, 'trend_break_50dma': 31, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 6}}
- core: {'num_trades': 108, 'win_rate_pct': 22.22, 'avg_win_r': np.float64(12.47), 'avg_loss_r': np.float64(-0.75), 'payoff_ratio': np.float64(16.58), 'expectancy_r': np.float64(2.186), 'total_pnl': np.float64(686135.53), 'best_trade_r': np.float64(147.13), 'worst_trade_r': np.float64(-1.06), 'exit_reason_breakdown': {'stop_loss': 76, 'weekly_close_below_30wk_ma': 28, 'backtest_end': 4}, 'trades_ge_5r': 6}
- cohorts: {'P1': {'num_trades': 112, 'expectancy_r': np.float64(2.313), 'win_rate_pct': 38.39}, 'P2': {'num_trades': 104, 'expectancy_r': np.float64(0.148), 'win_rate_pct': 16.35}}
- equity: {'start_date': Timestamp('2023-08-01 00:00:00'), 'end_date': Timestamp('2026-07-03 00:00:00'), 'years': 2.92, 'starting_equity': 1000000, 'ending_equity': np.float64(1807299.32), 'total_return_pct': np.float64(80.73), 'cagr_pct': np.float64(22.46), 'max_drawdown_pct': np.float64(-12.37)}

## Pre-registered reading rules
- V3a-F earns the anticipation tier capital ONLY if expectancy is
  positive in both cohorts AND beats V3a-P (fundamentals must add
  value over price-only anticipation).
- V3b judged on drawdown + Sharpe-like smoothness vs baseline;
  it trades CAGR for safety by design.
- Structural caveat: core exits fire fast near a flat 30wMA —
  declared before running.