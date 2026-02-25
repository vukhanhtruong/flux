"""Test all routes are registered."""
from fastapi.testclient import TestClient

from flux_api.app import app

client = TestClient(app)


def test_all_routes_registered():
    """Verify all expected routes are registered in the app."""
    routes = [route.path for route in app.routes]

    # Health check
    assert "/health" in routes

    # Transactions
    assert "/transactions/" in routes
    assert "/transactions/{transaction_id}" in routes

    # Budgets
    assert "/budgets/" in routes
    assert "/budgets/{budget_id}" in routes

    # Goals
    assert "/goals/" in routes
    assert "/goals/{goal_id}" in routes

    # Subscriptions
    assert "/subscriptions/" in routes
    assert "/subscriptions/{subscription_id}" in routes

    # Assets
    assert "/assets/" in routes
    assert "/assets/{asset_id}" in routes

    # Analytics
    assert "/analytics/spending-report" in routes
    assert "/analytics/financial-health" in routes


def test_openapi_docs_available():
    """Verify OpenAPI documentation is generated."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi_spec = response.json()
    assert openapi_spec["info"]["title"] == "flux API"

    # Verify all paths are documented
    paths = openapi_spec["paths"]
    assert "/transactions/" in paths
    assert "/budgets/" in paths
    assert "/goals/" in paths
    assert "/subscriptions/" in paths
    assert "/assets/" in paths
    assert "/analytics/spending-report" in paths
    assert "/analytics/financial-health" in paths
