import pandas as pd

class DataHandler:
    """
    Handles loading, processing, and resampling of market data.
    """
    TIMEFRAME_MAP = {
        'M1': '1min', 'M2': '2min', 'M3': '3min', 'M4': '4min', 'M5': '5min',
        'M6': '6min', 'M10': '10min', 'M12': '12min', 'M15': '15min',
        'M20': '20min', 'M30': '30min', 'H1': 'h'
    }

    def __init__(self, csv_filepath, symbol):
        """
        Initializes the DataHandler.

        :param csv_filepath: Path to the CSV file with M1 data.
        :param symbol: The symbol of the instrument (e.g., 'EURUSD').
        """
        self.csv_filepath = csv_filepath
        self.symbol = symbol
        self.m1_data = None
        self._load_data()

    def _load_data(self):
        """
        Loads the M1 data from the CSV file and sets the Timestamp as the index.
        """
        try:
            self.m1_data = pd.read_csv(self.csv_filepath)
            self.m1_data['Timestamp'] = pd.to_datetime(self.m1_data['Timestamp'])
            self.m1_data.set_index('Timestamp', inplace=True)
            # Rename columns to lowercase for pandas_ta compatibility
            self.m1_data.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }, inplace=True)
        except FileNotFoundError:
            print(f"Error: Data file not found at {self.csv_filepath}")
            self.m1_data = pd.DataFrame()

    def get_resampled_data(self, timeframe_str):
        """
        Resamples the M1 data to the specified timeframe.

        :param timeframe_str: The target timeframe (e.g., 'M5', 'H1').
        :return: A pandas DataFrame with the resampled data.
        """
        if self.m1_data.empty:
            return pd.DataFrame()

        if timeframe_str not in self.TIMEFRAME_MAP:
            raise ValueError(f"Timeframe '{timeframe_str}' is not supported.")

        resample_rule = self.TIMEFRAME_MAP[timeframe_str]

        ohlc = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }

        resampled_data = self.m1_data.resample(resample_rule).apply(ohlc)
        resampled_data.dropna(inplace=True)
        return resampled_data

    def get_latest_bar(self, timeframe_str):
        """
        Gets the latest available bar for a given timeframe.

        :param timeframe_str: The timeframe to get the latest bar for (e.g., 'M5', 'H1').
        :return: A pandas Series representing the latest bar.
        """
        if self.m1_data.empty:
            return None

        return self.get_resampled_data(timeframe_str).iloc[-1]
