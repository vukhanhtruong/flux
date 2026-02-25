"""Test FastAPI application setup."""
from fastapi.testclient import TestClient

from flux_api.app import app

client = TestClient(app)


def test_health_check():
    """Verify health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
