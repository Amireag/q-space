import logging
import pandas as pd
from datetime import datetime

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
        self.magic_number = 12345 # A unique ID for trades placed by this bot

    def connect(self) -> bool:
        """
        Initializes the connection to the MetaTrader 5 terminal.
        """
        if mt5 is None:
            log.critical("Cannot connect: MetaTrader5 library is not installed.")
            return False

        if not mt5.initialize(login=self.config['account'], password=self.config['password'], server=self.config['server']):
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
        """
        if not self.connected: return pd.DataFrame()
        try:
            timeframe_map = {'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5, 'M15': mt5.TIMEFRAME_M15, 'H1': mt5.TIMEFRAME_H1} # Add others as needed
            mt5_timeframe = timeframe_map.get(timeframe_str, mt5.TIMEFRAME_M1)
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, num_bars)
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.rename(columns={'time': 'timestamp', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'tick_volume': 'volume'}, inplace=True)
            df.set_index('timestamp', inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            log.error(f"An exception occurred while fetching rates: {e}")
            return pd.DataFrame()

    def place_order(self, symbol, direction, volume, stop_loss, take_profit):
        """
        Places a market order on the MT5 terminal.
        """
        if not self.connected: return None

        order_type = mt5.ORDER_TYPE_BUY if direction == 'LONG' else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).ask if direction == 'LONG' else mt5.symbol_info_tick(symbol).bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "magic": self.magic_number,
            "comment": "Q.bot trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            log.error(f"Order send failed: {result.comment if result else 'No result'}, retcode={result.retcode if result else 'N/A'}")
            return None

        log.info(f"Order sent successfully: {result.order}")
        return result

    def get_open_positions(self):
        """
        Gets a list of open positions matching the bot's magic number.
        """
        if not self.connected: return []

        positions = mt5.positions_get(magic=self.magic_number)
        if positions is None:
            return []
        return list(positions)

    def close_position(self, position_id: int):
        """
        Closes an open position by its ticket ID.
        """
        if not self.connected: return False

        positions = mt5.positions_get(ticket=position_id)
        if not positions:
            log.error(f"Cannot close position. Position with ticket {position_id} not found.")
            return False

        position = positions[0]
        symbol = position.symbol
        volume = position.volume
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "magic": self.magic_number,
            "comment": "Q.bot close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            log.error(f"Close order failed: {result.comment if result else 'No result'}, retcode={result.retcode if result else 'N/A'}")
            return False

        log.info(f"Close order sent successfully for position {position_id}.")
        return True
