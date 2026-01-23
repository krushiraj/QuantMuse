import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from paper_trading.models import Base, PaperSession, DailyPerformance, PaperTrade


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal


@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    from api.main import app
    from api.dependencies import get_db

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def setup_data(test_db):
    """Set up test session with performance data."""
    db = test_db()

    # Create session
    session = PaperSession(
        name="Test Session",
        initial_balance=100000,
        current_balance=112000,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create daily performance snapshots
    today = datetime.now().date()
    for i in range(5):
        perf = DailyPerformance(
            session_id=session.id,
            date=today - timedelta(days=4-i),
            portfolio_value=100000 + (i * 3000),
            cash_balance=50000,
            invested_value=50000 + (i * 3000),
            daily_pnl=3000 if i > 0 else 0,
            daily_return_pct=3.0 if i > 0 else 0,
            cumulative_return_pct=i * 3.0,
            drawdown_pct=0,
            num_positions=2,
            num_trades=i * 2,
        )
        db.add(perf)

    # Create trades for metrics
    trades = [
        PaperTrade(session_id=session.id, position_id=1, symbol="A", market="nse",
                   trade_type="sell", quantity=10, price=100, value=1000, commission=1, pnl=500),
        PaperTrade(session_id=session.id, position_id=2, symbol="B", market="nse",
                   trade_type="sell", quantity=10, price=100, value=1000, commission=1, pnl=800),
        PaperTrade(session_id=session.id, position_id=3, symbol="C", market="nse",
                   trade_type="sell", quantity=10, price=100, value=1000, commission=1, pnl=-200),
    ]
    db.add_all(trades)
    db.commit()

    session_id = session.id
    db.close()
    return session_id


def test_get_daily_performance(client, setup_data):
    """Test getting daily performance data."""
    session_id = setup_data
    response = client.get(f"/api/performance/daily?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


def test_get_performance_metrics(client, setup_data):
    """Test getting performance metrics."""
    session_id = setup_data
    response = client.get(f"/api/performance/metrics?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert "total_return_pct" in data
    assert "win_rate" in data
    assert "max_drawdown_pct" in data
    assert data["winning_trades"] == 2
    assert data["losing_trades"] == 1
