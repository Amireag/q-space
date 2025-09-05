import logging
import random
from q_bot.core.models import Position, Signal

log = logging.getLogger('Q.bot')

class MockBroker:
    """
    A simulated broker for testing purposes.
    """
    def __init__(self, rejection_rate=0.1):
        self.open_positions = []
        self.trade_history = []
        self.rejection_rate = rejection_rate

    def place_order(self, signal: Signal, sl_pips: float, tp_pips: float):
        """
        Simulates placing an order and opening a position.
        Can be rejected based on the rejection_rate.
        """
        if random.random() < self.rejection_rate:
            log.critical("--- MOCK BROKER: ORDER REJECTED ---")
            return None

        log.info(f"Placing order for {signal.direction} {signal.symbol} at {signal.price}")

        pip_value = 0.0001

        if signal.direction == 'LONG':
            stop_loss = signal.price - sl_pips * pip_value
            take_profit = signal.price + tp_pips * pip_value
        else: # SHORT
            stop_loss = signal.price + sl_pips * pip_value
            take_profit = signal.price - tp_pips * pip_value

        position = Position(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.price,
            entry_timestamp=signal.timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        self.open_positions.append(position)
        self.trade_history.append(position)
        log.info(f"Position opened: {position}")
        return position

    def get_open_positions(self):
        """
        Returns the list of open positions.
        """
        return self.open_positions

    def close_position(self, position_id: str, close_price: float):
        """
        Simulates closing a position.
        """
        position_to_close = next((p for p in self.open_positions if p.position_id == position_id), None)

        if position_to_close:
            pnl = (close_price - position_to_close.entry_price) * (1 if position_to_close.direction == 'LONG' else -1)
            pnl *= 10000
            position_to_close.pnl = pnl
            position_to_close.status = 'CLOSED'
            self.open_positions.remove(position_to_close)
            log.info(f"Position closed: {position_to_close.position_id} at {close_price}, PnL: {pnl:.2f}")
        else:
            log.error(f"Position not found: {position_id}")

        return position_to_close
