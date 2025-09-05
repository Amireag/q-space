import threading
import time
from q_bot.data.handler import DataHandler
from q_bot.core.engine import TradingEngine
from q_bot.execution.mt5_broker import MT5Broker
from q_bot.execution.manager import TradeManager
from q_bot.risk.rules import RiskManager
from q_bot.utils.time_utils import SessionManager
from q_bot.utils.logger import setup_logging, log
from q_bot.utils.config import load_config
from q_bot.connectors.mt5_adapter import MT5Adapter
from q_bot.ui.dashboard import Dashboard

def main():
    """
    Main function to initialize and run the Q.bot.
    """
    setup_logging()

    log.info("=============================================")
    log.info("           STARTING Q.BOT (Live Mode)        ")
    log.info("=============================================")

    # 1. Load Configuration
    config = load_config('q_bot/config/settings.json')
    if not config:
        log.critical("Could not load configuration. Exiting.")
        return

    # 2. Initialize components
    bot_conf = config['bot_settings']
    risk_conf = config['risk_management']
    trade_conf = config['trade_management']
    session_conf = config['session_management']
    mt5_conf = config['mt5_settings']

    mt5_adapter = MT5Adapter(config=mt5_conf)
    if not mt5_adapter.connect():
        log.critical("Failed to connect to MetaTrader 5.")
        return

    data_handler = DataHandler(mt5_adapter=mt5_adapter, symbol=bot_conf['symbol'])
    broker = MT5Broker(mt5_adapter=mt5_adapter)
    session_manager = SessionManager(config=session_conf)
    risk_manager = RiskManager(initial_balance=risk_conf['initial_balance'])
    trade_manager = TradeManager(broker, risk_manager, session_manager, trade_conf)
    engine = TradingEngine(bot_conf['symbol'], data_handler, trade_manager, session_manager, config['indicator_settings'])

    # --- Initialize Dashboard ---
    dashboard = Dashboard(risk_manager, broker, bot_conf['symbol'])

    # 3. Run components in threads
    log.info("Starting components in background threads...")
    engine_thread = threading.Thread(target=engine.run)
    dashboard.start() # The dashboard's start method handles its own thread
    engine_thread.start()

    try:
        while engine_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Caught KeyboardInterrupt. Stopping all components...")
        engine.stop()
        dashboard.stop()

    # 4. Disconnect and shutdown
    mt5_adapter.disconnect()
    engine_thread.join()
    log.info("=============================================")
    log.info("           Q.BOT SHUTDOWN COMPLETE           ")
    log.info("=============================================")


if __name__ == "__main__":
    main()
