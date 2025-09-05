import time
import logging
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from q_bot.connectors.mt5_adapter import MT5Adapter

log = logging.getLogger('Q.bot.DataLogger')

class DataLogger:
    """
    Handles the collection and saving of market data from MT5.
    """
    TIME_FRAMES_TO_LOG = {
        'M1': 1, 'M2': 2, 'M3': 3, 'M4': 4, 'M5': 5, 'M6': 6,
        'M10': 10, 'M12': 12, 'M15': 15, 'M20': 20, 'M30': 30, 'H1': 60
    }
    DATA_DIR = Path("q_bot/data")

    def __init__(self, mt5_adapter: MT5Adapter, symbol: str):
        self.adapter = mt5_adapter
        self.symbol = symbol
        self._running = False
        self.DATA_DIR.mkdir(exist_ok=True)

    def initial_backfill(self, num_bars=10000):
        log.info(f"Starting initial data backfill for {num_bars} bars...")
        for timeframe in self.TIME_FRAMES_TO_LOG.keys():
            log.info(f"Fetching data for {self.symbol} on {timeframe} timeframe...")
            df = self.adapter.get_rates(self.symbol, timeframe, num_bars)
            if not df.empty:
                file_path = self.DATA_DIR / f"{self.symbol}_{timeframe}.csv"
                df.to_csv(file_path, index=True, index_label='timestamp')
                log.info(f"Saved {len(df)} bars to {file_path}")
            else:
                log.warning(f"Could not fetch data for {timeframe}. Skipping.")
        log.info("Initial data backfill complete.")

    def _save_data_to_csv(self, df_row: pd.Series, timeframe: str):
        file_path = self.DATA_DIR / f"{self.symbol}_{timeframe}.csv"
        df_to_write = df_row.to_frame().T
        # File should exist after backfill, so we append without header
        df_to_write.to_csv(file_path, mode='a', header=False, index=True, index_label='timestamp')
        log.info(f"Appended 1 bar to {file_path}")

    def _collect_data(self, timeframe, interval_minutes):
        now = datetime.now(timezone.utc)
        if now.minute % interval_minutes == 0:
            log.info(f"Fetching data for {self.symbol} on {timeframe} timeframe...")
            rates_df = self.adapter.get_rates(self.symbol, timeframe, 2)
            if rates_df is not None and not rates_df.empty:
                latest_bar = rates_df.iloc[-1]
                # TODO: Add logic to ensure we don't save a duplicate bar
                self._save_data_to_csv(latest_bar, timeframe)
            else:
                log.warning(f"Could not fetch data for {timeframe}.")

    def run_continuous_logging(self):
        """
        Runs the continuous data logging loop in a blocking manner.
        """
        self._running = True
        log.info("Starting continuous data logging loop.")
        while self._running:
            try:
                sleep_time = 60 - datetime.now(timezone.utc).second
                log.debug(f"Logger sleeping for {sleep_time} seconds.")
                time.sleep(sleep_time)

                for tf, interval in self.TIME_FRAMES_TO_LOG.items():
                    self._collect_data(tf, interval)
            except Exception as e:
                log.error(f"Error in continuous logging loop: {e}")
                time.sleep(60) # Wait a minute before retrying after an error

    def stop(self):
        log.info("Stopping continuous data logger.")
        self._running = False
