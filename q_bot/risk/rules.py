import logging
from datetime import datetime

log = logging.getLogger('Q.bot')

class RiskManager:
    """
    Manages trading risk based on a set of rules.
    """
    def __init__(self, initial_balance=10000, pnl_goal_pct=2.0, drawdown_stop_pct=1.0, max_trades_per_day=20):
        self.initial_balance = initial_balance
        self.pnl_goal_pct = pnl_goal_pct
        self.drawdown_stop_pct = drawdown_stop_pct
        self.max_trades_per_day = max_trades_per_day

        self.current_balance = initial_balance
        self.today = datetime.utcnow().date()
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.trading_halted = False

    def _reset_daily_stats(self):
        """
        Resets the daily statistics if a new day has started.
        """
        current_date = datetime.utcnow().date()
        if self.today != current_date:
            self.today = current_date
            self.daily_pnl = 0.0
            self.trades_today = 0
            self.trading_halted = False
            self.initial_balance = self.current_balance
            log.info(f"New day. Daily stats reset. New initial balance: {self.initial_balance:.2f}")

    def is_trade_allowed(self) -> bool:
        """
        Checks if a new trade is allowed based on the risk rules.
        """
        self._reset_daily_stats()

        if self.trading_halted:
            log.warning("Trading is halted for the day.")
            return False

        daily_loss_limit = - (self.drawdown_stop_pct / 100) * self.initial_balance
        if self.daily_pnl <= daily_loss_limit:
            log.critical(f"Daily loss limit of {daily_loss_limit:.2f} reached. Halting trading.")
            self.trading_halted = True
            return False

        daily_profit_goal = (self.pnl_goal_pct / 100) * self.initial_balance
        if self.daily_pnl >= daily_profit_goal:
            log.critical(f"Daily profit goal of {daily_profit_goal:.2f} reached. Halting trading.")
            self.trading_halted = True
            return False

        if self.trades_today >= self.max_trades_per_day:
            log.critical(f"Max trades per day ({self.max_trades_per_day}) reached. Halting trading.")
            self.trading_halted = True
            return False

        return True

    def on_trade_closed(self, pnl: float):
        """
        Updates the risk manager's state after a trade is closed.

        :param pnl: The profit or loss of the closed trade.
        """
        self._reset_daily_stats()
        self.current_balance += pnl
        self.daily_pnl += pnl
        self.trades_today += 1
        log.info(f"Trade closed. PnL: {pnl:.2f}, Daily PnL: {self.daily_pnl:.2f}, Trades today: {self.trades_today}")

    def get_position_size(self) -> float:
        """
        Calculates the position size for a new trade.
        (Simplified version)
        """
        return 0.1
