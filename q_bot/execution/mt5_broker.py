import logging
from q_bot.core.models import Signal
from q_bot.connectors.mt5_adapter import MT5Adapter

log = logging.getLogger('Q.bot')

class MT5Broker:
    """
    A broker that interacts with the MT5 terminal via the MT5Adapter.
    """
    def __init__(self, mt5_adapter: MT5Adapter):
        self.adapter = mt5_adapter

    def place_order(self, signal: Signal, sl_pips: float, tp_pips: float):
        """
        Places a trade order.
        """
        log.info(f"MT5Broker: Relaying order to MT5Adapter for {signal.direction} {signal.symbol}")

        pip_value = 0.0001

        if signal.direction == 'LONG':
            stop_loss = signal.price - sl_pips * pip_value
            take_profit = signal.price + tp_pips * pip_value
        else: # SHORT
            stop_loss = signal.price + sl_pips * pip_value
            take_profit = signal.price - tp_pips * pip_value

        # Volume would be calculated by the RiskManager in a full implementation
        volume = 0.1

        return self.adapter.place_order(
            symbol=signal.symbol,
            direction=signal.direction,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

    def get_open_positions(self):
        """
        Returns the list of open positions.
        """
        return self.adapter.get_open_positions()

    def close_position(self, position_id: str, close_price: float):
        """
        Closes a position.
        """
        log.info(f"MT5Broker: Relaying close order to MT5Adapter for position {position_id}")
        return self.adapter.close_position(position_id)
