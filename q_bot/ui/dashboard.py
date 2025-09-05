import time
import threading
from datetime import datetime
from q_bot.risk.rules import RiskManager
from q_bot.execution.mt5_broker import MT5Broker

class Dashboard:
    """
    A CLI dashboard to display real-time bot statistics.
    """
    def __init__(self, risk_manager: RiskManager, broker: MT5Broker, symbol: str):
        self.risk_manager = risk_manager
        self.broker = broker
        self.symbol = symbol
        self._running = False
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        """
        The main loop for the dashboard thread.
        """
        self._running = True
        while self._running:
            try:
                stats = self.risk_manager.get_stats()
                open_trades = len(self.broker.get_open_positions())

                # [date:time] [symbol] [win rate] [loss rate] [balance] [open trades] [today's profit] [total profit of today]
                status_line = (
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"[{self.symbol}] "
                    f"[Win: {stats['win_rate']}] "
                    f"[Loss: {stats['loss_rate']}] "
                    f"[Balance: {stats['balance']}] "
                    f"[Open: {open_trades}] "
                    f"[Daily PnL: {stats['daily_pnl']}] "
                    f"[Total PnL: {stats['total_pnl']}]"
                )

                # Print the status line, using carriage return to overwrite the previous line
                print(status_line, end='\\r')

                time.sleep(1)
            except Exception as e:
                print(f"Error in Dashboard: {e}")
                time.sleep(5)

    def start(self):
        """
        Starts the dashboard thread.
        """
        self.thread.start()

    def stop(self):
        """
        Stops the dashboard thread.
        """
        self._running = False
        # Add a final newline character to avoid leaving the last status line hanging
        print()
