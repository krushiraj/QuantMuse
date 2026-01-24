import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from paper_trading.models import Base


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


def test_websocket_connect(client):
    """Test WebSocket connection."""
    with client.websocket_connect("/api/ws") as websocket:
        # Send subscription message
        websocket.send_json({"type": "subscribe", "session_id": 1})

        # Should receive acknowledgment
        data = websocket.receive_json()
        assert data["type"] == "subscribed"


def test_websocket_ping_pong(client):
    """Test WebSocket ping/pong."""
    with client.websocket_connect("/api/ws") as websocket:
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data["type"] == "pong"


def test_websocket_manager_broadcast():
    """Test WebSocket manager broadcast function."""
    from api.websocket import ConnectionManager

    manager = ConnectionManager()
    # Verify manager can be instantiated and has broadcast method
    assert manager is not None
    assert hasattr(manager, 'broadcast')
    assert hasattr(manager, 'connect')
    assert hasattr(manager, 'disconnect')
