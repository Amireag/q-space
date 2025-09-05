import pandas_ta as ta

class IndicatorManager:
    """
    A class to manage the calculation of technical indicators.
    """
    def __init__(self, data, indicator_config: dict):
        """
        Initializes the IndicatorManager with a pandas DataFrame and indicator settings.

        :param data: A pandas DataFrame with OHLCV data.
        :param indicator_config: A dictionary with indicator settings.
        """
        self.data = data.copy()
        self.config = indicator_config

    def add_all_indicators(self):
        """
        Adds all the required indicators to the DataFrame based on the config.
        """
        for length in self.config['ema_lengths']:
            self.add_ema(length=length)

        self.add_vwap()
        self.add_atr(length=self.config['atr_length'])
        self.add_bbands(length=self.config['bbands_length'])
        self.add_macd()
        self.add_rsi(length=self.config['rsi_length'])
        self.add_zscore(length=self.config['zscore_length'])
        self.add_adx(length=self.config['adx_length'])
        self.add_obv()
        return self.data

    def add_ema(self, length):
        self.data.ta.ema(length=length, append=True)

    def add_vwap(self):
        self.data.ta.vwap(append=True)

    def add_atr(self, length):
        self.data.ta.atr(length=length, append=True)

    def add_bbands(self, length):
        self.data.ta.bbands(length=length, append=True)

    def add_macd(self):
        self.data.ta.macd(append=True)

    def add_rsi(self, length):
        self.data.ta.rsi(length=length, append=True)

    def add_zscore(self, length):
        self.data.ta.zscore(length=length, append=True)

    def add_adx(self, length):
        self.data.ta.adx(length=length, append=True)

    def add_obv(self):
        self.data.ta.obv(append=True)
