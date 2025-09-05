import logging
from datetime import time, datetime, timedelta

log = logging.getLogger('Q.bot')

class SessionManager:
    """
    Manages trading sessions and time-based rules in UTC.
    """
    def __init__(self, config: dict):
        self.trading_windows = [
            (time.fromisoformat(start), time.fromisoformat(end))
            for start, end in config['trading_windows_utc']
        ]
        self.rollover_time = time.fromisoformat(config['rollover_time'])

    def _get_current_time_utc(self):
        """Returns the current time in UTC."""
        return datetime.utcnow()

    def is_trading_allowed(self):
        """
        Checks if the current time is within a valid trading window and not in the pre-rollover block.
        """
        now_utc = self._get_current_time_utc()

        in_window = any(start <= now_utc.time() <= end for start, end in self.trading_windows)
        if not in_window:
            return False

        rollover_dt = now_utc.replace(hour=self.rollover_time.hour, minute=self.rollover_time.minute, second=0, microsecond=0)
        no_entry_start = rollover_dt - timedelta(minutes=45)

        if no_entry_start <= now_utc < rollover_dt:
            log.warning(f"In pre-rollover no-entry window. Trading blocked. Current UTC: {now_utc.strftime('%H:%M:%S')}")
            return False

        return True

    def is_force_close_time(self):
        """
        Checks if it's time to flatten all positions before rollover (T-15 mins).
        """
        now_utc = self._get_current_time_utc()

        rollover_dt = now_utc.replace(hour=self.rollover_time.hour, minute=self.rollover_time.minute, second=0, microsecond=0)
        force_close_start = rollover_dt - timedelta(minutes=15)

        return force_close_start <= now_utc < rollover_dt
