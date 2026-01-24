"""Performance tracker for recording daily snapshots and calculating metrics."""
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import math

from paper_trading.models import (
    DailyPerformance,
    PaperSession,
    PaperPosition,
    PaperTrade,
)


class PerformanceTracker:
    """Track and record trading performance metrics."""

    def __init__(self, db: Session):
        self.db = db

    def record_daily_snapshot(
        self,
        session_id: int,
        snapshot_date: Optional[date] = None,
    ) -> DailyPerformance:
        """
        Record a daily performance snapshot for a session.

        Args:
            session_id: Trading session ID
            snapshot_date: Date for snapshot (defaults to today)

        Returns:
            Created DailyPerformance record
        """
        snapshot_date = snapshot_date or date.today()

        # Get session
        session = self.db.query(PaperSession).filter(
            PaperSession.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get open positions
        open_positions = self.db.query(PaperPosition).filter(
            PaperPosition.session_id == session_id,
            PaperPosition.status == "open"
        ).all()

        # Calculate values
        invested_value = sum(p.quantity * p.entry_price for p in open_positions)
        unrealized_pnl = sum(p.unrealized_pnl for p in open_positions)
        portfolio_value = session.current_balance + invested_value + unrealized_pnl

        # Get today's trades
        today_start = datetime.combine(snapshot_date, datetime.min.time())
        today_end = datetime.combine(snapshot_date, datetime.max.time())

        today_trades = self.db.query(PaperTrade).filter(
            PaperTrade.session_id == session_id,
            PaperTrade.timestamp >= today_start,
            PaperTrade.timestamp <= today_end
        ).count()

        # Get previous snapshot for daily P&L calculation
        prev_snapshot = self.db.query(DailyPerformance).filter(
            DailyPerformance.session_id == session_id,
            DailyPerformance.date < snapshot_date
        ).order_by(DailyPerformance.date.desc()).first()

        if prev_snapshot:
            daily_pnl = portfolio_value - prev_snapshot.portfolio_value
            daily_return_pct = (daily_pnl / prev_snapshot.portfolio_value) * 100
        else:
            daily_pnl = portfolio_value - session.initial_balance
            daily_return_pct = (daily_pnl / session.initial_balance) * 100

        # Calculate cumulative return
        cumulative_return_pct = ((portfolio_value - session.initial_balance)
                                 / session.initial_balance * 100)

        # Calculate drawdown
        drawdown_pct = self._calculate_drawdown(session_id, portfolio_value)

        # Check for existing snapshot (compare as datetime range since date column is DateTime)
        snapshot_datetime = datetime.combine(snapshot_date, datetime.min.time())
        existing = self.db.query(DailyPerformance).filter(
            DailyPerformance.session_id == session_id,
            DailyPerformance.date >= snapshot_datetime,
            DailyPerformance.date < snapshot_datetime + timedelta(days=1)
        ).first()

        if existing:
            # Update existing
            existing.portfolio_value = portfolio_value
            existing.cash_balance = session.current_balance
            existing.invested_value = invested_value
            existing.daily_pnl = daily_pnl
            existing.daily_return_pct = daily_return_pct
            existing.cumulative_return_pct = cumulative_return_pct
            existing.drawdown_pct = drawdown_pct
            existing.num_positions = len(open_positions)
            existing.num_trades = today_trades
            self.db.commit()
            return existing

        # Create new snapshot
        snapshot = DailyPerformance(
            session_id=session_id,
            date=snapshot_datetime,
            portfolio_value=portfolio_value,
            cash_balance=session.current_balance,
            invested_value=invested_value,
            daily_pnl=daily_pnl,
            daily_return_pct=daily_return_pct,
            cumulative_return_pct=cumulative_return_pct,
            drawdown_pct=drawdown_pct,
            num_positions=len(open_positions),
            num_trades=today_trades,
        )

        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)

        return snapshot

    def _calculate_drawdown(self, session_id: int, current_value: float) -> float:
        """Calculate current drawdown from peak."""
        # Get historical peak
        max_value = self.db.query(func.max(DailyPerformance.portfolio_value)).filter(
            DailyPerformance.session_id == session_id
        ).scalar()

        if not max_value or current_value >= max_value:
            return 0.0

        drawdown = ((max_value - current_value) / max_value) * 100
        return drawdown

    def calculate_metrics(self, session_id: int) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.

        Args:
            session_id: Trading session ID

        Returns:
            Dict of performance metrics
        """
        session = self.db.query(PaperSession).filter(
            PaperSession.id == session_id
        ).first()

        if not session:
            return {}

        # Get all sell trades (completed trades)
        sell_trades = self.db.query(PaperTrade).filter(
            PaperTrade.session_id == session_id,
            PaperTrade.trade_type == "sell",
            PaperTrade.pnl.isnot(None)
        ).all()

        winning = [t for t in sell_trades if t.pnl > 0]
        losing = [t for t in sell_trades if t.pnl < 0]

        win_count = len(winning)
        loss_count = len(losing)
        total_completed = win_count + loss_count

        # Basic stats
        total_pnl = sum(t.pnl for t in sell_trades)
        total_return_pct = (total_pnl / session.initial_balance * 100) if session.initial_balance else 0
        win_rate = (win_count / total_completed * 100) if total_completed > 0 else 0

        # Win/loss averages
        avg_win = sum(t.pnl for t in winning) / win_count if win_count > 0 else 0
        avg_loss = abs(sum(t.pnl for t in losing) / loss_count) if loss_count > 0 else 0

        total_wins = sum(t.pnl for t in winning)
        total_losses = abs(sum(t.pnl for t in losing))

        # Profit factor
        profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf')

        # Get daily returns for risk metrics
        daily_snapshots = self.db.query(DailyPerformance).filter(
            DailyPerformance.session_id == session_id
        ).order_by(DailyPerformance.date).all()

        daily_returns = [s.daily_return_pct for s in daily_snapshots if s.daily_return_pct is not None]

        # Sharpe ratio (assuming 5% risk-free rate annually, ~0.02% daily)
        sharpe_ratio = None
        if len(daily_returns) > 1:
            avg_return = sum(daily_returns) / len(daily_returns)
            std_dev = math.sqrt(sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns))
            if std_dev > 0:
                risk_free_daily = 0.02
                sharpe_ratio = (avg_return - risk_free_daily) / std_dev * math.sqrt(252)

        # Max drawdown
        max_drawdown = max((s.drawdown_pct for s in daily_snapshots), default=0)

        # Sortino ratio (downside deviation)
        sortino_ratio = None
        negative_returns = [r for r in daily_returns if r < 0]
        if negative_returns and len(daily_returns) > 1:
            avg_return = sum(daily_returns) / len(daily_returns)
            downside_dev = math.sqrt(sum(r ** 2 for r in negative_returns) / len(negative_returns))
            if downside_dev > 0:
                sortino_ratio = (avg_return - 0.02) / downside_dev * math.sqrt(252)

        # Calmar ratio
        calmar_ratio = None
        if max_drawdown > 0:
            annualized_return = total_return_pct * (252 / max(len(daily_snapshots), 1))
            calmar_ratio = annualized_return / max_drawdown

        return {
            "total_return_pct": total_return_pct,
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "total_trades": len(sell_trades) * 2,  # Buy + Sell
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_win_pct": (avg_win / session.initial_balance * 100) if session.initial_balance else 0,
            "avg_loss_pct": (-avg_loss / session.initial_balance * 100) if session.initial_balance else 0,
            "profit_factor": min(profit_factor, 999.99),
            "max_drawdown_pct": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "largest_win": max((t.pnl for t in winning), default=0),
            "largest_loss": min((t.pnl for t in losing), default=0),
        }

    def get_equity_curve(
        self,
        session_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get equity curve data for charting."""
        cutoff = date.today() - timedelta(days=days)

        snapshots = self.db.query(DailyPerformance).filter(
            DailyPerformance.session_id == session_id,
            DailyPerformance.date >= cutoff
        ).order_by(DailyPerformance.date).all()

        return [
            {
                "date": s.date.isoformat(),
                "portfolio_value": s.portfolio_value,
                "daily_pnl": s.daily_pnl,
                "cumulative_return_pct": s.cumulative_return_pct,
                "drawdown_pct": s.drawdown_pct,
            }
            for s in snapshots
        ]
