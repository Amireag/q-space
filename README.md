# Q.bot - A Multi-Timeframe Forex Trading Bot

Q.bot is a sophisticated, event-driven trading bot designed for the EURUSD market. It operates on a multi-timeframe logic, incorporating a comprehensive set of technical indicators, risk management rules, and session timing to make trading decisions.

This version of the bot operates in a simulated environment, using historical data from a CSV file and a mock broker for trade execution.

## Core Features

- **Multi-Timeframe Analysis**: Utilizes 12 different timeframes (from M1 to H1) for signal generation.
- **Trend-Following Strategy**: Implements a detailed trend continuation strategy based on EMA alignment, pullbacks, and MACD triggers.
- **Robust Risk Management**: Features a `RiskManager` that enforces daily profit goals, drawdown stops, and a maximum number of trades per day.
- **Session & Compliance Management**: Restricts trading to specific high-liquidity sessions and ensures a flat book before the daily rollover to avoid swap fees.
- **Circuit Breakers**: Includes safeguards to pause trading in the event of broker order rejections.
- **External Configuration**: All bot parameters are managed via a centralized `settings.json` file for easy tuning.
- **Structured Logging**: All actions are logged to both the console and a `q_bot.log` file for detailed performance analysis and debugging.

## Project Structure

The project is organized into a modular structure to separate concerns and improve maintainability:

```
q_bot/
├── config/
│   └── settings.json       # All tunable parameters
├── core/
│   ├── engine.py           # The main trading engine and signal logic
│   └── models.py           # Data models for signals and positions
├── data/
│   ├── handler.py          # Handles loading and resampling of market data
│   └── EURUSD_M1.csv       # Sample M1 data
├── execution/
│   ├── broker.py           # Mock broker for simulated trading
│   └── manager.py          # Manages trade execution and position lifecycle
├── indicators/
│   └── technicals.py       # Calculates all technical indicators
├── risk/
│   └── rules.py            # The RiskManager class
├── utils/
│   ├── config.py           # Configuration loader
│   ├── logger.py           # Logging setup
│   └── time_utils.py       # Session and time management
└── main.py                 # The main entry point for the bot
```

## Setup and Installation

1.  **Clone the repository**:
    ```sh
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install dependencies**:
    Ensure you have Python 3.10+ installed. Then, install the required packages using pip:
    ```sh
    pip install -r requirements.txt
    ```

## Configuration

All bot parameters can be tuned in the `q_bot/config/settings.json` file. This includes risk settings, indicator parameters, session times, and more.

## How to Run

To run the bot, execute the `main.py` module from the root directory of the project:

```sh
python -m q_bot.main
```

The bot will start running, and you will see its activity logged to the console and to the `q_bot.log` file. To stop the bot, press `Ctrl+C`.
