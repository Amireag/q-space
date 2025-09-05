import logging
import pandas as pd
from datetime import datetime

# The MetaTrader5 library is only available on Windows.
# This code is written to its API and must be run on a Windows machine
# with the MT5 terminal installed and running.
try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 library not found. This module can only be run on Windows with MT5 installed.")
    mt5 = None

log = logging.getLogger('Q.bot')

class MT5Adapter:
    """
    Handles all interactions with the MetaTrader 5 terminal.
    """
    def __init__(self, config: dict):
        self.config = config
        self.connected = False

    def connect(self) -> bool:
        """
        Initializes the connection to the MetaTrader 5 terminal.
        """
        if mt5 is None:
            log.critical("Cannot connect: MetaTrader5 library is not installed.")
            return False

        if not mt5.initialize(
            login=self.config['account'],
            password=self.config['password'],
            server=self.config['server']
        ):
            log.critical(f"MT5 initialize() failed, error code = {mt5.last_error()}")
            return False

        log.info("MT5 connection initialized successfully.")
        self.connected = True
        return True

    def disconnect(self):
        """
        Shuts down the connection to the MetaTrader 5 terminal.
        """
        if self.connected and mt5:
            mt5.shutdown()
            log.info("MT5 connection shut down.")
        self.connected = False

    def get_rates(self, symbol: str, timeframe_str: str, num_bars: int) -> pd.DataFrame:
        """
        Fetches historical OHLCV data from the MT5 terminal.

        :param symbol: The symbol to fetch data for (e.g., "EURUSD").
        :param timeframe_str: The MT5 timeframe constant (e.g., "M1", "H1").
        :param num_bars: The number of bars to fetch.
        :return: A pandas DataFrame with the OHLCV data, or an empty DataFrame on failure.
        """
        if not self.connected or not mt5:
            log.error("Cannot fetch rates: not connected to MT5.")
            return pd.DataFrame()

        try:
            # Map our timeframe strings to MT5 constants
            timeframe_map = {
                'M1': mt5.TIMEFRAME_M1, 'M2': mt5.TIMEFRAME_M2, 'M3': mt5.TIMEFRAME_M3,
                'M4': mt5.TIMEFRAME_M4, 'M5': mt5.TIMEFRAME_M5, 'M6': mt5.TIMEFRAME_M6,
                'M10': mt5.TIMEFRAME_M10, 'M12': mt5.TIMEFRAME_M12, 'M15': mt5.TIMEFRAME_M15,
                'M20': mt5.TIMEFRAME_M20, 'M30': mt5.TIMEFRAME_M30, 'H1': mt5.TIMEFRAME_H1
            }
            mt5_timeframe = timeframe_map.get(timeframe_str)
            if mt5_timeframe is None:
                log.error(f"Unsupported timeframe string: {timeframe_str}")
                return pd.DataFrame()

            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, num_bars)
            if rates is None:
                log.error(f"Failed to get rates for {symbol} on {timeframe_str}, error = {mt5.last_error()}")
                return pd.DataFrame()

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.rename(columns={
                'time': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume'
            }, inplace=True)
            df.set_index('timestamp', inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            log.error(f"An exception occurred while fetching rates: {e}")
            return pd.DataFrame()

    def place_order(self, symbol, direction, volume, stop_loss, take_profit):
        """
        Places a trade order on the MT5 terminal.
        (Placeholder - requires careful implementation and testing)
        """
        log.info(f"--- MT5 ADAPTER: Would place {direction} order for {volume} lots of {symbol} ---")
        # In a real implementation, this would use mt5.order_send()
        # and handle the request dictionary and result object carefully.
        return True # Simulate successful order placement

    def close_position(self, position_id):
        """
        Closes an open position on the MT5 terminal.
        (Placeholder)
        """
        log.info(f"--- MT5 ADAPTER: Would close position {position_id} ---")
        return True

    def get_open_positions(self):
        """
        Gets a list of open positions from the MT5 terminal.
        (Placeholder)
        """
        log.info("--- MT5 ADAPTER: Would fetch open positions ---")
        return []
