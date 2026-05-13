# Indian Stock Market Trading Bot

## Project Overview

This project is a fully autonomous algorithmic trading bot designed specifically for Cash Equities Delivery (Swing Trading) on the National Stock Exchange (NSE). It integrates with the Upstox v2 API for real-time and historical market data, as well as order execution. The core trading logic executes a 10/50 Simple Moving Average (SMA) crossover strategy on daily charts to identify and capture medium-term market trends.

## Architecture Highlights

The trading bot's architecture is modular, scalable, and built for reliability:

*   **Unified CLI (`main.py`)**: A single entry point powered by `argparse` that manages the entire lifecycle of the bot, from data downloading and backtesting to live execution.
*   **Self-healing API Client (`core/client.py`)**: A robust Upstox API client that handles automatic token refreshing and API interactions, ensuring uninterrupted operation during live trading sessions.
*   **Automated Daily Execution (`core/scheduler.py`)**: Utilizes APScheduler to run the bot autonomously at scheduled intervals, analyzing the market and executing trades at optimal times.

## Prerequisites & Setup

The project uses `uv` for lightning-fast Python dependency management.

1.  **Install dependencies**:
    Make sure you have `uv` installed, then synchronize the environment:
    ```bash
    uv sync
    ```

2.  **Initial Authentication**:
    Before running any data or trading commands, you must authenticate with the Upstox API. This generates an access token that is saved for subsequent requests.
    ```bash
    uv run main.py auth
    ```
    This will create a `data/token.json` file.

## Usage Commands

The bot features a unified CLI to manage all phases of trading.

### Data Preparation
*   **Download Historical Data**:
    Download historical Nifty data for analysis.
    ```bash
    uv run main.py download --start 2015-01-01 --format parquet
    ```
*   **Screen Stocks**:
    Run the Smart Money Filter to identify potential institutional activity.
    ```bash
    uv run main.py screen
    ```

### Strategy Development
*   **Backtest Strategy**:
    Run a simulation of the 10/50 SMA crossover strategy against historical data.
    ```bash
    uv run main.py backtest
    ```
*   **Optimize Strategy Parameters**:
    Find the optimal parameters for your trading strategy.
    ```bash
    uv run main.py optimize
    ```

### Execution
*   **Manual Trading**:
    Execute a single trade for a specific symbol.
    ```bash
    uv run main.py trade <symbol> <side> <quantity> <price>
    ```
    *Example: `uv run main.py trade RELIANCE BUY 10 2500`*
    *   **Paper Mode**: By default, this command runs a simulated (paper) trade.
    *   **Live Mode**: Append the `--live` flag to execute a REAL order on the Upstox exchange.
*   **Start the Autonomous Bot**:
    Launch the scheduler for automated daily execution.
    ```bash
    uv run main.py start
    ```
    *   The bot uses a daily cron trigger scheduled for **15:15 IST** to evaluate the daily charts just before the market closes.
    *   Like the `trade` command, it runs in paper mode by default. Use the `--live` flag for real automated trading.

## Deployment Note

All persistent state—including the authentication token (`token.json`), the cached instrument list (`nse_instruments.csv`), downloaded data, and charts—is saved within the `data/` directory.

When deploying the bot in a headless or containerized environment (e.g., Docker), you can simply mount the `data/` directory as a volume. This ensures your authentication tokens and cached data persist across container restarts, making the bot resilient and easy to maintain.
