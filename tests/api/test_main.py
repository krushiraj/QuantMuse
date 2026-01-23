import pytest
from fastapi.testclient import TestClient


def test_app_health_check():
    """Test that the API health endpoint returns OK."""
    from api.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_app_has_cors_enabled():
    """Test that CORS is configured."""
    from api.main import app
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )
    assert "access-control-allow-origin" in response.headers
