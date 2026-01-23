"""Performance router for analytics and metrics."""
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import DailyPerformanceResponse, PerformanceMetrics
from paper_trading.models import DailyPerformance, PaperSession, PaperTrade

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/daily", response_model=List[DailyPerformanceResponse])
def get_daily_performance(
    session_id: int = Query(..., description="Session ID"),
    days: int = Query(30, description="Number of days to return"),
    db: Session = Depends(get_db)
):
    """Get daily performance snapshots."""
    cutoff_date = datetime.now() - timedelta(days=days)

    snapshots = db.query(DailyPerformance).filter(
        DailyPerformance.session_id == session_id,
        DailyPerformance.date >= cutoff_date
    ).order_by(DailyPerformance.date.asc()).all()

    return snapshots


@router.get("/metrics", response_model=PerformanceMetrics)
def get_performance_metrics(
    session_id: int = Query(..., description="Session ID"),
    db: Session = Depends(get_db)
):
    """Calculate overall performance metrics."""
    session = db.query(PaperSession).filter(PaperSession.id == session_id).first()
    if not session:
        return PerformanceMetrics(
            total_return_pct=0, win_rate=0, total_trades=0,
            winning_trades=0, losing_trades=0, avg_win_pct=0,
            avg_loss_pct=0, profit_factor=0, max_drawdown_pct=0
        )

    # Get all completed trades (sells with P&L)
    sell_trades = db.query(PaperTrade).filter(
        PaperTrade.session_id == session_id,
        PaperTrade.trade_type == "sell",
        PaperTrade.pnl.isnot(None)
    ).all()

    total_trades = db.query(PaperTrade).filter(
        PaperTrade.session_id == session_id
    ).count()

    winning = [t for t in sell_trades if t.pnl > 0]
    losing = [t for t in sell_trades if t.pnl < 0]

    win_count = len(winning)
    loss_count = len(losing)
    completed = win_count + loss_count

    # Calculate metrics
    total_return_pct = ((session.current_balance - session.initial_balance)
                        / session.initial_balance * 100) if session.initial_balance > 0 else 0

    win_rate = (win_count / completed * 100) if completed > 0 else 0

    total_wins = sum(t.pnl for t in winning)
    total_losses = abs(sum(t.pnl for t in losing))

    avg_win = total_wins / win_count if win_count > 0 else 0
    avg_loss = total_losses / loss_count if loss_count > 0 else 0

    # Approximate percentages
    avg_win_pct = (avg_win / session.initial_balance * 100) if session.initial_balance > 0 else 0
    avg_loss_pct = (-avg_loss / session.initial_balance * 100) if session.initial_balance > 0 else 0

    profit_factor = (total_wins / total_losses) if total_losses > 0 else (float('inf') if total_wins > 0 else 0)

    # Get max drawdown from daily snapshots
    snapshots = db.query(DailyPerformance).filter(
        DailyPerformance.session_id == session_id
    ).all()
    max_drawdown = max((s.drawdown_pct for s in snapshots), default=0)

    return PerformanceMetrics(
        total_return_pct=total_return_pct,
        win_rate=win_rate,
        total_trades=total_trades,
        winning_trades=win_count,
        losing_trades=loss_count,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        profit_factor=profit_factor if profit_factor != float('inf') else 999.99,
        max_drawdown_pct=max_drawdown,
    )
