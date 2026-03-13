"""Tests for ProcessSubscriptionBilling use case."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from flux_core.use_cases.subscriptions.process_billing import ProcessSubscriptionBilling


def _mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.conn = MagicMock()
    uow.add_vector = MagicMock()
    uow.add_event = MagicMock()
    return uow


@patch("flux_core.use_cases.subscriptions.process_billing.SqliteSubscriptionRepository")
@patch("flux_core.use_cases.subscriptions.process_billing.SqliteTransactionRepository")
async def test_process_billing_creates_transaction(MockTxnRepo, MockSubRepo):
    uow = _mock_uow()
    mock_embedding = MagicMock()
    mock_embedding.embed.return_value = [0.1] * 384

    sub_id = uuid4()
    mock_sub = MagicMock()
    mock_sub.id = sub_id
    mock_sub.name = "Netflix"
    mock_sub.amount = Decimal("15.99")
    mock_sub.category = "entertainment"
    mock_sub.active = True
    MockSubRepo.return_value.get.return_value = mock_sub
    mock_txn = MagicMock(id=uuid4())
    MockTxnRepo.return_value.create.return_value = mock_txn

    uc = ProcessSubscriptionBilling(uow, mock_embedding)
    result = await uc.execute("tg:123", str(sub_id), "Asia/Ho_Chi_Minh")

    assert result["subscription_name"] == "Netflix"
    assert result["amount"] == "15.99"
    assert "transaction_id" in result
    MockTxnRepo.return_value.create.assert_called_once()
    MockSubRepo.return_value.advance_next_date.assert_called_once()
    uow.add_vector.assert_called_once()
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.subscriptions.process_billing.SqliteSubscriptionRepository")
@patch("flux_core.use_cases.subscriptions.process_billing.SqliteTransactionRepository")
async def test_process_billing_not_found(MockTxnRepo, MockSubRepo):
    uow = _mock_uow()
    mock_embedding = MagicMock()
    MockSubRepo.return_value.get.return_value = None

    uc = ProcessSubscriptionBilling(uow, mock_embedding)
    result = await uc.execute("tg:123", str(uuid4()), "UTC")

    assert "error" in result
    uow.commit.assert_not_called()


@patch("flux_core.use_cases.subscriptions.process_billing.SqliteSubscriptionRepository")
@patch("flux_core.use_cases.subscriptions.process_billing.SqliteTransactionRepository")
async def test_process_billing_inactive(MockTxnRepo, MockSubRepo):
    uow = _mock_uow()
    mock_embedding = MagicMock()
    MockSubRepo.return_value.get.return_value = MagicMock(active=False)

    uc = ProcessSubscriptionBilling(uow, mock_embedding)
    result = await uc.execute("tg:123", str(uuid4()), "UTC")

    assert "error" in result
    uow.commit.assert_not_called()
