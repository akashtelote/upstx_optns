import argparse
import logging
import sys
import backtrader as bt
import pandas as pd
from core.auth import authenticate_and_save_token
from tools.download_data import download_nifty_data
from core.smart_money import SmartMoneyFilter
from strategies.trend_strategy import TrendStrategy

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

    logger.info(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    cerebro.run()
    logger.info(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")

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

if __name__ == "__main__":
    main()
