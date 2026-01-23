"""
Exit Manager for Paper Trading

Handles stop-loss, take-profit, and trailing stop logic.
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from .config import PaperTradingConfig

logger = logging.getLogger(__name__)


@dataclass
class ExitSignal:
    """Exit signal information"""
    should_exit: bool
    reason: str  # stop_loss, take_profit, trailing_stop, confidence, manual
    exit_price: float
    pnl_pct: float


class ExitManager:
    """
    Manages exit logic for positions.

    Features:
    - Hard stop-loss
    - Take-profit targets
    - Trailing stops (activate after profit threshold)
    - ATR-based dynamic levels
    """

    def __init__(self, config: PaperTradingConfig):
        """
        Initialize exit manager.

        Args:
            config: Paper trading configuration
        """
        self.config = config
        self.exits = config.exits
        self.logger = logging.getLogger(__name__)

    def check_exit(self, position: Dict[str, Any]) -> Optional[ExitSignal]:
        """
        Check if position should be exited.

        Args:
            position: Position dictionary with prices and levels

        Returns:
            ExitSignal if exit triggered, None otherwise
        """
        current_price = position.get("current_price", 0)
        entry_price = position.get("entry_price", 0)
        stop_loss = position.get("stop_loss")
        take_profit = position.get("take_profit")
        trailing_stop = position.get("trailing_stop")
        direction = position.get("direction", "long")

        if entry_price <= 0:
            return None

        # Calculate P&L percentage
        if direction == "long":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Check trailing stop first (it's usually tighter than hard SL when active)
        if trailing_stop is not None:
            if direction == "long" and current_price <= trailing_stop:
                return ExitSignal(
                    should_exit=True,
                    reason="trailing_stop",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )
            elif direction == "short" and current_price >= trailing_stop:
                return ExitSignal(
                    should_exit=True,
                    reason="trailing_stop",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )

        # Check hard stop-loss
        if stop_loss is not None:
            if direction == "long" and current_price <= stop_loss:
                return ExitSignal(
                    should_exit=True,
                    reason="stop_loss",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )
            elif direction == "short" and current_price >= stop_loss:
                return ExitSignal(
                    should_exit=True,
                    reason="stop_loss",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )

        # Check take-profit
        if take_profit is not None:
            if direction == "long" and current_price >= take_profit:
                return ExitSignal(
                    should_exit=True,
                    reason="take_profit",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )
            elif direction == "short" and current_price <= take_profit:
                return ExitSignal(
                    should_exit=True,
                    reason="take_profit",
                    exit_price=current_price,
                    pnl_pct=pnl_pct,
                )

        return None

    def update_trailing_stop(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update trailing stop based on current price.

        Args:
            position: Position dictionary

        Returns:
            Updated position dictionary
        """
        current_price = position.get("current_price", 0)
        entry_price = position.get("entry_price", 0)
        trailing_stop = position.get("trailing_stop")
        trailing_stop_high = position.get("trailing_stop_high", entry_price)
        direction = position.get("direction", "long")

        activation_pct = self.exits.trailing_stop_activation_pct
        trail_distance_pct = self.exits.trailing_stop_distance_pct

        # Calculate current profit percentage
        if direction == "long":
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_pct = ((entry_price - current_price) / entry_price) * 100

        # Check if trailing stop should be activated
        if profit_pct >= activation_pct:
            if direction == "long":
                # Update high water mark
                new_high = max(trailing_stop_high, current_price)
                # Calculate new trailing stop
                new_trail = new_high * (1 - trail_distance_pct / 100)

                # Trailing stop only moves up, never down
                if trailing_stop is None or new_trail > trailing_stop:
                    position["trailing_stop"] = round(new_trail, 2)
                    position["trailing_stop_high"] = new_high
            else:
                # Short position: trailing stop moves down
                new_low = min(trailing_stop_high, current_price)
                new_trail = new_low * (1 + trail_distance_pct / 100)

                if trailing_stop is None or new_trail < trailing_stop:
                    position["trailing_stop"] = round(new_trail, 2)
                    position["trailing_stop_high"] = new_low

        return position

    def calculate_exit_levels(
        self,
        entry_price: float,
        direction: str = "long",
        atr: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Calculate stop-loss and take-profit levels.

        Args:
            entry_price: Entry price
            direction: Trade direction (long/short)
            atr: Average True Range (optional, for ATR-based levels)

        Returns:
            Dictionary with stop_loss, take_profit, trailing_activation
        """
        if atr is not None and self.exits.use_atr_stops:
            # ATR-based levels
            sl_distance = atr * self.exits.atr_stop_multiplier
            tp_distance = atr * self.exits.atr_tp_multiplier
        else:
            # Percentage-based levels
            sl_distance = entry_price * (self.exits.default_stop_loss_pct / 100)
            tp_distance = entry_price * (self.exits.default_take_profit_pct / 100)

        if direction == "long":
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
            trailing_activation = entry_price * (1 + self.exits.trailing_stop_activation_pct / 100)
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
            trailing_activation = entry_price * (1 - self.exits.trailing_stop_activation_pct / 100)

        return {
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "trailing_activation": round(trailing_activation, 2),
        }

    def adjust_levels_for_confidence(
        self,
        position: Dict[str, Any],
        new_confidence: float,
    ) -> Dict[str, Any]:
        """
        Adjust SL/TP levels based on confidence change.

        Args:
            position: Position dictionary
            new_confidence: New confidence level

        Returns:
            Updated position with adjusted levels
        """
        entry_price = position.get("entry_price", 0)
        original_sl = position.get("stop_loss")
        original_tp = position.get("take_profit")
        direction = position.get("direction", "long")

        # Find applicable tier
        tiers = self.config.confidence.tiers
        sl_factor = 1.0
        tp_factor = 1.0
        action = "hold"

        for min_conf, sl_f, tp_f, act in tiers:
            if new_confidence >= min_conf:
                sl_factor = sl_f
                tp_factor = tp_f
                action = act
                break

        if action == "close":
            position["should_close"] = True
            return position

        # Adjust levels by tightening (moving closer to entry)
        if original_sl is not None and entry_price > 0:
            if direction == "long":
                sl_distance = entry_price - original_sl
                new_sl_distance = sl_distance * sl_factor
                position["stop_loss"] = round(entry_price - new_sl_distance, 2)
            else:
                sl_distance = original_sl - entry_price
                new_sl_distance = sl_distance * sl_factor
                position["stop_loss"] = round(entry_price + new_sl_distance, 2)

        if original_tp is not None and entry_price > 0:
            if direction == "long":
                tp_distance = original_tp - entry_price
                new_tp_distance = tp_distance * tp_factor
                position["take_profit"] = round(entry_price + new_tp_distance, 2)
            else:
                tp_distance = entry_price - original_tp
                new_tp_distance = tp_distance * tp_factor
                position["take_profit"] = round(entry_price - new_tp_distance, 2)

        position["current_confidence"] = new_confidence
        position["confidence_action"] = action

        return position
