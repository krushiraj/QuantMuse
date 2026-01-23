import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from paper_trading.models import Base, PaperSession, PaperTrade


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
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
    """Set up test session and trades."""
    db = test_db()

    # Create session
    session = PaperSession(
        name="Test Session",
        initial_balance=100000,
        current_balance=95000,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create trades
    trades = [
        PaperTrade(session_id=session.id, position_id=1, symbol="RELIANCE.NS", market="nse",
                   trade_type="buy", quantity=100, price=2500, value=250000, commission=50, pnl=None),
        PaperTrade(session_id=session.id, position_id=1, symbol="RELIANCE.NS", market="nse",
                   trade_type="sell", quantity=100, price=2650, value=265000, commission=50, pnl=14900),
        PaperTrade(session_id=session.id, position_id=2, symbol="TCS.NS", market="nse",
                   trade_type="buy", quantity=50, price=3500, value=175000, commission=35, pnl=None),
        PaperTrade(session_id=session.id, position_id=2, symbol="TCS.NS", market="nse",
                   trade_type="sell", quantity=50, price=3400, value=170000, commission=35, pnl=-5070),
    ]
    db.add_all(trades)
    db.commit()

    session_id = session.id
    db.close()
    return session_id


def test_list_trades(client, setup_data):
    """Test listing trades."""
    session_id = setup_data
    response = client.get(f"/api/trades?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4


def test_list_trades_filter_by_type(client, setup_data):
    """Test filtering trades by type."""
    session_id = setup_data
    response = client.get(f"/api/trades?session_id={session_id}&trade_type=sell")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(t["trade_type"] == "sell" for t in data)


def test_get_trade_stats(client, setup_data):
    """Test getting trade statistics."""
    session_id = setup_data
    response = client.get(f"/api/trades/stats?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_trades"] == 4
    assert data["winning_trades"] == 1
    assert data["losing_trades"] == 1
    assert "win_rate" in data
    assert "total_pnl" in data
