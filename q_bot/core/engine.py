import time
import logging
import pandas as pd
import joblib
from q_bot.data.handler import DataHandler
from q_bot.indicators.technicals import IndicatorManager
from q_bot.core.models import Signal
from q_bot.execution.manager import TradeManager
from q_bot.utils.time_utils import SessionManager

log = logging.getLogger('Q.bot')
MODEL_FILE = "q_bot_model.joblib"

class TradingEngine:
    """
    The core trading engine, now driven by a machine learning model.
    """
    def __init__(self, symbol: str, data_handler: DataHandler, trade_manager: TradeManager, session_manager: SessionManager, indicator_config: dict):
        self.symbol = symbol
        self.data_handler = data_handler
        self.trade_manager = trade_manager
        self.session_manager = session_manager
        self.indicator_config = indicator_config
        self.running = False
        self.model = self._load_model()

    def _load_model(self):
        """Loads the trained machine learning model."""
        try:
            model = joblib.load(MODEL_FILE)
            log.info(f"Successfully loaded model from {MODEL_FILE}")
            return model
        except FileNotFoundError:
            log.critical(f"Model file not found at {MODEL_FILE}. Please run train_model.py first.")
            return None

    def run(self):
        """
        Starts the trading engine's main loop.
        """
        if self.model is None:
            log.critical("Cannot start TradingEngine: model not loaded.")
            return

        self.running = True
        log.info("Trading engine started in ML mode.")
        while self.running:
            self.on_tick()
            time.sleep(5) # Check every 5 seconds
        log.info("Trading engine stopped.")

    def stop(self):
        self.running = False

    def on_tick(self):
        """
        Called on each tick of the engine.
        Fetches data, calculates features, and makes a prediction.
        """
        latest_price_data = self.data_handler.get_resampled_data('M1')
        if not latest_price_data.empty:
            latest_price = latest_price_data.iloc[-1]['close']
            self.trade_manager.monitor_positions(latest_price)

        if not self.session_manager.is_trading_allowed():
            return

        log.info("New tick. Getting data for prediction...")
        # We trained the model on M5 data, so we need M5 data for prediction.
        m5_data = self.data_handler.get_resampled_data('M5')

        if m5_data is None or len(m5_data) < self.indicator_config.get('zscore_length', 20): # Check for enough data
            log.warning("Not enough M5 data to generate features for prediction.")
            return

        # 1. Feature Engineering
        features_df = IndicatorManager(m5_data, self.indicator_config).add_all_indicators()
        latest_features = features_df.iloc[-1]

        # Check for NaN values in the latest features
        if latest_features.isnull().any():
            log.warning("Latest features contain NaN values. Skipping prediction.")
            return

        # 2. Make Prediction
        # The model expects a 2D array, so we reshape the series.
        features_for_prediction = latest_features.drop(['open', 'high', 'low', 'close', 'volume']).values.reshape(1, -1)
        prediction = self.model.predict(features_for_prediction)[0]

        # 3. Generate Signal
        # 1 = BUY, 0 = SELL/HOLD. We will treat 0 as SELL for this implementation.
        if prediction == 1:
            direction = 'LONG'
        else:
            direction = 'SHORT'

        log.info(f"Model prediction: {direction}")

        # For now, we'll trade on every signal. Confidence score can be added later.
        signal = Signal(
            symbol=self.symbol,
            timestamp=latest_features.name,
            signal_type='ML_PREDICTION',
            direction=direction,
            price=latest_features['close'],
            confidence_score=99, # High confidence as it's from the model
            details={'model_prediction': int(prediction)}
        )
        self.trade_manager.on_signal(signal)
