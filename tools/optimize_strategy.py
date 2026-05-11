import sys
import logging
import backtrader as bt
import pandas as pd
from strategies.trend_strategy import TrendStrategy

logger = logging.getLogger(__name__)

def run_optimization():
    logger.info('Optimization module initializing...')

    try:
        df = pd.read_parquet('data/nifty50_historical.parquet')
    except FileNotFoundError:
        logger.error("Historical data not found. Please run the 'download' command first: python main.py download")
        sys.exit(1)

    data = bt.feeds.PandasData(dataname=df)

    cerebro = bt.Cerebro(maxcpus=None, optreturn=False)
    cerebro.adddata(data)

    cerebro.optstrategy(
        TrendStrategy,
        fast_ma=range(5, 25, 5),
        slow_ma=range(20, 70, 10)
    )

    cerebro.broker.setcash(100000.0)

    # Position Sizer
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

    # Analyzers
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    logger.info("Starting strategy optimization...")
    results = cerebro.run()
    logger.info("Strategy optimization completed.")

    parsed_results = []

    for run in results:
        for strat in run:
            fast_ma = strat.params.fast_ma
            slow_ma = strat.params.slow_ma
            final_value = strat.broker.getvalue()

            trades_analyzer = strat.analyzers.trades.get_analysis()
            drawdown_analyzer = strat.analyzers.drawdown.get_analysis()

            total_closed = trades_analyzer.total.closed if 'total' in trades_analyzer and 'closed' in trades_analyzer.total else 0
            won_trades = trades_analyzer.won.total if 'won' in trades_analyzer and 'total' in trades_analyzer.won else 0
            max_drawdown = drawdown_analyzer.max.drawdown if 'max' in drawdown_analyzer and 'drawdown' in drawdown_analyzer.max else 0.0

            if total_closed > 0:
                win_rate = f"{(won_trades / total_closed * 100):.2f}%"
            else:
                win_rate = "N/A"

            parsed_results.append({
                'fast_ma': fast_ma,
                'slow_ma': slow_ma,
                'final_value': final_value,
                'win_rate': win_rate,
                'max_drawdown': max_drawdown
            })

    # Sort by Final Portfolio Value descending
    parsed_results.sort(key=lambda x: x['final_value'], reverse=True)

    logger.info("Top 5 Parameter Combinations:")
    for index, res in enumerate(parsed_results[:5], start=1):
        logger.info(f"Rank {index}: Fast MA={res['fast_ma']}, Slow MA={res['slow_ma']} | Final Value: ₹{res['final_value']:.2f} | Win Rate: {res['win_rate']} | Max DD: {res['max_drawdown']:.2f}%")
