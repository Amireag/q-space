import time
import logging
import os
import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime, timezone
from q_bot.data.handler import DataHandler
from q_bot.indicators.technicals import IndicatorManager
from q_bot.core.models import Signal
from q_bot.execution.manager import TradeManager
from q_bot.utils.time_utils import SessionManager

log = logging.getLogger('Q.bot')
MODEL_DIR = Path("q_bot/ml/models")

class TradingEngine:
    """
    The core trading engine, driven by a multi-model, grouped voting system
    with dynamic model reloading.
    """
    TIME_FRAME_GROUPS = {
        'Short': ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M10'],
        'Mid': ['M12', 'M15', 'M20', 'M30'],
        'Long': ['H1']
    }

    def __init__(self, symbol: str, data_handler: DataHandler, trade_manager: TradeManager, session_manager: SessionManager, indicator_config: dict):
        self.symbol = symbol
        self.data_handler = data_handler
        self.trade_manager = trade_manager
        self.session_manager = session_manager
        self.indicator_config = indicator_config
        self.running = False
        self.models = {}
        self.model_timestamps = {}
        self.last_model_check = 0

    def _load_models(self, force_reload=False):
        """Loads or reloads all available trained models."""
        if not force_reload: log.info("Loading all trained models...")

        all_timeframes = [tf for group in self.TIME_FRAME_GROUPS.values() for tf in group]
        for tf in all_timeframes:
            model_path = MODEL_DIR / f"model_{tf}.joblib"
            if model_path.exists():
                try:
                    current_mtime = os.path.getmtime(model_path)
                    if force_reload and tf in self.models and self.model_timestamps.get(tf) == current_mtime:
                        continue # Skip if model hasn't changed

                    self.models[tf] = joblib.load(model_path)
                    self.model_timestamps[tf] = current_mtime
                    log.info(f"{'Reloaded' if force_reload else 'Loaded'} model for {tf}.")
                except Exception as e:
                    log.error(f"Error loading model for {tf}: {e}")
            elif not force_reload:
                log.warning(f"Model for {tf} not found. It will be skipped.")

        if not self.models:
            log.critical("No models were loaded. Trading engine cannot start.")
            return False
        return True

    def run(self):
        if not self._load_models(): return
        self.running = True
        log.info("Trading engine started in ML-Voting mode.")
        while self.running:
            # Check for new models every 60 seconds
            if time.time() - self.last_model_check > 60:
                self._load_models(force_reload=True)
                self.last_model_check = time.time()

            self.on_tick()
            time.sleep(5)
        log.info("Trading engine stopped.")

    def stop(self):
        self.running = False

    def _get_group_vote(self, group_name: str, timeframes: list) -> str:
        votes = []
        for tf in timeframes:
            if tf not in self.models: continue

            data = self.data_handler.get_resampled_data(tf)
            if data is None or len(data) < 20: continue

            features_df = IndicatorManager(data, self.indicator_config).add_all_indicators()
            latest_features = features_df.iloc[-1]
            if latest_features.isnull().any(): continue

            features = latest_features.drop(['open', 'high', 'low', 'close', 'volume'])
            prediction = self.models[tf].predict(features.values.reshape(1, -1))[0]
            votes.append('LONG' if prediction == 1 else 'SHORT')

        if not votes: return 'HOLD'
        return max(set(votes), key=votes.count)

    def on_tick(self):
        latest_price_data = self.data_handler.get_resampled_data('M1')
        if not latest_price_data.empty:
            self.trade_manager.monitor_positions(latest_price_data.iloc[-1]['close'])

        if not self.session_manager.is_trading_allowed(): return

        log.info("New tick. Getting votes from model groups...")

        short_vote = self._get_group_vote('Short', self.TIME_FRAME_GROUPS['Short'])
        mid_vote = self._get_group_vote('Mid', self.TIME_FRAME_GROUPS['Mid'])
        long_vote = self._get_group_vote('Long', self.TIME_FRAME_GROUPS['Long'])

        log.info(f"Votes: Short={short_vote}, Mid={mid_vote}, Long={long_vote}")

        if short_vote == mid_vote == long_vote and short_vote != 'HOLD':
            direction = short_vote
            log.info(f"CONSENSUS REACHED: {direction}")

            signal = Signal(
                symbol=self.symbol,
                timestamp=datetime.now(timezone.utc),
                signal_type='ML_VOTING',
                direction=direction,
                price=latest_price_data.iloc[-1]['close'],
                confidence_score=99,
                details={'votes': f'S:{short_vote}, M:{mid_vote}, L:{long_vote}'}
            )
            self.trade_manager.on_signal(signal)
        else:
            log.info("No consensus. Holding.")
