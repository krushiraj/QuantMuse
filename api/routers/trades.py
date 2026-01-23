"""Trades router for trade history and statistics."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import TradeResponse, TradeStats
from paper_trading.models import PaperTrade

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("", response_model=List[TradeResponse])
def list_trades(
    session_id: int = Query(..., description="Session ID"),
    trade_type: Optional[str] = Query(None, description="Filter by type (buy/sell)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List trades for a session."""
    query = db.query(PaperTrade).filter(PaperTrade.session_id == session_id)

    if trade_type:
        query = query.filter(PaperTrade.trade_type == trade_type)
    if symbol:
        query = query.filter(PaperTrade.symbol == symbol)

    trades = query.order_by(PaperTrade.timestamp.desc()).offset(skip).limit(limit).all()
    return trades


@router.get("/stats", response_model=TradeStats)
def get_trade_stats(
    session_id: int = Query(..., description="Session ID"),
    db: Session = Depends(get_db)
):
    """Get trade statistics for a session."""
    # Get all sell trades (which have P&L)
    sell_trades = db.query(PaperTrade).filter(
        PaperTrade.session_id == session_id,
        PaperTrade.trade_type == "sell"
    ).all()

    # Count all trades
    total_trades = db.query(PaperTrade).filter(
        PaperTrade.session_id == session_id
    ).count()

    # Calculate stats
    winning_trades = [t for t in sell_trades if t.pnl and t.pnl > 0]
    losing_trades = [t for t in sell_trades if t.pnl and t.pnl < 0]

    total_pnl = sum(t.pnl or 0 for t in sell_trades)

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    completed_trades = win_count + loss_count

    win_rate = (win_count / completed_trades * 100) if completed_trades > 0 else 0

    avg_win = sum(t.pnl for t in winning_trades) / win_count if win_count > 0 else 0
    avg_loss = sum(t.pnl for t in losing_trades) / loss_count if loss_count > 0 else 0

    largest_win = max((t.pnl for t in winning_trades), default=0)
    largest_loss = min((t.pnl for t in losing_trades), default=0)

    return TradeStats(
        total_trades=total_trades,
        winning_trades=win_count,
        losing_trades=loss_count,
        win_rate=win_rate,
        total_pnl=total_pnl,
        avg_win=avg_win,
        avg_loss=avg_loss,
        largest_win=largest_win,
        largest_loss=largest_loss,
    )
