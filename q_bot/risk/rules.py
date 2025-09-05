import logging
from datetime import datetime
from q_bot.connectors.mt5_adapter import MT5Adapter

log = logging.getLogger('Q.bot')

class RiskManager:
    """
    Manages trading risk and provides live performance statistics from the broker.
    """
    def __init__(self, mt5_adapter: MT5Adapter, initial_balance=10000, pnl_goal_pct=2.0, drawdown_stop_pct=1.0, max_trades_per_day=20):
        self.adapter = mt5_adapter
        self.initial_balance = initial_balance # Used for daily PnL % calculations
        self.pnl_goal_pct = pnl_goal_pct
        self.drawdown_stop_pct = drawdown_stop_pct
        self.max_trades_per_day = max_trades_per_day

        # Internal state for tracking trades managed by the bot
        self.today = datetime.now().date()
        self.trades_today = 0
        self.wins_today = 0
        self.losses_today = 0
        self.trading_halted = False

    def _reset_daily_stats(self):
        """
        Resets the daily trade-count statistics if a new day has started.
        """
        current_date = datetime.now().date()
        if self.today != current_date:
            self.today = current_date
            self.trades_today = 0
            self.wins_today = 0
            self.losses_today = 0
            self.trading_halted = False
            # Update the initial balance for the new day based on the previous day's close
            account_info = self.adapter.get_account_info()
            if account_info:
                self.initial_balance = account_info.balance
            log.info(f"New day. Daily stats reset. New initial balance: {self.initial_balance:.2f}")

    def is_trade_allowed(self) -> bool:
        self._reset_daily_stats()
        account_info = self.adapter.get_account_info()
        if not account_info:
            log.error("Could not get account info. Trading disallowed.")
            return False

        daily_pnl = account_info.profit

        if self.trading_halted:
            log.warning("Trading is halted for the day.")
            return False

        daily_loss_limit = - (self.drawdown_stop_pct / 100) * self.initial_balance
        if daily_pnl <= daily_loss_limit:
            log.critical(f"Daily loss limit of {daily_loss_limit:.2f} reached. Halting trading.")
            self.trading_halted = True
            return False

        daily_profit_goal = (self.pnl_goal_pct / 100) * self.initial_balance
        if daily_pnl >= daily_profit_goal:
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
        Updates internal trade counters after a trade is closed.
        Note: The primary PnL tracking is now done via live account info.
        """
        self._reset_daily_stats()
        self.trades_today += 1
        if pnl > 0:
            self.wins_today += 1
        elif pnl < 0:
            self.losses_today += 1
        log.info(f"Trade closed. Bot-managed trades today: {self.trades_today}")

    def get_stats(self) -> dict:
        """
        Returns a dictionary of LIVE performance statistics from the broker.
        """
        account_info = self.adapter.get_account_info()
        if not account_info:
            return {
                "win_rate": "N/A", "loss_rate": "N/A", "balance": "N/A",
                "daily_pnl": "N/A", "total_pnl": "N/A"
            }

        win_rate = (self.wins_today / self.trades_today) * 100 if self.trades_today > 0 else 0
        loss_rate = (self.losses_today / self.trades_today) * 100 if self.trades_today > 0 else 0

        return {
            "win_rate": f"{win_rate:.2f}%",
            "loss_rate": f"{loss_rate:.2f}%",
            "balance": f"{account_info.balance:.2f}",
            "daily_pnl": f"{account_info.profit:.2f}",
            "total_pnl": f"{account_info.equity - self.initial_balance:.2f}"
        }
