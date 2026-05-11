import backtrader as bt
from strategies.base_strategy import BaseStrategy

class TrendStrategy(BaseStrategy):
    params = (
        ('fast_ma', 10),
        ('slow_ma', 50),
        ('rsi_period', 14),
        ('trail_percent', 0.02),
    )

    def __init__(self):
        super().__init__()

        self.order = None

        self.fast_ma = bt.indicators.SMA(period=self.p.fast_ma)
        self.slow_ma = bt.indicators.SMA(period=self.p.slow_ma)
        self.rsi = bt.indicators.RSI_SMA(period=self.p.rsi_period, safediv=True)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if self.order or self.position:
            return

        if self.crossover[0] > 0 and self.rsi[0] > 50:
            self.order = self.buy(transmit=False)
            self.sell(
                exectype=bt.Order.StopTrail,
                trailpercent=self.p.trail_percent,
                parent=self.order,
                transmit=True
            )

    def notify_order(self, order):
        super().notify_order(order)

        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            if order == self.order:
                self.order = None
