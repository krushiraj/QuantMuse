"""Signal generator for converting strategy outputs to trading signals."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradingSignal:
    """Trading signal generated from strategy analysis."""
    symbol: str
    market: str  # "nse" or "crypto"
    signal_type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float  # 0-1
    strategy: str
    factors: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    # Optional fields
    trailing_activation: Optional[float] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/storage."""
        return {
            "symbol": self.symbol,
            "market": self.market,
            "signal_type": self.signal_type.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "confidence": self.confidence,
            "strategy": self.strategy,
            "factors": self.factors,
            "timestamp": self.timestamp.isoformat(),
            "trailing_activation": self.trailing_activation,
            "notes": self.notes,
        }


class SignalGenerator:
    """Generate trading signals from strategy outputs."""

    def __init__(
        self,
        default_stop_loss_pct: float = 5.0,
        default_take_profit_pct: float = 15.0,
        trailing_activation_pct: float = 5.0,
        min_confidence: float = 0.6,
    ):
        self.default_stop_loss_pct = default_stop_loss_pct
        self.default_take_profit_pct = default_take_profit_pct
        self.trailing_activation_pct = trailing_activation_pct
        self.min_confidence = min_confidence

    def generate_signal(
        self,
        symbol: str,
        market: str,
        strategy_name: str,
        strategy_output: Dict[str, Any],
        current_price: float,
        atr: Optional[float] = None,
    ) -> Optional[TradingSignal]:
        """
        Generate a trading signal from strategy output.

        Args:
            symbol: Trading symbol
            market: Market type ("nse" or "crypto")
            strategy_name: Name of the strategy
            strategy_output: Output from strategy (should have 'signal', 'confidence', 'factors')
            current_price: Current market price
            atr: Average True Range for dynamic stops (optional)

        Returns:
            TradingSignal if signal meets criteria, None otherwise
        """
        # Extract signal info from strategy output
        signal_value = strategy_output.get("signal", 0)
        confidence = strategy_output.get("confidence", 0.5)
        factors = strategy_output.get("factors", {})

        # Determine signal type
        if signal_value > 0:
            signal_type = SignalType.BUY
        elif signal_value < 0:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        # Skip if HOLD or below confidence threshold
        if signal_type == SignalType.HOLD:
            return None
        if confidence < self.min_confidence:
            return None

        # Calculate entry, stop loss, take profit
        entry_price = current_price

        if atr:
            # Use ATR-based stops
            stop_distance = atr * 2  # 2 ATR stop
            profit_distance = atr * 3  # 3 ATR target
        else:
            # Use percentage-based stops
            stop_distance = entry_price * (self.default_stop_loss_pct / 100)
            profit_distance = entry_price * (self.default_take_profit_pct / 100)

        if signal_type == SignalType.BUY:
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + profit_distance
            trailing_activation = entry_price * (1 + self.trailing_activation_pct / 100)
        else:  # SELL (short)
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - profit_distance
            trailing_activation = entry_price * (1 - self.trailing_activation_pct / 100)

        return TradingSignal(
            symbol=symbol,
            market=market,
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            strategy=strategy_name,
            factors=factors,
            trailing_activation=trailing_activation,
        )

    def filter_signals(
        self,
        signals: List[TradingSignal],
        max_signals: int = 5,
        min_confidence: Optional[float] = None,
    ) -> List[TradingSignal]:
        """
        Filter and rank signals by confidence.

        Args:
            signals: List of signals to filter
            max_signals: Maximum number of signals to return
            min_confidence: Minimum confidence threshold (uses default if None)

        Returns:
            Filtered and sorted list of signals
        """
        threshold = min_confidence or self.min_confidence

        # Filter by confidence
        filtered = [s for s in signals if s.confidence >= threshold]

        # Sort by confidence (highest first)
        filtered.sort(key=lambda s: s.confidence, reverse=True)

        return filtered[:max_signals]
