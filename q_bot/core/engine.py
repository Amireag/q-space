import time
import logging
import numpy as np
import pandas as pd
from q_bot.data.handler import DataHandler
from q_bot.indicators.technicals import IndicatorManager
from q_bot.core.models import Signal
from q_bot.execution.manager import TradeManager
from q_bot.utils.time_utils import SessionManager

log = logging.getLogger('Q.bot')

class TradingEngine:
    """
    The core trading engine.
    """
    def __init__(self, symbol: str, data_handler: DataHandler, trade_manager: TradeManager, session_manager: SessionManager, indicator_config: dict):
        self.symbol = symbol
        self.data_handler = data_handler
        self.trade_manager = trade_manager
        self.session_manager = session_manager
        self.indicator_config = indicator_config
        self.running = False

    def _has_required_columns(self, df: pd.DataFrame, columns: list) -> bool:
        """Checks if a dataframe has all the required columns."""
        return all(col in df.columns for col in columns)

    def run(self):
        """
        Starts the trading engine's main loop.
        """
        self.running = True
        log.info("Trading engine started.")
        while self.running:
            self.on_tick()
            time.sleep(5)
        log.info("Trading engine stopped.")

    def stop(self):
        """
        Stops the trading engine.
        """
        self.running = False

    def on_tick(self):
        """
        Called on each tick of the engine.
        """
        latest_m1_data = self.data_handler.get_resampled_data('M1')
        if not latest_m1_data.empty:
            latest_price = latest_m1_data.iloc[-1]['close']
            self.trade_manager.monitor_positions(latest_price)

        if not self.session_manager.is_trading_allowed():
            return

        log.info("New tick. Checking for signals...")
        try:
            h1_data = IndicatorManager(self.data_handler.get_resampled_data('H1'), self.indicator_config).add_all_indicators()
            m30_data = IndicatorManager(self.data_handler.get_resampled_data('M30'), self.indicator_config).add_all_indicators()
            m10_data = IndicatorManager(self.data_handler.get_resampled_data('M10'), self.indicator_config).add_all_indicators()
            m1_data = IndicatorManager(latest_m1_data, self.indicator_config).add_all_indicators()
        except Exception as e:
            log.error(f"Error getting data or indicators: {e}")
            return

        self.check_for_signals(h1_data, m30_data, m10_data, m1_data)

    def check_for_signals(self, h1_data, m30_data, m10_data, m1_data):
        """
        Checks for all types of signals.
        """
        self.check_trend_continuation(h1_data, m30_data, m10_data, m1_data)

    def check_trend_continuation(self, h1_data, m30_data, m10_data, m1_data):
        """
        Checks for a trend continuation signal.
        """
        bias_cols = ['EMA_50', 'EMA_200', 'close']
        if not (self._has_required_columns(h1_data, bias_cols) and self._has_required_columns(m30_data, bias_cols)):
            return

        latest_h1 = h1_data.iloc[-1]
        latest_m30 = m30_data.iloc[-1]

        h1_bullish = latest_h1['EMA_50'] > latest_h1['EMA_200'] and latest_h1['close'] > latest_h1['EMA_200']
        m30_bullish = latest_m30['EMA_50'] > latest_m30['EMA_200'] and latest_m30['close'] > latest_m30['EMA_200']
        is_bullish_bias = h1_bullish and m30_bullish

        h1_bearish = latest_h1['EMA_50'] < latest_h1['EMA_200'] and latest_h1['close'] < latest_h1['EMA_200']
        m30_bearish = latest_m30['EMA_50'] < latest_m30['EMA_200'] and latest_m30['close'] < latest_m30['EMA_200']
        is_bearish_bias = h1_bearish and m30_bearish

        if not (is_bullish_bias or is_bearish_bias):
            return
        direction = 'LONG' if is_bullish_bias else 'SHORT'
        log.info(f"Trend Bias Confirmed: {direction}")

        setup_cols = ['RSI_14', 'EMA_20', 'low', 'high', 'close']
        if not self._has_required_columns(m10_data, setup_cols):
            return

        latest_m10 = m10_data.iloc[-1]
        rsi_in_zone = 45 <= latest_m10['RSI_14'] <= 55
        long_pullback = latest_m10['low'] < latest_m10['EMA_20'] and latest_m10['close'] > latest_m10['EMA_20']
        short_pullback = latest_m10['high'] > latest_m10['EMA_20'] and latest_m10['close'] < latest_m10['EMA_20']

        if not ((is_bullish_bias and rsi_in_zone and long_pullback) or \
                (is_bearish_bias and rsi_in_zone and short_pullback)):
            return
        log.info(f"Setup Confirmed on M10: {direction}")

        trigger_cols = ['MACDh_12_26_9']
        if not self._has_required_columns(m1_data, trigger_cols) or len(m1_data) < 2:
            return

        latest_m1 = m1_data.iloc[-1]
        prev_m1 = m1_data.iloc[-2]

        long_trigger = is_bullish_bias and latest_m1['MACDh_12_26_9'] > 0 and prev_m1['MACDh_12_26_9'] <= 0
        short_trigger = is_bearish_bias and latest_m1['MACDh_12_26_9'] < 0 and prev_m1['MACDh_12_26_9'] >= 0

        if long_trigger or short_trigger:
            log.info(f"TRIGGER FIRED: {direction}")
            score = self.calculate_confidence_score(latest_h1, latest_m30)
            if score >= 65:
                signal = Signal(
                    symbol=self.symbol, timestamp=latest_m1.name, signal_type='TREND_CONTINUATION',
                    direction=direction, price=latest_m1['close'], confidence_score=score,
                    details={'bias': f'H1 bullish: {h1_bullish}, M30 bullish: {m30_bullish}'}
                )
                self.trade_manager.on_signal(signal)

    def calculate_confidence_score(self, latest_h1, latest_m30):
        score = 0
        if latest_h1['EMA_50'] > latest_h1['EMA_200']: score += 15
        if latest_m30['EMA_50'] > latest_m30['EMA_200']: score += 15
        score += 40 # Placeholder for other factors
        return score
