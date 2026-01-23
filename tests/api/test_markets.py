import pytest
from unittest.mock import patch, MagicMock
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


def test_get_market_status(client):
    """Test getting market status."""
    with patch('data_service.fetchers.nse_fetcher.NSEFetcher') as mock_fetcher_class:
        mock_fetcher = MagicMock()
        mock_fetcher.is_market_open.return_value = False
        mock_fetcher_class.return_value = mock_fetcher

        # Check the endpoint returns correct structure
        response = client.get("/api/markets/status")
        assert response.status_code == 200
        data = response.json()
        assert "nse" in data
        assert "crypto" in data
        assert "is_open" in data["nse"]


def test_get_prices(client):
    """Test getting prices for watchlist."""
    with patch('data_service.fetchers.nse_fetcher.NSEFetcher') as mock_fetcher_class:
        mock_fetcher = MagicMock()
        mock_fetcher.get_current_price.return_value = 2500.0
        mock_fetcher_class.return_value = mock_fetcher

        response = client.get("/api/markets/prices?symbols=RELIANCE.NS,TCS.NS")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


def test_get_watchlist(client):
    """Test getting default watchlist."""
    response = client.get("/api/markets/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert "nse" in data
    assert "crypto" in data
    assert len(data["nse"]) > 0


def test_get_quote(client):
    """Test getting quote for a symbol."""
    with patch('data_service.fetchers.nse_fetcher.NSEFetcher') as mock_fetcher_class:
        mock_fetcher = MagicMock()
        mock_fetcher.get_current_price.return_value = 2500.0
        mock_fetcher.calculate_atr.return_value = 50.0
        mock_fetcher_class.return_value = mock_fetcher

        response = client.get("/api/markets/quote/RELIANCE.NS")
        assert response.status_code == 200
        data = response.json()
        assert "symbol" in data
        assert data["symbol"] == "RELIANCE.NS"


def test_get_quote_error(client):
    """Test getting quote when error occurs."""
    with patch('data_service.fetchers.nse_fetcher.NSEFetcher') as mock_fetcher_class:
        mock_fetcher = MagicMock()
        mock_fetcher.get_current_price.side_effect = Exception("Network error")
        mock_fetcher_class.return_value = mock_fetcher

        response = client.get("/api/markets/quote/INVALID")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data


def test_market_status_structure(client):
    """Test market status response structure."""
    response = client.get("/api/markets/status")
    assert response.status_code == 200
    data = response.json()

    # NSE market structure
    assert "market" in data["nse"]
    assert "is_open" in data["nse"]
    assert "hours" in data["nse"]
    assert "timezone" in data["nse"]

    # Crypto market structure
    assert "market" in data["crypto"]
    assert "is_open" in data["crypto"]
    assert data["crypto"]["is_open"] is True  # Crypto is always open
    assert data["crypto"]["hours"] == "24/7"


def test_prices_missing_symbols_parameter(client):
    """Test prices endpoint without symbols parameter returns 422."""
    response = client.get("/api/markets/prices")
    assert response.status_code == 422  # Validation error


def test_watchlist_contains_expected_symbols(client):
    """Test watchlist contains expected default symbols."""
    response = client.get("/api/markets/watchlist")
    assert response.status_code == 200
    data = response.json()

    # Check NSE watchlist
    assert "RELIANCE.NS" in data["nse"]
    assert "TCS.NS" in data["nse"]

    # Check crypto watchlist
    assert "BTCUSDT" in data["crypto"]
    assert "ETHUSDT" in data["crypto"]
