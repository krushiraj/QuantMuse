"""Positions router for managing trading positions."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import PositionResponse, PositionClose
from paper_trading.models import PaperPosition, PaperSession, PaperTrade, PositionAdjustment

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("", response_model=List[PositionResponse])
def list_positions(
    session_id: int = Query(..., description="Session ID to filter positions"),
    status: Optional[str] = Query(None, description="Filter by status (open/closed)"),
    market: Optional[str] = Query(None, description="Filter by market (nse/crypto)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List positions for a session."""
    query = db.query(PaperPosition).filter(PaperPosition.session_id == session_id)

    if status:
        query = query.filter(PaperPosition.status == status)
    if market:
        query = query.filter(PaperPosition.market == market)

    positions = query.offset(skip).limit(limit).all()

    # Add computed fields
    result = []
    for pos in positions:
        pos_dict = {
            "id": pos.id,
            "session_id": pos.session_id,
            "symbol": pos.symbol,
            "market": pos.market,
            "direction": pos.direction,
            "quantity": pos.quantity,
            "entry_price": pos.entry_price,
            "current_price": pos.current_price,
            "stop_loss": pos.stop_loss,
            "take_profit": pos.take_profit,
            "trailing_stop": pos.trailing_stop,
            "status": pos.status,
            "opened_at": pos.opened_at,
            "closed_at": pos.closed_at,
            "close_reason": pos.close_reason,
            "unrealized_pnl": pos.unrealized_pnl,
            "unrealized_pnl_pct": (pos.unrealized_pnl / (pos.entry_price * pos.quantity)) * 100 if pos.entry_price and pos.quantity else 0,
        }
        result.append(pos_dict)

    return result


@router.get("/{position_id}", response_model=PositionResponse)
def get_position(position_id: int, db: Session = Depends(get_db)):
    """Get a specific position by ID."""
    position = db.query(PaperPosition).filter(PaperPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    return {
        "id": position.id,
        "session_id": position.session_id,
        "symbol": position.symbol,
        "market": position.market,
        "direction": position.direction,
        "quantity": position.quantity,
        "entry_price": position.entry_price,
        "current_price": position.current_price,
        "stop_loss": position.stop_loss,
        "take_profit": position.take_profit,
        "trailing_stop": position.trailing_stop,
        "status": position.status,
        "opened_at": position.opened_at,
        "closed_at": position.closed_at,
        "close_reason": position.close_reason,
        "unrealized_pnl": position.unrealized_pnl,
        "unrealized_pnl_pct": (position.unrealized_pnl / (position.entry_price * position.quantity)) * 100 if position.entry_price and position.quantity else 0,
    }


@router.post("/{position_id}/close", response_model=PositionResponse)
def close_position(
    position_id: int,
    close_data: PositionClose,
    db: Session = Depends(get_db)
):
    """Manually close a position."""
    position = db.query(PaperPosition).filter(PaperPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    if position.status == "closed":
        raise HTTPException(status_code=400, detail="Position already closed")

    # Determine close price
    close_price = close_data.close_price or position.current_price

    # Calculate P&L
    if position.direction in ("long", "BUY"):
        pnl = (close_price - position.entry_price) * position.quantity
    else:  # short or SELL
        pnl = (position.entry_price - close_price) * position.quantity

    # Update position
    position.status = "closed"
    position.close_reason = close_data.reason
    position.closed_at = datetime.now()
    position.current_price = close_price

    # Update session balance
    session = db.query(PaperSession).filter(PaperSession.id == position.session_id).first()
    if session:
        # Return capital + P&L
        session.current_balance += (position.entry_price * position.quantity) + pnl

    # Create sell trade record
    trade = PaperTrade(
        session_id=position.session_id,
        position_id=position.id,
        symbol=position.symbol,
        market=position.market,
        trade_type="sell",
        quantity=position.quantity,
        price=close_price,
        value=close_price * position.quantity,
        commission=0,
        pnl=pnl,
    )
    db.add(trade)

    db.commit()
    db.refresh(position)

    return {
        "id": position.id,
        "session_id": position.session_id,
        "symbol": position.symbol,
        "market": position.market,
        "direction": position.direction,
        "quantity": position.quantity,
        "entry_price": position.entry_price,
        "current_price": position.current_price,
        "stop_loss": position.stop_loss,
        "take_profit": position.take_profit,
        "trailing_stop": position.trailing_stop,
        "status": position.status,
        "opened_at": position.opened_at,
        "closed_at": position.closed_at,
        "close_reason": position.close_reason,
        "unrealized_pnl": 0,
        "unrealized_pnl_pct": 0,
    }


@router.get("/{position_id}/history")
def get_position_history(position_id: int, db: Session = Depends(get_db)):
    """Get adjustment history for a position."""
    position = db.query(PaperPosition).filter(PaperPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    adjustments = db.query(PositionAdjustment).filter(
        PositionAdjustment.position_id == position_id
    ).order_by(PositionAdjustment.timestamp.desc()).all()

    return [
        {
            "id": adj.id,
            "adjustment_type": adj.adjustment_type,
            "old_stop_loss": adj.old_stop_loss,
            "new_stop_loss": adj.new_stop_loss,
            "old_take_profit": adj.old_take_profit,
            "new_take_profit": adj.new_take_profit,
            "reason": adj.reason,
            "timestamp": adj.timestamp,
        }
        for adj in adjustments
    ]
