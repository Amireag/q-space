import threading
import time
from q_bot.data.handler import DataHandler
from q_bot.core.engine import TradingEngine
from q_bot.execution.broker import MockBroker
from q_bot.execution.manager import TradeManager
from q_bot.risk.rules import RiskManager
from q_bot.utils.time_utils import SessionManager
from q_bot.utils.logger import setup_logging, log
from q_bot.utils.config import load_config

def main():
    """
    Main function to initialize and run the Q.bot.
    """
    setup_logging()

    log.info("=============================================")
    log.info("           STARTING Q.BOT                    ")
    log.info("=============================================")

    # 1. Load Configuration
    log.info("Loading configuration...")
    config = load_config('q_bot/config/settings.json') # Adjusted path for root execution
    if not config:
        log.critical("Could not load configuration. Exiting.")
        return

    # 2. Initialize components with config
    log.info("Initializing components from config...")
    bot_conf = config['bot_settings']
    risk_conf = config['risk_management']
    trade_conf = config['trade_management']
    session_conf = config['session_management']
    broker_conf = config['broker_settings']

    data_handler = DataHandler(csv_filepath=bot_conf['data_filepath'], symbol=bot_conf['symbol'])
    broker = MockBroker(rejection_rate=broker_conf['rejection_rate'])
    session_manager = SessionManager(config=session_conf)
    risk_manager = RiskManager(
        initial_balance=risk_conf['initial_balance'],
        pnl_goal_pct=risk_conf['pnl_goal_pct'],
        drawdown_stop_pct=risk_conf['drawdown_stop_pct'],
        max_trades_per_day=risk_conf['max_trades_per_day']
    )
    trade_manager = TradeManager(
        broker=broker,
        risk_manager=risk_manager,
        session_manager=session_manager,
        config=trade_conf
    )
    engine = TradingEngine(
        symbol=bot_conf['symbol'],
        data_handler=data_handler,
        trade_manager=trade_manager,
        session_manager=session_manager,
        indicator_config=config['indicator_settings']
    )

    # 3. Run the engine
    log.info("Starting trading engine...")
    engine_thread = threading.Thread(target=engine.run)
    engine_thread.start()

    try:
        while engine_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Caught KeyboardInterrupt. Stopping engine...")
        engine.stop()

    engine_thread.join()
    log.info("=============================================")
    log.info("           Q.BOT SHUTDOWN COMPLETE           ")
    log.info("=============================================")


if __name__ == "__main__":
    main()
