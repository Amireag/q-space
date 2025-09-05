import pandas as pd
from finta import TA

class IndicatorManager:
    """
    A class to manage the calculation of technical indicators using the 'finta' library
    and custom implementations.
    """
    def __init__(self, data: pd.DataFrame, indicator_config: dict):
        """
        Initializes the IndicatorManager with a pandas DataFrame and indicator settings.

        :param data: A pandas DataFrame with OHLCV data (lowercase columns).
        :param indicator_config: A dictionary with indicator settings.
        """
        self.data = data.copy()
        self.config = indicator_config

    def add_all_indicators(self):
        """
        Adds all the required indicators to the DataFrame based on the config.
        """
        if self.data.empty:
            return self.data

        # Use FINTA for supported indicators
        for length in self.config['ema_lengths']:
            self.add_ema(length=length)

        self.add_bbands(length=self.config['bbands_length'])
        self.add_macd()
        self.add_rsi(length=self.config['rsi_length'])
        self.add_adx(length=self.config['adx_length'])
        self.add_atr(length=self.config['atr_length'])

        # Manually implement missing indicators
        self.add_vwap()
        self.add_zscore(length=self.config['zscore_length'])
        self.add_obv()

        return self.data

    def add_ema(self, length):
        self.data[f'EMA_{length}'] = TA.EMA(self.data, period=length)

    def add_bbands(self, length):
        bbands = TA.BBANDS(self.data, period=length)
        self.data['BB_UPPER'] = bbands['BB_UPPER']
        self.data['BB_MIDDLE'] = bbands['BB_MIDDLE']
        self.data['BB_LOWER'] = bbands['BB_LOWER']

    def add_macd(self):
        macd = TA.MACD(self.data)
        self.data['MACD'] = macd['MACD']
        self.data['MACD_SIGNAL'] = macd['SIGNAL']
        # Finta's MACD doesn't directly return the histogram, so we calculate it.
        self.data['MACD_HIST'] = self.data['MACD'] - self.data['MACD_SIGNAL']

    def add_rsi(self, length):
        self.data[f'RSI_{length}'] = TA.RSI(self.data, period=length)

    def add_adx(self, length):
        self.data[f'ADX_{length}'] = TA.ADX(self.data, period=length)

    def add_atr(self, length):
        self.data[f'ATR_{length}'] = TA.ATR(self.data, period=length)

    # --- Custom Indicator Implementations ---

    def add_vwap(self):
        """Calculates and adds the Volume Weighted Average Price (VWAP)."""
        vp = self.data['volume'] * (self.data['high'] + self.data['low'] + self.data['close']) / 3
        self.data['VWAP'] = vp.cumsum() / self.data['volume'].cumsum()

    def add_zscore(self, length):
        """Calculates and adds the Z-score of the close price."""
        mean = self.data['close'].rolling(window=length).mean()
        std = self.data['close'].rolling(window=length).std()
        self.data[f'ZSCORE_{length}'] = (self.data['close'] - mean) / std

    def add_obv(self):
        """Calculates and adds the On-Balance Volume (OBV)."""
        obv = (self.data['volume'] * (~self.data['close'].diff().le(0) * 2 - 1)).cumsum()
        self.data['OBV'] = obv
