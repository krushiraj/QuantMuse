"""Sessions router for managing trading sessions."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import SessionCreate, SessionResponse, SessionSummary
from paper_trading.models import PaperSession, PaperPosition, PaperTrade

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(session_data: SessionCreate, db: Session = Depends(get_db)):
    """Create a new trading session."""
    session = PaperSession(
        name=session_data.name,
        initial_balance=session_data.initial_balance,
        current_balance=session_data.initial_balance,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=List[SessionResponse])
def list_sessions(
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all trading sessions."""
    query = db.query(PaperSession)
    if status:
        query = query.filter(PaperSession.status == status)
    return query.offset(skip).limit(limit).all()


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get a specific session by ID."""
    session = db.query(PaperSession).filter(PaperSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/summary", response_model=SessionSummary)
def get_session_summary(session_id: int, db: Session = Depends(get_db)):
    """Get session summary with portfolio statistics."""
    session = db.query(PaperSession).filter(PaperSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get open positions
    open_positions = db.query(PaperPosition).filter(
        PaperPosition.session_id == session_id,
        PaperPosition.status == "open"
    ).all()

    # Calculate invested value
    invested_value = sum(p.quantity * p.entry_price for p in open_positions)

    # Calculate unrealized P&L
    unrealized_pnl = sum(p.unrealized_pnl for p in open_positions)

    # Get total trades
    total_trades = db.query(PaperTrade).filter(
        PaperTrade.session_id == session_id
    ).count()

    # Calculate portfolio value
    portfolio_value = session.current_balance + invested_value + unrealized_pnl

    # Calculate total P&L
    total_pnl = portfolio_value - session.initial_balance
    total_pnl_pct = (total_pnl / session.initial_balance) * 100 if session.initial_balance > 0 else 0

    return SessionSummary(
        id=session.id,
        name=session.name,
        initial_balance=session.initial_balance,
        current_balance=session.current_balance,
        portfolio_value=portfolio_value,
        cash_balance=session.current_balance,
        invested_value=invested_value,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        open_positions=len(open_positions),
        total_trades=total_trades,
        status=session.status,
    )


@router.patch("/{session_id}/end")
def end_session(session_id: int, db: Session = Depends(get_db)):
    """End a trading session."""
    session = db.query(PaperSession).filter(PaperSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "ended"
    db.commit()
    return {"message": "Session ended", "session_id": session_id}
