import time
import logging
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from q_bot.connectors.mt5_adapter import MT5Adapter
from q_bot.utils.config import load_config
from q_bot.utils.logger import setup_logging

log = logging.getLogger('Q.bot.DataLogger')

# Define the timeframes we want to log
TIME_FRAMES_TO_LOG = {
    'M1': 1, 'M2': 2, 'M3': 3, 'M4': 4, 'M5': 5, 'M6': 6,
    'M10': 10, 'M12': 12, 'M15': 15, 'M20': 20, 'M30': 30, 'H1': 60
}
DATA_DIR = Path("data")

def save_data_to_csv(df_row: pd.Series, symbol: str, timeframe: str):
    """
    Appends a single row of data to the appropriate CSV file.
    """
    file_path = DATA_DIR / f"{symbol}_{timeframe}.csv"
    df_to_write = df_row.to_frame().T
    write_header = not file_path.exists()

    # Add index_label to ensure the timestamp column has a header
    df_to_write.to_csv(file_path, mode='a', header=write_header, index=True, index_label='timestamp')
    log.info(f"Saved 1 bar to {file_path}")

def collect_data(adapter, symbol, timeframe, interval_minutes):
    """
    Fetches the latest bar for a given timeframe and saves it to CSV.
    """
    now = datetime.now(timezone.utc)
    if now.minute % interval_minutes == 0:
        log.info(f"Fetching data for {symbol} on {timeframe} timeframe...")
        rates_df = adapter.get_rates(symbol, timeframe, 2)
        if not rates_df.empty:
            latest_bar = rates_df.iloc[-1]
            save_data_to_csv(latest_bar, symbol, timeframe)
        else:
            log.warning(f"Could not fetch data for {timeframe}.")

def main():
    """
    The main function for the Data Logger.
    """
    setup_logging()
    DATA_DIR.mkdir(exist_ok=True)
    log.info("--- Starting Data Logger ---")

    config = load_config('q_bot/config/settings.json')
    if not config: return

    mt5_conf = config['mt5_settings']
    bot_conf = config['bot_settings']
    symbol = bot_conf['symbol']

    mt5_adapter = MT5Adapter(config=mt5_conf)
    if not mt5_adapter.connect(): return

    log.info("Successfully connected to MT5. Starting data collection loop.")

    try:
        while True:
            # Use timezone-aware datetime objects
            sleep_time = 60 - datetime.now(timezone.utc).second
            log.debug(f"Sleeping for {sleep_time} seconds until the next minute.")
            time.sleep(sleep_time)

            for tf, interval in TIME_FRAMES_TO_LOG.items():
                collect_data(mt5_adapter, symbol, tf, interval)

    except KeyboardInterrupt:
        log.info("Stopping Data Logger.")
    finally:
        mt5_adapter.disconnect()
        log.info("--- Data Logger Stopped ---")


if __name__ == "__main__":
    main()
