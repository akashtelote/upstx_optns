# Indian Stock Market Trading Bot

This project is an automated trading bot for the Indian Stock Market, integrating with the Upstox API for data and execution.

## Roadmap

The development of this trading bot is structured into four main phases:

### Phase 1: Setup & Data Foundation
* Project initialization with `uv`.
* Upstox API authentication via TOTP.
* Establishing a unified Data Manager for historical and real-time data.

### Phase 2: Screening & Analysis
* Building a technical screener (RSI, SMA, MACD).
* Implementing a News & Sentiment engine for stock filtering.

### Phase 3: Backtesting & Probability
* Implementing a strategy simulation module using `backtrader`.
* Tracking performance stats like Win Rate and Profit Factor.

### Phase 4: Execution & Reporting
* Integrating Paper Trading and Live Order execution with Upstox.
* Including P&L and Brokerage calculators.
