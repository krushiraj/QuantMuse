import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from paper_trading.models import Base, PaperSession, PaperPosition


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
    """Set up test session and positions."""
    db = test_db()

    # Create session
    session = PaperSession(
        name="Test Session",
        initial_balance=100000,
        current_balance=90000,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create positions
    pos1 = PaperPosition(
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
    pos2 = PaperPosition(
        session_id=session.id,
        symbol="TCS.NS",
        market="nse",
        direction="long",
        quantity=50,
        entry_price=3500.0,
        current_price=3400.0,
        stop_loss=3325.0,
        take_profit=4025.0,
        status="open",
    )
    db.add_all([pos1, pos2])
    db.commit()

    session_id = session.id
    db.close()
    return session_id


def test_list_positions(client, setup_data):
    """Test listing open positions."""
    session_id = setup_data
    response = client.get(f"/api/positions?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_positions_filter_by_status(client, setup_data):
    """Test filtering positions by status."""
    session_id = setup_data
    response = client.get(f"/api/positions?session_id={session_id}&status=open")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(p["status"] == "open" for p in data)


def test_get_position(client, setup_data):
    """Test getting a specific position."""
    session_id = setup_data
    list_resp = client.get(f"/api/positions?session_id={session_id}")
    position_id = list_resp.json()[0]["id"]

    response = client.get(f"/api/positions/{position_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "RELIANCE.NS"
    assert "unrealized_pnl" in data


def test_close_position(client, setup_data):
    """Test closing a position manually."""
    session_id = setup_data
    list_resp = client.get(f"/api/positions?session_id={session_id}")
    position_id = list_resp.json()[0]["id"]

    response = client.post(
        f"/api/positions/{position_id}/close",
        json={"reason": "manual", "close_price": 2650.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"
    assert data["close_reason"] == "manual"
