"""E2E tests for goal API routes with seeded SQLite+zvec."""
TEST_USER_ID = "test:e2e-user"


def test_create_and_list_goals(seeded_app):
    """POST create goal then GET list."""
    resp = seeded_app.post(
        "/goals/",
        params={
            "user_id": TEST_USER_ID,
            "name": "Emergency Fund",
            "target_amount": 10000.00,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Emergency Fund"
    assert float(data["target_amount"]) == 10000.00
    assert float(data["current_amount"]) == 0.00
    goal_id = data["id"]

    # List
    list_resp = seeded_app.get(f"/goals/?user_id={TEST_USER_ID}")
    assert list_resp.status_code == 200
    goals = list_resp.json()
    assert any(g["id"] == goal_id for g in goals)


def test_deposit_to_goal(seeded_app):
    """Create goal then deposit money into it."""
    create_resp = seeded_app.post(
        "/goals/",
        params={
            "user_id": TEST_USER_ID,
            "name": "Vacation",
            "target_amount": 5000.00,
        },
    )
    goal_id = create_resp.json()["id"]

    # Deposit
    dep_resp = seeded_app.post(
        f"/goals/{goal_id}/deposit",
        params={
            "user_id": TEST_USER_ID,
            "amount": 1000.00,
        },
    )
    assert dep_resp.status_code == 200
    data = dep_resp.json()
    assert float(data["current_amount"]) == 1000.00


def test_create_and_delete_goal(seeded_app):
    """Create then delete a goal."""
    create_resp = seeded_app.post(
        "/goals/",
        params={
            "user_id": TEST_USER_ID,
            "name": "Car Fund",
            "target_amount": 20000.00,
        },
    )
    goal_id = create_resp.json()["id"]

    # Delete
    del_resp = seeded_app.delete(
        f"/goals/{goal_id}?user_id={TEST_USER_ID}"
    )
    assert del_resp.status_code == 204

    # Verify gone
    list_resp = seeded_app.get(f"/goals/?user_id={TEST_USER_ID}")
    ids = [g["id"] for g in list_resp.json()]
    assert goal_id not in ids
