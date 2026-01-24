"""
Paper Executor for Paper Trading

Executes simulated trades, manages positions, and updates balances.
"""
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session

from .models import PaperSession, PaperPosition, PaperTrade, PositionAdjustment
from .config import PaperTradingConfig
from .position_manager import PositionManager

logger = logging.getLogger(__name__)


class PaperExecutor:
    """
    Executes paper trades and manages position lifecycle.

    Features:
    - Open new positions
    - Close positions (full or partial)
    - Update position prices
    - Record all trades and adjustments
    """

    def __init__(self, config: PaperTradingConfig, db: Session):
        """
        Initialize paper executor.

        Args:
            config: Paper trading configuration
            db: SQLAlchemy database session
        """
        self.config = config
        self.db = db
        self.position_manager = PositionManager(config)
        self.logger = logging.getLogger(__name__)

    def open_position(
        self,
        session_id: int,
        signal: Dict[str, Any],
        quantity: int,
    ) -> PaperPosition:
        """
        Open a new paper trading position.

        Args:
            session_id: Paper trading session ID
            signal: Signal dictionary with entry details
            quantity: Number of shares/units to buy

        Returns:
            Created PaperPosition object
        """
        # Get session
        session = self.db.query(PaperSession).filter_by(id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        symbol = signal.get("symbol")
        market = signal.get("market", "nse")
        entry_price = signal.get("entry_price")
        stop_loss = signal.get("stop_loss")
        take_profit = signal.get("take_profit")
        confidence = signal.get("confidence", 1.0)
        strategy = signal.get("strategy", "")
        direction = signal.get("direction", "long")

        # Calculate trade value and commission
        trade_value = entry_price * quantity
        commission = self.position_manager.calculate_commission(trade_value, market)

        # Check sufficient balance
        total_cost = trade_value + commission
        if session.current_balance < total_cost:
            raise ValueError(f"Insufficient balance: {session.current_balance} < {total_cost}")

        # Create position
        position = PaperPosition(
            session_id=session_id,
            symbol=symbol,
            market=market,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=None,
            trailing_stop_high=entry_price,
            entry_confidence=confidence,
            current_confidence=confidence,
            strategy=strategy,
            status="open",
        )
        self.db.add(position)
        self.db.flush()  # Get position ID

        # Create buy trade record
        trade = PaperTrade(
            session_id=session_id,
            position_id=position.id,
            symbol=symbol,
            market=market,
            trade_type="buy",
            quantity=quantity,
            price=entry_price,
            value=trade_value,
            commission=commission,
            pnl=None,
        )
        self.db.add(trade)

        # Update session balance
        session.current_balance -= total_cost

        self.db.commit()
        self.logger.info(f"Opened position: {symbol} x{quantity} @ {entry_price}")

        return position

    def close_position(
        self,
        position_id: int,
        exit_price: float,
        reason: str = "manual",
    ) -> PaperPosition:
        """
        Close an existing position.

        Args:
            position_id: Position ID to close
            exit_price: Exit price
            reason: Close reason (stop_loss, take_profit, trailing_stop, manual, confidence)

        Returns:
            Closed PaperPosition object
        """
        position = self.db.query(PaperPosition).filter_by(id=position_id).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")

        if position.status != "open":
            raise ValueError(f"Position {position_id} is not open")

        session = self.db.query(PaperSession).filter_by(id=position.session_id).first()

        # Calculate P&L
        if position.direction in ("long", "BUY"):
            gross_pnl = (exit_price - position.entry_price) * position.quantity
        else:  # short or SELL
            gross_pnl = (position.entry_price - exit_price) * position.quantity

        # Calculate trade value and commission
        trade_value = exit_price * position.quantity
        commission = self.position_manager.calculate_commission(trade_value, position.market)
        net_pnl = gross_pnl - commission

        # Create sell trade record
        trade = PaperTrade(
            session_id=position.session_id,
            position_id=position.id,
            symbol=position.symbol,
            market=position.market,
            trade_type="sell",
            quantity=position.quantity,
            price=exit_price,
            value=trade_value,
            commission=commission,
            pnl=net_pnl,
        )
        self.db.add(trade)

        # Update position
        position.current_price = exit_price
        position.status = "closed"
        position.close_reason = reason
        position.closed_at = datetime.utcnow()

        # Update session balance
        session.current_balance += trade_value - commission

        self.db.commit()
        self.logger.info(f"Closed position: {position.symbol} @ {exit_price}, P&L: {net_pnl}")

        return position

    def partial_close(
        self,
        position_id: int,
        close_pct: float,
        exit_price: float,
        reason: str = "partial",
    ) -> Tuple[PaperTrade, PaperPosition]:
        """
        Partially close a position.

        Args:
            position_id: Position ID
            close_pct: Percentage to close (0-100)
            exit_price: Exit price
            reason: Close reason

        Returns:
            Tuple of (sell trade, remaining position)
        """
        position = self.db.query(PaperPosition).filter_by(id=position_id).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")

        session = self.db.query(PaperSession).filter_by(id=position.session_id).first()

        # Calculate quantity to close
        close_quantity = int(position.quantity * (close_pct / 100))
        if close_quantity <= 0:
            raise ValueError("Close quantity must be positive")

        remaining_quantity = position.quantity - close_quantity

        # Calculate P&L for closed portion
        if position.direction in ("long", "BUY"):
            gross_pnl = (exit_price - position.entry_price) * close_quantity
        else:  # short or SELL
            gross_pnl = (position.entry_price - exit_price) * close_quantity

        trade_value = exit_price * close_quantity
        commission = self.position_manager.calculate_commission(trade_value, position.market)
        net_pnl = gross_pnl - commission

        # Create sell trade for partial close
        trade = PaperTrade(
            session_id=position.session_id,
            position_id=position.id,
            symbol=position.symbol,
            market=position.market,
            trade_type="sell",
            quantity=close_quantity,
            price=exit_price,
            value=trade_value,
            commission=commission,
            pnl=net_pnl,
        )
        self.db.add(trade)

        # Update position quantity
        position.quantity = remaining_quantity
        position.current_price = exit_price

        # If nothing remaining, close position
        if remaining_quantity <= 0:
            position.status = "closed"
            position.close_reason = reason
            position.closed_at = datetime.utcnow()

        # Update session balance
        session.current_balance += trade_value - commission

        # Record adjustment
        adjustment = PositionAdjustment(
            position_id=position.id,
            adjustment_type="partial_close",
            reason=f"Closed {close_pct}% ({close_quantity} units) - {reason}",
        )
        self.db.add(adjustment)

        self.db.commit()
        self.logger.info(f"Partial close: {position.symbol} x{close_quantity} @ {exit_price}")

        return trade, position

    def update_position_price(
        self,
        position_id: int,
        current_price: float,
    ) -> PaperPosition:
        """
        Update current price for a position.

        Args:
            position_id: Position ID
            current_price: New current price

        Returns:
            Updated position
        """
        position = self.db.query(PaperPosition).filter_by(id=position_id).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")

        position.current_price = current_price

        # Update trailing stop high if applicable
        if position.direction in ("long", "BUY"):
            if position.trailing_stop_high is None or current_price > position.trailing_stop_high:
                position.trailing_stop_high = current_price
        else:  # short or SELL
            if position.trailing_stop_high is None or current_price < position.trailing_stop_high:
                position.trailing_stop_high = current_price

        self.db.commit()
        return position

    def record_adjustment(
        self,
        position_id: int,
        adjustment_type: str,
        old_sl: Optional[float] = None,
        new_sl: Optional[float] = None,
        old_tp: Optional[float] = None,
        new_tp: Optional[float] = None,
        old_confidence: Optional[float] = None,
        new_confidence: Optional[float] = None,
        reason: str = "",
    ) -> PositionAdjustment:
        """
        Record a position adjustment.

        Args:
            position_id: Position ID
            adjustment_type: Type of adjustment
            old_sl/new_sl: Stop loss changes
            old_tp/new_tp: Take profit changes
            old_confidence/new_confidence: Confidence changes
            reason: Reason for adjustment

        Returns:
            Created adjustment record
        """
        adjustment = PositionAdjustment(
            position_id=position_id,
            adjustment_type=adjustment_type,
            old_stop_loss=old_sl,
            new_stop_loss=new_sl,
            old_take_profit=old_tp,
            new_take_profit=new_tp,
            old_confidence=old_confidence,
            new_confidence=new_confidence,
            reason=reason,
        )
        self.db.add(adjustment)
        self.db.commit()

        return adjustment

    def get_open_positions(self, session_id: int) -> list:
        """Get all open positions for a session."""
        return self.db.query(PaperPosition).filter_by(
            session_id=session_id,
            status="open"
        ).all()

    def get_session_value(self, session_id: int) -> Dict[str, float]:
        """
        Calculate total session value including positions.

        Returns:
            Dictionary with cash, invested, total values
        """
        session = self.db.query(PaperSession).filter_by(id=session_id).first()
        if not session:
            return {"cash": 0, "invested": 0, "total": 0}

        open_positions = self.get_open_positions(session_id)
        invested_value = sum(p.current_price * p.quantity for p in open_positions)

        return {
            "cash": session.current_balance,
            "invested": invested_value,
            "total": session.current_balance + invested_value,
        }
