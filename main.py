import threading
import time
from q_bot.data.handler import DataHandler
from q_bot.data.logger import DataLogger
from q_bot.core.engine import TradingEngine
from q_bot.execution.mt5_broker import MT5Broker
from q_bot.execution.manager import TradeManager
from q_bot.risk.rules import RiskManager
from q_bot.utils.time_utils import SessionManager
from q_bot.utils.logger import setup_logging, log
from q_bot.utils.config import load_config
from q_bot.connectors.mt5_adapter import MT5Adapter
from q_bot.ui.dashboard import Dashboard
from q_bot.ml.trainer import ModelTrainer

def main():
    """
    Main function to initialize and run the complete Q.bot system.
    """
    setup_logging()
    log.info("=============================================")
    log.info("           STARTING Q.BOT (ML Live Mode)     ")
    log.info("=============================================")

    # 1. Load Config
    config = load_config('q_bot/config/settings.json')
    if not config: return

    # 2. Initialize Components
    bot_conf = config['bot_settings']
    mt5_conf = config['mt5_settings']

    mt5_adapter = MT5Adapter(config=mt5_conf)
    if not mt5_adapter.connect(): return

    # 3. Perform Initial Data Backfill
    # This runs once at the start to ensure we have data.
    data_logger = DataLogger(mt5_adapter, bot_conf['symbol'])
    data_logger.initial_backfill()

    # 4. Perform Initial Model Training
    # This runs once at the start to ensure we have models to trade with.
    model_trainer = ModelTrainer(config)
    model_trainer.train_all_models()

    # 5. Initialize Live Components
    data_handler = DataHandler(mt5_adapter, bot_conf['symbol'])
    broker = MT5Broker(mt5_adapter)
    session_manager = SessionManager(config=config['session_management'])
    risk_manager = RiskManager(initial_balance=config['risk_management']['initial_balance'])
    trade_manager = TradeManager(broker, risk_manager, session_manager, config['trade_management'])
    engine = TradingEngine(bot_conf['symbol'], data_handler, trade_manager, session_manager, config['indicator_settings'])
    dashboard = Dashboard(risk_manager, broker, bot_conf['symbol'])

    # 6. Start All Components in Background Threads
    log.info("Starting all components in background threads...")

    # Create threads for each long-running process
    engine_thread = threading.Thread(target=engine.run, name="TradingEngine")
    dashboard_thread = threading.Thread(target=dashboard.run, name="Dashboard")
    logger_thread = threading.Thread(target=data_logger.run_continuous_logging, name="DataLogger")
    trainer_thread = threading.Thread(target=model_trainer.run_periodic_training, name="ModelTrainer")

    threads = [engine_thread, dashboard_thread, logger_thread, trainer_thread]

    for t in threads:
        t.start()

    try:
        # Keep the main thread alive to handle the exit
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Caught KeyboardInterrupt. Stopping all components...")
        data_logger.stop()
        model_trainer.stop()
        engine.stop()
        dashboard.stop()

    # 7. Disconnect and Shutdown
    for t in threads:
        t.join() # Wait for all threads to finish

    mt5_adapter.disconnect()
    log.info("=============================================")
    log.info("           Q.BOT SHUTDOWN COMPLETE           ")
    log.info("=============================================")


if __name__ == "__main__":
    main()
