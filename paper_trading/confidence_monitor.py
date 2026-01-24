"""Confidence monitor for dynamic position management."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from sqlalchemy.orm import Session

from paper_trading.models import PaperPosition, PositionAdjustment, PaperSession
from paper_trading.config import PaperTradingConfig, ConfidenceTier


@dataclass
class ConfidenceAction:
    """Action to take based on confidence change."""
    action: str  # hold, tighten, partial_close, close
    new_stop_loss: Optional[float] = None
    new_take_profit: Optional[float] = None
    close_pct: float = 0.0  # Percentage to close for partial_close
    reason: str = ""


class ConfidenceMonitor:
    """Monitor and manage positions based on confidence levels."""

    def __init__(self, config: PaperTradingConfig = None):
        self.config = config or PaperTradingConfig()
        self.confidence_config = self.config.confidence

    def get_tier(self, confidence: float) -> ConfidenceTier:
        """Get the confidence tier for a given confidence level."""
        for tier in self.confidence_config.tiers:
            if confidence >= tier.min_confidence:
                return tier
        # Return lowest tier if none match
        return self.confidence_config.tiers[-1]

    def evaluate_position(
        self,
        position: PaperPosition,
        new_confidence: float
    ) -> ConfidenceAction:
        """
        Evaluate a position and determine action based on confidence change.

        Args:
            position: The position to evaluate
            new_confidence: Updated confidence score (0-1)

        Returns:
            ConfidenceAction with recommended action
        """
        old_confidence = position.current_confidence or position.entry_confidence or 1.0
        tier = self.get_tier(new_confidence)

        # Calculate adjusted stop loss and take profit
        original_sl_distance = abs(position.entry_price - position.stop_loss)
        original_tp_distance = abs(position.take_profit - position.entry_price)

        new_sl_distance = original_sl_distance * tier.sl_factor
        new_tp_distance = original_tp_distance * tier.tp_factor

        if position.direction == "long":
            new_stop_loss = position.entry_price - new_sl_distance
            new_take_profit = position.entry_price + new_tp_distance
        else:
            new_stop_loss = position.entry_price + new_sl_distance
            new_take_profit = position.entry_price - new_tp_distance

        action = ConfidenceAction(
            action=tier.action,
            reason=f"Confidence changed from {old_confidence:.2f} to {new_confidence:.2f}"
        )

        if tier.action == "hold":
            # No changes needed
            pass
        elif tier.action == "tighten":
            action.new_stop_loss = new_stop_loss
            action.new_take_profit = new_take_profit
        elif tier.action == "partial_close":
            action.new_stop_loss = new_stop_loss
            action.new_take_profit = new_take_profit
            action.close_pct = self.confidence_config.partial_close_pct
        elif tier.action == "close":
            action.close_pct = 100.0

        return action

    def apply_action(
        self,
        db: Session,
        position: PaperPosition,
        action: ConfidenceAction,
        new_confidence: float
    ) -> Dict[str, Any]:
        """
        Apply the confidence action to a position.

        Args:
            db: Database session
            position: Position to update
            action: Action to apply
            new_confidence: New confidence value

        Returns:
            Dict with applied changes
        """
        changes = {
            "position_id": position.id,
            "action": action.action,
            "old_confidence": position.current_confidence,
            "new_confidence": new_confidence,
        }

        # Record adjustment
        if action.action in ["tighten", "partial_close"]:
            adjustment = PositionAdjustment(
                position_id=position.id,
                adjustment_type="confidence_change",
                old_stop_loss=position.stop_loss,
                new_stop_loss=action.new_stop_loss,
                old_take_profit=position.take_profit,
                new_take_profit=action.new_take_profit,
                old_confidence=position.current_confidence,
                new_confidence=new_confidence,
                reason=action.reason,
            )
            db.add(adjustment)

            # Update position
            if action.new_stop_loss:
                position.stop_loss = action.new_stop_loss
                changes["new_stop_loss"] = action.new_stop_loss
            if action.new_take_profit:
                position.take_profit = action.new_take_profit
                changes["new_take_profit"] = action.new_take_profit

        # Update confidence
        position.current_confidence = new_confidence

        if action.action == "partial_close":
            changes["close_pct"] = action.close_pct
            # Partial close logic would be handled by executor

        if action.action == "close":
            changes["should_close"] = True

        db.commit()
        return changes

    def check_all_positions(
        self,
        db: Session,
        session_id: int,
        confidence_provider: Callable[[str, str], float]
    ) -> List[Dict[str, Any]]:
        """
        Check all open positions and apply confidence-based adjustments.

        Args:
            db: Database session
            session_id: Trading session ID
            confidence_provider: Function that takes (symbol, strategy) and returns new confidence

        Returns:
            List of changes made
        """
        positions = db.query(PaperPosition).filter(
            PaperPosition.session_id == session_id,
            PaperPosition.status == "open"
        ).all()

        all_changes = []
        for position in positions:
            try:
                # Get updated confidence from provider
                new_confidence = confidence_provider(
                    position.symbol,
                    position.strategy
                )

                # Evaluate and apply action
                action = self.evaluate_position(position, new_confidence)

                if action.action != "hold":
                    changes = self.apply_action(db, position, action, new_confidence)
                    all_changes.append(changes)
                else:
                    # Still update confidence even for hold
                    position.current_confidence = new_confidence
                    db.commit()

            except Exception as e:
                all_changes.append({
                    "position_id": position.id,
                    "error": str(e)
                })

        return all_changes
