import logging
from datetime import datetime, timedelta
from q_bot.core.models import Signal, Position
from q_bot.execution.mt5_broker import MT5Broker
from q_bot.risk.rules import RiskManager
from q_bot.utils.time_utils import SessionManager

log = logging.getLogger('Q.bot')

class TradeManager:
    """
    Manages the execution of trades and positions.
    """
    def __init__(self, broker: MT5Broker, risk_manager: RiskManager, session_manager: SessionManager, config: dict):
        self.broker = broker
        self.risk_manager = risk_manager
        self.session_manager = session_manager
        self.micro_tp_pips = config['micro_tp_pips']
        self.hard_sl_pips = config['hard_sl_pips']
        self.paused_until = None
        self.pause_duration = timedelta(minutes=config['pause_duration_minutes'])

    def on_signal(self, signal: Signal):
        """
        Handles a new trading signal.
        """
        if self.paused_until and datetime.utcnow() < self.paused_until:
            log.warning(f"Trade manager is paused until {self.paused_until}. Signal ignored.")
            return

        if self.risk_manager.is_trade_allowed():
            if signal.confidence_score >= 65:
                log.info(f"TradeManager received valid signal: {signal}")
                position = self.broker.place_order(signal, sl_pips=self.hard_sl_pips, tp_pips=self.micro_tp_pips)
                if position is None:
                    log.critical("Order rejected by broker. Pausing trade manager.")
                    self.paused_until = datetime.utcnow() + self.pause_duration
        else:
            log.warning(f"Trade not allowed by RiskManager. Signal ignored: {signal}")


    def monitor_positions(self, latest_price: float):
        """
        Monitors open positions for SL/TP hits or force close.

        :param latest_price: The latest price tick for the symbol.
        """
        if not self.broker.get_open_positions():
            return

        if self.session_manager.is_force_close_time():
            log.warning("Force close time reached. Closing all open positions.")
            for position in list(self.broker.get_open_positions()):
                closed_position = self.broker.close_position(position.position_id, latest_price)
                if closed_position:
                    self.risk_manager.on_trade_closed(closed_position.pnl)
            return

        for position in list(self.broker.get_open_positions()):
            closed_position = None
            if position.direction == 'LONG':
                if latest_price >= position.take_profit:
                    log.info(f"Take profit hit for {position.position_id}")
                    closed_position = self.broker.close_position(position.position_id, position.take_profit)
                elif latest_price <= position.stop_loss:
                    log.info(f"Stop loss hit for {position.position_id}")
                    closed_position = self.broker.close_position(position.position_id, position.stop_loss)

            elif position.direction == 'SHORT':
                if latest_price <= position.take_profit:
                    log.info(f"Take profit hit for {position.position_id}")
                    closed_position = self.broker.close_position(position.position_id, position.take_profit)
                elif latest_price >= position.stop_loss:
                    log.info(f"Stop loss hit for {position.position_id}")
                    closed_position = self.broker.close_position(position.position_id, position.stop_loss)

            if closed_position:
                self.risk_manager.on_trade_closed(closed_position.pnl)
