import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from paper_trading.models import Base, PaperSession, PendingSignal


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
    """Set up test session and signals."""
    db = test_db()

    # Create session
    session = PaperSession(
        name="Test Session",
        initial_balance=100000,
        current_balance=100000,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create signals
    signals = [
        PendingSignal(
            session_id=session.id, symbol="RELIANCE.NS", market="nse",
            signal_type="BUY", entry_price=2500, stop_loss=2375, take_profit=2875,
            confidence=0.85, strategy="MomentumStrategy", status="pending"
        ),
        PendingSignal(
            session_id=session.id, symbol="TCS.NS", market="nse",
            signal_type="BUY", entry_price=3500, stop_loss=3325, take_profit=4025,
            confidence=0.72, strategy="MultiFactorStrategy", status="pending"
        ),
    ]
    db.add_all(signals)
    db.commit()

    session_id = session.id
    db.close()
    return session_id


def test_list_signals(client, setup_data):
    """Test listing pending signals."""
    session_id = setup_data
    response = client.get(f"/api/signals?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_signals_filter_by_status(client, setup_data):
    """Test filtering signals by status."""
    session_id = setup_data
    response = client.get(f"/api/signals?session_id={session_id}&status=pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_approve_signal(client, setup_data):
    """Test approving a signal."""
    session_id = setup_data
    list_resp = client.get(f"/api/signals?session_id={session_id}")
    signal_id = list_resp.json()[0]["id"]

    response = client.post(
        f"/api/signals/{signal_id}/action",
        json={"action": "approve"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "executed"


def test_reject_signal(client, setup_data):
    """Test rejecting a signal."""
    session_id = setup_data
    list_resp = client.get(f"/api/signals?session_id={session_id}")
    signal_id = list_resp.json()[1]["id"]

    response = client.post(
        f"/api/signals/{signal_id}/action",
        json={"action": "reject"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
