"""Tests for performance tracker."""
import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from paper_trading.models import Base, PaperSession, PaperPosition, PaperTrade, DailyPerformance
from paper_trading.performance_tracker import PerformanceTracker


@pytest.fixture
def db():
    """Create test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def setup_session(db):
    """Create test session with data."""
    session = PaperSession(
        name="Test Session",
        initial_balance=100000,
        current_balance=90000,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Add a position
    position = PaperPosition(
        session_id=session.id,
        symbol="RELIANCE.NS",
        market="nse",
        direction="long",
        quantity=100,
        entry_price=2500.0,
        current_price=2600.0,
        stop_loss=2375.0,
        take_profit=2875.0,
        status="open",
    )
    db.add(position)
    db.commit()

    return session


@pytest.fixture
def tracker(db):
    """Create performance tracker."""
    return PerformanceTracker(db)


def test_record_daily_snapshot(db, setup_session, tracker):
    """Test recording a daily snapshot."""
    snapshot = tracker.record_daily_snapshot(setup_session.id)

    assert snapshot is not None
    assert snapshot.session_id == setup_session.id
    assert snapshot.portfolio_value > 0
    assert snapshot.num_positions == 1


def test_snapshot_updates_existing(db, setup_session, tracker):
    """Test that snapshot updates existing record for same day."""
    snapshot1 = tracker.record_daily_snapshot(setup_session.id)
    snapshot2 = tracker.record_daily_snapshot(setup_session.id)

    assert snapshot1.id == snapshot2.id


def test_calculate_drawdown(db, setup_session, tracker):
    """Test drawdown calculation."""
    # Create some historical snapshots with higher values
    for i in range(5):
        perf = DailyPerformance(
            session_id=setup_session.id,
            date=date.today() - timedelta(days=5-i),
            portfolio_value=100000 + (i * 5000),  # Peak at 120000
            cash_balance=50000,
            invested_value=50000,
            daily_pnl=5000,
            daily_return_pct=5.0,
            cumulative_return_pct=i * 5.0,
            drawdown_pct=0,
            num_positions=1,
            num_trades=0,
        )
        db.add(perf)
    db.commit()

    # Current value below peak
    drawdown = tracker._calculate_drawdown(setup_session.id, 110000)
    assert drawdown > 0  # Should show drawdown from peak


def test_calculate_metrics(db, setup_session, tracker):
    """Test metrics calculation."""
    # Add some closed trades
    trades = [
        PaperTrade(session_id=setup_session.id, position_id=1, symbol="A",
                   market="nse", trade_type="sell", quantity=10, price=110, value=1100,
                   commission=1, pnl=100),
        PaperTrade(session_id=setup_session.id, position_id=2, symbol="B",
                   market="nse", trade_type="sell", quantity=10, price=90, value=900,
                   commission=1, pnl=-100),
    ]
    db.add_all(trades)
    db.commit()

    metrics = tracker.calculate_metrics(setup_session.id)

    assert "total_return_pct" in metrics
    assert "win_rate" in metrics
    assert metrics["winning_trades"] == 1
    assert metrics["losing_trades"] == 1
    assert metrics["win_rate"] == 50.0


def test_get_equity_curve(db, setup_session, tracker):
    """Test equity curve retrieval."""
    # Add daily snapshots
    for i in range(10):
        perf = DailyPerformance(
            session_id=setup_session.id,
            date=date.today() - timedelta(days=9-i),
            portfolio_value=100000 + (i * 1000),
            cash_balance=50000,
            invested_value=50000,
            daily_pnl=1000,
            daily_return_pct=1.0,
            cumulative_return_pct=i * 1.0,
            drawdown_pct=0,
            num_positions=1,
            num_trades=1,
        )
        db.add(perf)
    db.commit()

    curve = tracker.get_equity_curve(setup_session.id, days=30)

    assert len(curve) == 10
    assert curve[0]["date"] is not None
    assert curve[-1]["portfolio_value"] > curve[0]["portfolio_value"]
