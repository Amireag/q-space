from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass
class Signal:
    """
    Represents a trading signal.
    """
    symbol: str
    timestamp: datetime
    signal_type: str  # 'TREND_CONTINUATION', 'BREAKOUT', 'RANGE_SCALP'
    direction: str    # 'LONG', 'SHORT'
    price: float
    confidence_score: float
    details: dict     # To store any extra details about the signal generation

@dataclass
class Position:
    """
    Represents an open trade.
    """
    symbol: str
    direction: str
    entry_price: float
    entry_timestamp: datetime
    position_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    volume: float = 1.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    status: str = 'OPEN' # OPEN, CLOSED
    pnl: float = 0.0
