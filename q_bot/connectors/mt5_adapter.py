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
        self.symbol = config.get('symbol', 'EURUSD') # Get symbol from config
        self.connected = False
        self.magic_number = 12345

    def connect(self) -> bool:
        if mt5 is None:
            log.critical("Cannot connect: MetaTrader5 library is not installed.")
            return False

        if not mt5.initialize(login=self.config['account'], password=self.config['password'], server=self.config['server']):
            log.critical(f"MT5 initialize() failed, error code = {mt5.last_error()}")
            return False

        symbol_info = mt5.symbol_info(self.symbol)
        if not symbol_info:
            log.critical(f"Symbol {self.symbol} not found. Please add it to MarketWatch in the MT5 terminal.")
            mt5.shutdown()
            return False

        if not symbol_info.visible:
            log.info(f"Symbol {self.symbol} not visible in MarketWatch, enabling it...")
            if not mt5.symbol_select(self.symbol, True):
                log.critical(f"Failed to enable symbol {self.symbol} in MarketWatch.")
                mt5.shutdown()
                return False

        log.info("MT5 connection initialized successfully.")
        self.connected = True
        return True

    def disconnect(self):
        if self.connected and mt5:
            mt5.shutdown()
            log.info("MT5 connection shut down.")
        self.connected = False

    def get_rates(self, symbol: str, timeframe_str: str, num_bars: int) -> pd.DataFrame:
        # ... (existing get_rates logic remains the same)
        if not self.connected: return pd.DataFrame()
        try:
            timeframe_map = {'M1': mt5.TIMEFRAME_M1, 'M2': mt5.TIMEFRAME_M2, 'M3': mt5.TIMEFRAME_M3, 'M4': mt5.TIMEFRAME_M4, 'M5': mt5.TIMEFRAME_M5, 'M6': mt5.TIMEFRAME_M6, 'M10': mt5.TIMEFRAME_M10, 'M12': mt5.TIMEFRAME_M12, 'M15': mt5.TIMEFRAME_M15, 'M20': mt5.TIMEFRAME_M20, 'M30': mt5.TIMEFRAME_M30, 'H1': mt5.TIMEFRAME_H1}
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
        Places a robust market order on the MT5 terminal.
        """
        if not self.connected: return None

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            log.error(f"Could not get info for {symbol}. Order failed.")
            return None

        order_type = mt5.ORDER_TYPE_BUY if direction == 'LONG' else mt5.ORDER_TYPE_SELL

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            log.error(f"Could not get tick for {symbol}. Order failed.")
            return None

        price = tick.ask if direction == 'LONG' else tick.bid
        if price == 0:
            log.error(f"Invalid price (0) for {symbol}. Order failed.")
            return None

        # Dynamically determine the filling mode
        filling_modes = symbol_info.filling_modes
        filling_type = filling_modes[0] # Use the first available filling mode

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": self.config.get('deviation', 20),
            "magic": self.magic_number,
            "comment": "Q.bot trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            log.error(f"Order send failed: {result.comment if result else 'No result'}, retcode={result.retcode if result else 'N/A'}")
            return None

        log.info(f"Order sent successfully: {result.order}")
        return result

    def get_open_positions(self):
        if not self.connected: return []
        positions = mt5.positions_get(magic=self.magic_number)
        return list(positions) if positions else []

    def close_position(self, position_id: int):
        # ... (existing close_position logic remains the same)
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
            "type_filling": mt5.symbol_info(symbol).filling_modes[0],
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            log.error(f"Close order failed: {result.comment if result else 'No result'}, retcode={result.retcode if result else 'N/A'}")
            return False

        log.info(f"Close order sent successfully for position {position_id}.")
        return True
