import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from paper_trading.models import Base


@pytest.fixture
def test_db():
    """Create a test database."""
    # Use StaticPool to keep the same connection for in-memory SQLite
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


def test_create_session(client):
    """Test creating a new trading session."""
    response = client.post(
        "/api/sessions",
        json={"name": "Test Session", "initial_balance": 100000}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Session"
    assert data["initial_balance"] == 100000
    assert data["status"] == "active"
    assert "id" in data


def test_list_sessions(client):
    """Test listing all sessions."""
    # Create two sessions
    client.post("/api/sessions", json={"name": "Session 1", "initial_balance": 100000})
    client.post("/api/sessions", json={"name": "Session 2", "initial_balance": 200000})

    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_session(client):
    """Test getting a specific session."""
    create_resp = client.post(
        "/api/sessions",
        json={"name": "Test Session", "initial_balance": 100000}
    )
    session_id = create_resp.json()["id"]

    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Session"


def test_get_session_not_found(client):
    """Test getting non-existent session returns 404."""
    response = client.get("/api/sessions/999")
    assert response.status_code == 404


def test_get_session_summary(client):
    """Test getting session summary with portfolio stats."""
    create_resp = client.post(
        "/api/sessions",
        json={"name": "Test Session", "initial_balance": 100000}
    )
    session_id = create_resp.json()["id"]

    response = client.get(f"/api/sessions/{session_id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert "portfolio_value" in data
    assert "open_positions" in data
    assert "total_pnl" in data
