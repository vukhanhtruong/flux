"""E2E tests for budget API routes with seeded SQLite+zvec."""
TEST_USER_ID = "test:e2e-user"


def test_set_and_list_budgets(seeded_app):
    """POST create budget then GET list."""
    # Set budget
    resp = seeded_app.post(
        "/budgets/",
        params={
            "user_id": TEST_USER_ID,
            "category": "Food",
            "monthly_limit": 500.00,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "Food"
    assert float(data["monthly_limit"]) == 500.00

    # List
    list_resp = seeded_app.get(f"/budgets/?user_id={TEST_USER_ID}")
    assert list_resp.status_code == 200
    budgets = list_resp.json()
    assert len(budgets) >= 1
    assert any(b["category"] == "Food" for b in budgets)


def test_set_and_delete_budget(seeded_app):
    """Create then delete a budget."""
    seeded_app.post(
        "/budgets/",
        params={
            "user_id": TEST_USER_ID,
            "category": "Transport",
            "monthly_limit": 200.00,
        },
    )

    # Delete
    del_resp = seeded_app.delete(
        f"/budgets/Transport?user_id={TEST_USER_ID}"
    )
    assert del_resp.status_code == 204

    # Verify gone
    list_resp = seeded_app.get(f"/budgets/?user_id={TEST_USER_ID}")
    categories = [b["category"] for b in list_resp.json()]
    assert "Transport" not in categories


def test_update_budget_same_category(seeded_app):
    """Setting budget for same category should update (upsert)."""
    seeded_app.post(
        "/budgets/",
        params={
            "user_id": TEST_USER_ID,
            "category": "Health",
            "monthly_limit": 100.00,
        },
    )
    # Update same category
    resp = seeded_app.post(
        "/budgets/",
        params={
            "user_id": TEST_USER_ID,
            "category": "Health",
            "monthly_limit": 300.00,
        },
    )
    assert resp.status_code == 201
    assert float(resp.json()["monthly_limit"]) == 300.00

    # Only one Health budget
    list_resp = seeded_app.get(f"/budgets/?user_id={TEST_USER_ID}")
    health_budgets = [b for b in list_resp.json() if b["category"] == "Health"]
    assert len(health_budgets) == 1
