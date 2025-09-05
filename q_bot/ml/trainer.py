import logging
import time
import pandas as pd
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from q_bot.indicators.technicals import IndicatorManager

log = logging.getLogger('Q.bot.ModelTrainer')

class ModelTrainer:
    """
    Handles the training, evaluation, and saving of machine learning models.
    """
    DATA_DIR = Path("q_bot/data")
    MODEL_DIR = Path("q_bot/ml/models")

    # Define prediction horizons for each timeframe group
    HORIZONS = {
        'Short': 5,  # Predict 5 bars into the future for short-term models
        'Mid': 3,    # Predict 3 bars into the future for mid-term models
        'Long': 2    # Predict 2 bars into the future for long-term models
    }

    def __init__(self, config: dict):
        """
        Initializes the ModelTrainer.
        """
        self.config = config
        self.indicator_config = config['indicator_settings']
        self.symbol = config['bot_settings']['symbol']
        self.MODEL_DIR.mkdir(exist_ok=True)

    def _train_single_model(self, timeframe: str, group: str):
        """
        Trains a single model for a given timeframe.
        """
        log.info(f"--- Training model for {timeframe} ---")
        data_file = self.DATA_DIR / f"{self.symbol}_{timeframe}.csv"
        if not data_file.exists():
            log.warning(f"Data file not found for {timeframe}. Skipping training.")
            return

        df = pd.read_csv(data_file, index_col='timestamp', parse_dates=True)
        if len(df) < 100: # Need enough data to train
            log.warning(f"Not enough data for {timeframe} (found {len(df)} bars). Skipping training.")
            return

        # Feature Engineering
        feature_df = IndicatorManager(df, self.indicator_config).add_all_indicators()
        feature_df.dropna(inplace=True)

        # Define Target Variable
        horizon = self.HORIZONS[group]
        feature_df['future_close'] = feature_df['close'].shift(-horizon)
        feature_df.dropna(inplace=True)
        feature_df['target'] = (feature_df['future_close'] > feature_df['close']).astype(int)

        features = [col for col in feature_df.columns if col not in ['open', 'high', 'low', 'close', 'volume', 'future_close', 'target']]
        X = feature_df[features]
        y = feature_df['target']

        if len(X) < 50:
            log.warning(f"Not enough data to train for {timeframe} after processing. Skipping.")
            return

        # Train Model
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)
        model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)

        # Evaluate and Save
        accuracy = accuracy_score(y_test, model.predict(X_test))
        log.info(f"Model for {timeframe} trained with accuracy: {accuracy:.4f}")

        model_path = self.MODEL_DIR / f"model_{timeframe}.joblib"
        joblib.dump(model, model_path)
        log.info(f"Model saved to {model_path}")

    def train_all_models(self):
        """
        Trains a separate model for each timeframe, categorized by group.
        """
        log.info("Starting training for all models...")

        groups = {
            'Short': ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M10'],
            'Mid': ['M12', 'M15', 'M20', 'M30'],
            'Long': ['H1']
        }

        for group, timeframes in groups.items():
            log.info(f"--- Training models for {group} group ---")
            for tf in timeframes:
                self._train_single_model(tf, group)

        log.info("Model training cycle complete.")

    def run_periodic_training(self, interval_minutes=15):
        """
        Runs the training process in a loop, re-training at a specified interval.
        """
        log.info(f"Starting periodic re-training every {interval_minutes} minutes.")
        self._running = True
        while self._running:
            try:
                self.train_all_models()
                log.info(f"Next training cycle will start in {interval_minutes} minutes.")
                time.sleep(interval_minutes * 60)
            except Exception as e:
                log.error(f"Error in periodic training loop: {e}")
                time.sleep(60) # Wait a minute before retrying

    def stop(self):
        log.info("Stopping periodic model trainer.")
        self._running = False
