"""E2E tests for transaction API routes with seeded SQLite+zvec."""
TEST_USER_ID = "test:e2e-user"


def test_create_transaction(seeded_app):
    """POST /transactions/ creates a transaction in seeded DB."""
    response = seeded_app.post(
        "/transactions/",
        params={
            "user_id": TEST_USER_ID,
            "date_str": "2026-03-01",
            "amount": 42.50,
            "category": "Food",
            "description": "Lunch at restaurant",
            "transaction_type": "expense",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == TEST_USER_ID
    assert data["category"] == "Food"
    assert float(data["amount"]) == 42.50
    assert data["type"] == "expense"


def test_create_and_list_transactions(seeded_app):
    """Full flow: POST create then GET list."""
    # Create two transactions
    seeded_app.post(
        "/transactions/",
        params={
            "user_id": TEST_USER_ID,
            "date_str": "2026-03-01",
            "amount": 100.00,
            "category": "Transport",
            "description": "Taxi",
            "transaction_type": "expense",
        },
    )
    seeded_app.post(
        "/transactions/",
        params={
            "user_id": TEST_USER_ID,
            "date_str": "2026-03-02",
            "amount": 5000.00,
            "category": "Salary",
            "description": "March paycheck",
            "transaction_type": "income",
        },
    )

    # List
    response = seeded_app.get(f"/transactions/?user_id={TEST_USER_ID}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    categories = [t["category"] for t in data]
    assert "Transport" in categories
    assert "Salary" in categories


def test_create_and_get_by_id(seeded_app):
    """Create a transaction then GET by ID."""
    create_resp = seeded_app.post(
        "/transactions/",
        params={
            "user_id": TEST_USER_ID,
            "date_str": "2026-03-05",
            "amount": 25.00,
            "category": "Health",
            "description": "Pharmacy",
            "transaction_type": "expense",
        },
    )
    assert create_resp.status_code == 201
    txn_id = create_resp.json()["id"]

    # Get by ID
    get_resp = seeded_app.get(
        f"/transactions/{txn_id}?user_id={TEST_USER_ID}"
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == txn_id
    assert data["category"] == "Health"


def test_create_and_delete_transaction(seeded_app):
    """Create then DELETE a transaction."""
    create_resp = seeded_app.post(
        "/transactions/",
        params={
            "user_id": TEST_USER_ID,
            "date_str": "2026-03-06",
            "amount": 15.00,
            "category": "Entertainment",
            "description": "Movie ticket",
            "transaction_type": "expense",
        },
    )
    txn_id = create_resp.json()["id"]

    # Delete
    del_resp = seeded_app.delete(
        f"/transactions/{txn_id}?user_id={TEST_USER_ID}"
    )
    assert del_resp.status_code == 204

    # Verify gone
    get_resp = seeded_app.get(
        f"/transactions/{txn_id}?user_id={TEST_USER_ID}"
    )
    assert get_resp.status_code == 404


def test_get_nonexistent_transaction_returns_404(seeded_app):
    """GET a non-existent transaction returns 404."""
    response = seeded_app.get(
        f"/transactions/00000000-0000-0000-0000-000000000001?user_id={TEST_USER_ID}"
    )
    assert response.status_code == 404


def test_list_with_filters(seeded_app):
    """List transactions with date and category filters."""
    # Seed data
    for cat, d in [("Food", "2026-01-15"), ("Transport", "2026-03-15"), ("Food", "2026-06-01")]:
        seeded_app.post(
            "/transactions/",
            params={
                "user_id": TEST_USER_ID,
                "date_str": d,
                "amount": 50.00,
                "category": cat,
                "description": f"{cat} item",
                "transaction_type": "expense",
            },
        )

    # Filter by date range
    resp = seeded_app.get(
        f"/transactions/?user_id={TEST_USER_ID}&start_date=2026-02-01&end_date=2026-04-01"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["category"] == "Transport"
