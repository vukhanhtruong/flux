"""Tests for SqliteBotMessageRepository."""
import pytest
from flux_core.sqlite.bot.message_repo import SqliteBotMessageRepository


@pytest.fixture
def repo(conn):
    return SqliteBotMessageRepository(conn)


class TestInsert:
    def test_inserts_and_returns_id(self, repo):
        msg_id = repo.insert("tg:123", "telegram", "123", text="Hello")
        assert isinstance(msg_id, int)
        assert msg_id > 0

    def test_inserts_with_image(self, repo):
        msg_id = repo.insert("tg:123", "telegram", "123", image_path="/tmp/img.jpg")
        assert msg_id > 0


class TestFetchPending:
    def test_fetches_pending(self, repo):
        repo.insert("tg:123", "telegram", "123", text="Hello")
        repo.insert("tg:456", "telegram", "456", text="World")
        pending = repo.fetch_pending()
        assert len(pending) == 2
        assert pending[0]["text"] == "Hello"
        assert pending[0]["user_id"] == "tg:123"

    def test_empty(self, repo):
        assert repo.fetch_pending() == []


class TestMarkProcessing:
    def test_marks_processing(self, repo):
        msg_id = repo.insert("tg:123", "telegram", "123", text="Hello")
        repo.mark_processing(msg_id)
        pending = repo.fetch_pending()
        assert len(pending) == 0


class TestMarkProcessed:
    def test_marks_processed(self, repo, conn):
        msg_id = repo.insert("tg:123", "telegram", "123", text="Hello")
        repo.mark_processed(msg_id)
        row = conn.execute(
            "SELECT status, processed_at FROM bot_messages WHERE id = ?", (msg_id,)
        ).fetchone()
        assert row["status"] == "processed"
        assert row["processed_at"] is not None


class TestMarkFailed:
    def test_marks_failed(self, repo, conn):
        msg_id = repo.insert("tg:123", "telegram", "123", text="Hello")
        repo.mark_failed(msg_id, "timeout")
        row = conn.execute(
            "SELECT status, error, processed_at FROM bot_messages WHERE id = ?", (msg_id,)
        ).fetchone()
        assert row["status"] == "failed"
        assert row["error"] == "timeout"
        assert row["processed_at"] is not None
