import backtrader as bt
import logging
import datetime
import os

class BaseStrategy(bt.Strategy):
    """
    Base Strategy class that includes standardized logging for order execution
    and trade results, with dynamic log file generation.
    """

    def __init__(self):
        super().__init__()

        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)

        # Setup dynamic logging configuration
        strategy_name = self.__class__.__name__
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"logs/backtest_{strategy_name}_{timestamp}.log"

        # Create a unique logger for this strategy instance
        self.logger = logging.getLogger(f"{strategy_name}_{id(self)}")
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers if any
        self.logger.handlers.clear()

        # Create file handler
        fh = logging.FileHandler(log_filename)
        fh.setLevel(logging.INFO)

        # Formatter: just the message, since we include the simulated timestamp in the log method
        formatter = logging.Formatter('%(message)s')
        fh.setFormatter(formatter)

        self.logger.addHandler(fh)

        # Prevent propagation to the root logger to avoid duplicate console output
        self.logger.propagate = False

    def log(self, txt, dt=None):
        """
        Utility method for subclasses to log messages with ISO-formatted simulated timestamps.
        """
        if dt is None:
            try:
                # Simulated time from data feed
                dt = self.datas[0].datetime.datetime(0)
            except IndexError:
                # Fallback if datas is not populated or index is out of bounds
                dt = datetime.datetime.now()

        if isinstance(dt, datetime.datetime) or isinstance(dt, datetime.date):
            dt_str = dt.isoformat()
        else:
            dt_str = str(dt)

        self.logger.info(f"[{dt_str}] {txt}")

    def notify_order(self, order):
        """
        Handles order executions and logs standard information.
        """
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker
            return

        if order.status in [order.Completed]:
            action = 'BUY' if order.isbuy() else 'SELL'
            asset_name = order.data._name if hasattr(order.data, '_name') and order.data._name else 'Unknown'
            size = order.executed.size
            price = order.executed.price
            cost = order.executed.value
            commission = order.executed.comm

            self.log(f"{action} EXECUTED, Asset: {asset_name}, Size: {size}, Price: {price:.2f}, Cost: {cost:.2f}, Commission: {commission:.2f}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            action = 'BUY' if order.isbuy() else 'SELL'
            asset_name = order.data._name if hasattr(order.data, '_name') and order.data._name else 'Unknown'
            status_str = 'Canceled' if order.status == order.Canceled else 'Margin' if order.status == order.Margin else 'Rejected'
            self.log(f"{action} ORDER {status_str}, Asset: {asset_name}")

    def notify_trade(self, trade):
        """
        Handles closed trades and logs standardized performance information.
        """
        if not trade.isclosed:
            return

        asset_name = trade.data._name if hasattr(trade.data, '_name') and trade.data._name else 'Unknown'
        gross_pnl = trade.pnl
        net_pnl = trade.pnlcomm
        duration = trade.barlen

        self.log(f"TRADE CLOSED, Asset: {asset_name}, Gross PnL: {gross_pnl:.2f}, Net PnL: {net_pnl:.2f}, Duration: {duration} bars")
