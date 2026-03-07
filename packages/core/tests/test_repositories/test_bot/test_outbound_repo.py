"""Tests for SqliteBotOutboundRepository."""
import pytest
from flux_core.sqlite.bot.outbound_repo import SqliteBotOutboundRepository


@pytest.fixture
def repo(conn):
    return SqliteBotOutboundRepository(conn)


class TestInsert:
    def test_inserts_and_returns_id(self, repo):
        msg_id = repo.insert("tg:123", "Hello user!")
        assert isinstance(msg_id, int)
        assert msg_id > 0

    def test_inserts_with_sender(self, repo):
        msg_id = repo.insert("tg:123", "Hello user!", sender="scheduler")
        assert msg_id > 0


class TestFetchPending:
    def test_fetches_pending(self, repo):
        repo.insert("tg:123", "Message 1")
        repo.insert("tg:456", "Message 2")
        pending = repo.fetch_pending()
        assert len(pending) == 2
        assert pending[0]["text"] == "Message 1"
        assert pending[0]["user_id"] == "tg:123"

    def test_empty(self, repo):
        assert repo.fetch_pending() == []


class TestMarkSent:
    def test_marks_sent(self, repo, conn):
        msg_id = repo.insert("tg:123", "Hello")
        repo.mark_sent(msg_id)
        row = conn.execute(
            "SELECT status, completed_at FROM bot_outbound_messages WHERE id = ?",
            (msg_id,),
        ).fetchone()
        assert row["status"] == "sent"
        assert row["completed_at"] is not None
        # Should no longer appear in pending
        assert repo.fetch_pending() == []


class TestMarkFailed:
    def test_marks_failed(self, repo, conn):
        msg_id = repo.insert("tg:123", "Hello")
        repo.mark_failed(msg_id, "network error")
        row = conn.execute(
            "SELECT status, error, completed_at FROM bot_outbound_messages WHERE id = ?",
            (msg_id,),
        ).fetchone()
        assert row["status"] == "failed"
        assert row["error"] == "network error"
        assert row["completed_at"] is not None
