"""Test scheduled task REST routes."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from flux_api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_scheduled_tasks(client):
    """Test GET /scheduled-tasks/ returns list of tasks for a user."""
    expected = {
        "tasks": [
            {
                "id": 1,
                "user_id": "user-1",
                "prompt": "Pay rent",
                "schedule_type": "cron",
                "schedule_value": "0 0 1 * *",
                "status": "active",
                "next_run_at": "2026-04-01T00:00:00",
                "last_run_at": "2026-03-01T00:00:00",
                "subscription_id": "sub-123",
                "asset_id": None,
                "created_at": "2026-01-15T10:00:00",
            },
        ]
    }

    with (
        patch("flux_api.routes.scheduled_tasks.get_db") as mock_get_db,
        patch("flux_api.routes.scheduled_tasks.SqliteBotScheduledTaskRepository"),
        patch("flux_api.routes.scheduled_tasks.ListTasks") as MockUC,
    ):
        mock_get_db.return_value = MagicMock()
        MockUC.return_value.execute = AsyncMock(return_value=expected)
        response = client.get("/scheduled-tasks/?user_id=user-1")

    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["prompt"] == "Pay rent"


def test_list_scheduled_tasks_missing_user_id(client):
    """Test GET /scheduled-tasks/ without user_id returns 422."""
    response = client.get("/scheduled-tasks/")
    assert response.status_code == 422


def test_delete_scheduled_task(client):
    """Test DELETE /scheduled-tasks/{task_id} returns 204 on success."""
    with (
        patch("flux_api.routes.scheduled_tasks.get_uow") as mock_get_uow,
        patch("flux_api.routes.scheduled_tasks.CancelTask") as MockUC,
    ):
        mock_get_uow.return_value = MagicMock()
        MockUC.return_value.execute = AsyncMock(
            return_value={"status": "cancelled", "task_id": 1}
        )
        response = client.delete("/scheduled-tasks/1?user_id=user-1")

    assert response.status_code == 204
    MockUC.return_value.execute.assert_called_once_with("user-1", 1)


def test_delete_scheduled_task_not_found(client):
    """Test DELETE /scheduled-tasks/{task_id} returns 404 when task not found."""
    with (
        patch("flux_api.routes.scheduled_tasks.get_uow") as mock_get_uow,
        patch("flux_api.routes.scheduled_tasks.CancelTask") as MockUC,
    ):
        mock_get_uow.return_value = MagicMock()
        MockUC.return_value.execute = AsyncMock(
            return_value={"status": "error", "message": "Task 999 not found."}
        )
        response = client.delete("/scheduled-tasks/999?user_id=user-1")

    assert response.status_code == 404


def test_delete_scheduled_task_missing_user_id(client):
    """Test DELETE /scheduled-tasks/{task_id} without user_id returns 422."""
    response = client.delete("/scheduled-tasks/1")
    assert response.status_code == 422
