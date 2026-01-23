"""Signals router for managing pending trading signals."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import SignalResponse, SignalAction, SignalCreate
from paper_trading.models import PendingSignal, PaperSession

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("", response_model=List[SignalResponse])
def list_signals(
    session_id: int = Query(..., description="Session ID"),
    status: Optional[str] = Query(None, description="Filter by status (pending/executed/rejected)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List signals for a session."""
    query = db.query(PendingSignal).filter(PendingSignal.session_id == session_id)

    if status:
        query = query.filter(PendingSignal.status == status)

    signals = query.order_by(PendingSignal.created_at.desc()).offset(skip).limit(limit).all()
    return signals


@router.get("/{signal_id}", response_model=SignalResponse)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Get a specific signal."""
    signal = db.query(PendingSignal).filter(PendingSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


@router.post("", response_model=SignalResponse, status_code=201)
def create_signal(
    session_id: int,
    signal_data: SignalCreate,
    db: Session = Depends(get_db)
):
    """Create a new signal (for testing/manual entry)."""
    session = db.query(PaperSession).filter(PaperSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    signal = PendingSignal(
        session_id=session_id,
        symbol=signal_data.symbol,
        market=signal_data.market,
        signal_type=signal_data.signal_type,
        entry_price=signal_data.entry_price,
        stop_loss=signal_data.stop_loss,
        take_profit=signal_data.take_profit,
        confidence=signal_data.confidence,
        strategy=signal_data.strategy,
        status="pending",
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


@router.post("/{signal_id}/action", response_model=SignalResponse)
def signal_action(
    signal_id: int,
    action_data: SignalAction,
    db: Session = Depends(get_db)
):
    """Approve or reject a signal."""
    signal = db.query(PendingSignal).filter(PendingSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    if signal.status != "pending":
        raise HTTPException(status_code=400, detail=f"Signal already {signal.status}")

    if action_data.action == "approve":
        signal.status = "executed"
        signal.reviewed_at = datetime.now()
        # TODO: Create position via paper executor
    elif action_data.action == "reject":
        signal.status = "rejected"
        signal.reviewed_at = datetime.now()

    db.commit()
    db.refresh(signal)
    return signal
