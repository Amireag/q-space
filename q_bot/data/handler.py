import logging
import pandas as pd
from q_bot.connectors.mt5_adapter import MT5Adapter

log = logging.getLogger('Q.bot')

class DataHandler:
    """
    Handles fetching and resampling of market data from the MT5Adapter.
    """
    TIMEFRAME_MAP = {
        'M1': 'M1', 'M2': 'M2', 'M3': 'M3', 'M4': 'M4', 'M5': 'M5',
        'M6': 'M6', 'M10': 'M10', 'M12': 'M12', 'M15': 'M15',
        'M20': 'M20', 'M30': 'M30', 'H1': 'H1'
    }

    # We need enough bars for the longest indicator (e.g., 200 EMA)
    BARS_TO_FETCH = 300

    def __init__(self, mt5_adapter: MT5Adapter, symbol: str):
        """
        Initializes the DataHandler.

        :param mt5_adapter: An instance of the MT5Adapter.
        :param symbol: The symbol of the instrument (e.g., 'EURUSD').
        """
        self.adapter = mt5_adapter
        self.symbol = symbol

    def get_resampled_data(self, timeframe_str: str) -> pd.DataFrame:
        """
        Gets historical data for the specified timeframe from the MT5 adapter.
        Note: The MT5 adapter gets data for a specific timeframe directly,
        so this method is now a pass-through and no longer does resampling.

        :param timeframe_str: The target timeframe (e.g., 'M5', 'H1').
        :return: A pandas DataFrame with the data.
        """
        if timeframe_str not in self.TIMEFRAME_MAP:
            log.error(f"Unsupported timeframe: {timeframe_str}")
            return pd.DataFrame()

        mt5_timeframe = self.TIMEFRAME_MAP[timeframe_str]

        log.debug(f"Fetching {self.BARS_TO_FETCH} bars for {self.symbol} on {mt5_timeframe} timeframe.")

        return self.adapter.get_rates(
            symbol=self.symbol,
            timeframe_str=mt5_timeframe,
            num_bars=self.BARS_TO_FETCH
        )

    def get_latest_bar(self, timeframe_str: str):
        """
        Gets the latest available bar for a given timeframe.

        :param timeframe_str: The timeframe to get the latest bar for.
        :return: A pandas Series representing the latest bar, or None.
        """
        data = self.get_resampled_data(timeframe_str)
        if data.empty:
            return None
        return data.iloc[-1]
