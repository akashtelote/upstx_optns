import argparse
import logging
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import backtrader as bt
import pandas as pd
from core.auth import authenticate_and_save_token
from tools.download_data import download_nifty_data
from core.smart_money import SmartMoneyFilter
from strategies.trend_strategy import TrendStrategy
from tools.optimize_strategy import run_optimization
from core.client import UpstoxClient
from core.scheduler import start_scheduler

# Basic logging configuration for all core modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

def run_backtest():
    """Run the Backtrader backtest logic."""
    logger.info('Backtesting module initializing...')

    try:
        df = pd.read_parquet('data/nifty50_historical.parquet')
    except FileNotFoundError:
        logger.error("Historical data not found. Please run the 'download' command first: python main.py download")
        sys.exit(1)

    data = bt.feeds.PandasData(dataname=df)

    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(TrendStrategy)

    cerebro.broker.setcash(100000.0)

    # Position Sizer
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

    # Analyzers
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    logger.info(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    logger.info(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")

    # Extract metrics
    strat = results[0]
    trades_analyzer = strat.analyzers.trades.get_analysis()
    drawdown_analyzer = strat.analyzers.drawdown.get_analysis()

    total_open = trades_analyzer.total.open if 'total' in trades_analyzer and 'open' in trades_analyzer.total else 0
    total_closed = trades_analyzer.total.closed if 'total' in trades_analyzer and 'closed' in trades_analyzer.total else 0
    won_trades = trades_analyzer.won.total if 'won' in trades_analyzer and 'total' in trades_analyzer.won else 0
    max_drawdown = drawdown_analyzer.max.drawdown if 'max' in drawdown_analyzer and 'drawdown' in drawdown_analyzer.max else 0.0

    if total_closed > 0:
        win_rate = f"{(won_trades / total_closed * 100):.2f}%"
    else:
        win_rate = "N/A"

    logger.info(f"Total Open Trades: {total_open}")
    logger.info(f"Total Closed Trades: {total_closed}")
    logger.info(f"Win Rate: {win_rate}")
    logger.info(f"Maximum Drawdown: {max_drawdown:.2f}%")

    # Save visual chart to data/ directory
    try:
        figs = cerebro.plot(style='candlestick', barup='green', bardown='red')
        if figs and len(figs) > 0 and len(figs[0]) > 0:
            figs[0][0].savefig('data/backtest_chart.png')
            logger.info("Saved backtest chart to data/backtest_chart.png")
    except Exception as e:
        logger.warning(f"Could not save backtest chart due to upstream dependency compatibility: {e}")

def run_trade(args):
    """Run a simulated paper trade or live trade."""
    if args.live:
        logger.warning("WARNING: INITIATING LIVE EXCHANGE ORDER!")
    else:
        logger.info(f"Initiating paper trade for {args.quantity} shares of {args.symbol} at ₹{args.price}...")

    client = UpstoxClient()
    order_id = client.place_order(args.symbol, args.side, args.quantity, args.price, is_live=args.live)

    if order_id:
        if args.live:
            logger.info(f"Successfully routed LIVE trade. Upstox Order ID: {order_id}")
        else:
            logger.info(f"Successfully routed PAPER trade. Mock Order ID: {order_id}")

def main():
    parser = argparse.ArgumentParser(description="Indian Trading Bot - Unified CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    subparsers.required = True

    # Subcommand: auth
    auth_parser = subparsers.add_parser("auth", help="Generate or refresh the Upstox API token")

    # Subcommand: download
    download_parser = subparsers.add_parser("download", help="Download historical Nifty data")
    download_parser.add_argument(
        "--start",
        type=str,
        default="2015-01-01",
        help="Start date for data download (YYYY-MM-DD)"
    )
    download_parser.add_argument(
        "--format",
        type=str,
        default="parquet",
        choices=["parquet", "csv"],
        help="Output format (parquet or csv)"
    )

    # Subcommand: screen
    screen_parser = subparsers.add_parser("screen", help="Run the Smart Money Filter to find institutional whales")

    # Subcommand: backtest
    backtest_parser = subparsers.add_parser("backtest", help="Run backtesting strategy")

    # Subcommand: optimize
    optimize_parser = subparsers.add_parser("optimize", help="Optimize backtesting strategy parameters")

    # Subcommand: trade
    trade_parser = subparsers.add_parser("trade", help="Run a simulated paper trade or live trade")
    trade_parser.add_argument("symbol", type=str, help="Trading symbol (e.g., RELIANCE)")
    trade_parser.add_argument("side", type=str, choices=["BUY", "SELL"], help="Order side (BUY/SELL)")
    trade_parser.add_argument("quantity", type=int, help="Quantity to trade")
    trade_parser.add_argument("price", type=float, help="Order price")
    trade_parser.add_argument("--live", action="store_true", help="Execute a REAL trade on the Upstox exchange")

    # Subcommand: start
    start_parser = subparsers.add_parser("start", help="Start the daily scheduler")
    start_parser.add_argument("--live", action="store_true", help="Run the scheduled bot in REAL live trading mode")

    args = parser.parse_args()

    if args.command == "auth":
        logger.info("Executing auth command...")
        authenticate_and_save_token()
    elif args.command == "download":
        logger.info("Executing download command...")
        download_nifty_data(start_date=args.start, output_format=args.format)
    elif args.command == "screen":
        logger.info("Executing screen command...")
        filter = SmartMoneyFilter()
        filter.process_smart_money()
    elif args.command == "backtest":
        logger.info("Executing backtest command...")
        run_backtest()
    elif args.command == "optimize":
        logger.info("Executing optimize command...")
        run_optimization()
    elif args.command == "trade":
        logger.info("Executing trade command...")
        run_trade(args)
    elif args.command == "start":
        logger.info("Executing start command...")
        start_scheduler(args.live)

if __name__ == "__main__":
    main()
