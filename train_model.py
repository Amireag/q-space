import logging
import pandas as pd
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from q_bot.indicators.technicals import IndicatorManager
from q_bot.utils.config import load_config
from q_bot.utils.logger import setup_logging

log = logging.getLogger('Q.bot.ModelTrainer')
MODEL_FILE = "q_bot_model.joblib"

def main():
    """
    Main function for the Model Trainer.
    Loads data, engineers features, trains a model, and saves it.
    """
    setup_logging()
    log.info("--- Starting Model Trainer ---")

    # 1. Load Config
    config = load_config('q_bot/config/settings.json')
    if not config: return

    bot_conf = config['bot_settings']
    indicator_conf = config['indicator_settings']

    # 2. Load Data
    data_file = Path("data") / f"{bot_conf['symbol']}_M5.csv"
    if not data_file.exists():
        log.critical(f"Data file not found: {data_file}. Please run data_logger.py first.")
        return

    log.info(f"Loading data from {data_file}...")
    df = pd.read_csv(data_file, index_col='timestamp', parse_dates=True)

    # 3. Feature Engineering
    log.info("Engineering features...")
    feature_df = IndicatorManager(df, indicator_conf).add_all_indicators()
    feature_df.dropna(inplace=True)
    log.info(f"Feature engineering complete. Shape of feature set: {feature_df.shape}")

    # 4. Define Target Variable
    log.info("Defining target variable...")
    future_horizon = 5
    feature_df['future_close'] = feature_df['close'].shift(-future_horizon)
    feature_df.dropna(inplace=True)
    feature_df['target'] = (feature_df['future_close'] > feature_df['close']).astype(int)

    # 5. Define Features (X) and Target (y)
    features = [col for col in feature_df.columns if col not in ['open', 'high', 'low', 'close', 'volume', 'future_close', 'target']]
    X = feature_df[features]
    y = feature_df['target']

    if len(X) == 0:
        log.critical("Not enough data to train a model after processing. Please collect more data.")
        return

    # 6. Split Data
    log.info("Splitting data into training and testing sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)

    # 7. Train Model
    log.info("Training RandomForestClassifier model...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    # 8. Evaluate Model
    log.info("Evaluating model...")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    log.info(f"Model accuracy on test set: {accuracy:.4f}")

    # 9. Save Model
    log.info(f"Saving trained model to {MODEL_FILE}...")
    joblib.dump(model, MODEL_FILE)

    log.info("--- Model Training Complete ---")


if __name__ == "__main__":
    main()
