"""Tests for savings use cases."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from flux_core.models.asset import AssetFrequency, AssetOut, AssetType
from flux_core.models.transaction import TransactionOut, TransactionType
from flux_core.use_cases.savings import CreateSavings, ProcessInterest, WithdrawSavings

USER_ID = "tg:12345"
FAKE_ID = uuid4()
FAKE_NOW = datetime(2026, 3, 7, 12, 0, 0)


def _make_asset(**overrides) -> AssetOut:
    defaults = {
        "id": FAKE_ID,
        "user_id": USER_ID,
        "name": "Term Deposit",
        "amount": Decimal("10000.00"),
        "interest_rate": Decimal("5.00"),
        "frequency": AssetFrequency.monthly,
        "next_date": date(2026, 4, 7),
        "category": "savings",
        "active": True,
        "asset_type": AssetType.savings,
        "principal_amount": Decimal("10000.00"),
        "compound_frequency": "monthly",
        "maturity_date": date(2027, 3, 7),
        "start_date": date(2026, 3, 7),
    }
    defaults.update(overrides)
    return AssetOut(**defaults)


def _make_txn_out(**overrides) -> TransactionOut:
    defaults = {
        "id": uuid4(),
        "user_id": USER_ID,
        "date": date(2026, 3, 7),
        "amount": Decimal("10000.00"),
        "category": "savings",
        "description": "Withdrawal from savings: Term Deposit",
        "type": TransactionType.income,
        "is_recurring": False,
        "tags": [],
        "created_at": FAKE_NOW,
    }
    defaults.update(overrides)
    return TransactionOut(**defaults)


def _mock_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.conn = MagicMock()
    uow.add_event = MagicMock()
    return uow


# ── CreateSavings ───────────────────────────────────────────────────────


@patch("flux_core.use_cases.savings.create_savings.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.create_savings.SqliteAssetRepository")
async def test_create_savings(mock_asset_repo_cls, mock_task_repo_cls):
    uow = _mock_uow()
    expected = _make_asset()
    mock_asset_repo_cls.return_value.create.return_value = expected

    uc = CreateSavings(uow)
    result = await uc.execute(
        USER_ID,
        "Term Deposit",
        Decimal("10000.00"),
        Decimal("5.00"),
        "monthly",
        date(2026, 3, 7),
        date(2027, 3, 7),
        "savings",
    )

    assert result.name == "Term Deposit"
    assert result.asset_type == AssetType.savings
    mock_asset_repo_cls.assert_called_once_with(uow.conn)
    mock_task_repo_cls.assert_called_once_with(uow.conn)
    mock_task_repo_cls.return_value.create.assert_called_once()
    call_kwargs = mock_task_repo_cls.return_value.create.call_args.kwargs
    assert call_kwargs["asset_id"] == str(FAKE_ID)
    assert call_kwargs["schedule_type"] == "once"
    uow.add_event.assert_called_once()
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.savings.create_savings.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.create_savings.SqliteAssetRepository")
async def test_create_savings_next_date_capped_to_maturity(
    mock_asset_repo_cls, mock_task_repo_cls
):
    uow = _mock_uow()
    # Maturity is very close — next_date would exceed it
    expected = _make_asset(next_date=date(2026, 3, 20), maturity_date=date(2026, 3, 20))
    mock_asset_repo_cls.return_value.create.return_value = expected

    uc = CreateSavings(uow)
    await uc.execute(
        USER_ID,
        "Term Deposit",
        Decimal("10000.00"),
        Decimal("5.00"),
        "yearly",
        date(2026, 3, 7),
        date(2026, 3, 20),  # Very close maturity
        "savings",
    )

    # Prompt should indicate maturity
    call_kwargs = mock_task_repo_cls.return_value.create.call_args.kwargs
    assert "matures today" in call_kwargs["prompt"]


# ── ProcessInterest ─────────────────────────────────────────────────────


@patch("flux_core.use_cases.savings.process_interest.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.process_interest.SqliteAssetRepository")
async def test_process_interest(mock_asset_repo_cls, mock_task_repo_cls):
    uow = _mock_uow()
    asset = _make_asset()
    advanced = _make_asset(next_date=date(2026, 5, 7))
    mock_asset_repo_cls.return_value.get.return_value = asset
    mock_asset_repo_cls.return_value.update_amount.return_value = None
    mock_asset_repo_cls.return_value.advance_next_date.return_value = advanced

    uc = ProcessInterest(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    # 10000 * (5/100/12) = 41.67
    assert result["interest_applied"] == "41.67"
    assert result["new_balance"] == "10041.67"
    assert result["matured"] is False
    # Should create next scheduled task
    mock_task_repo_cls.return_value.create.assert_called_once()
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.savings.process_interest.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.process_interest.SqliteAssetRepository")
async def test_process_interest_matured(mock_asset_repo_cls, mock_task_repo_cls):
    uow = _mock_uow()
    asset = _make_asset(maturity_date=date(2026, 4, 7))
    # After advance, next_date exceeds maturity
    advanced = _make_asset(next_date=date(2026, 5, 7), maturity_date=date(2026, 4, 7))
    mock_asset_repo_cls.return_value.get.return_value = asset
    mock_asset_repo_cls.return_value.update_amount.return_value = None
    mock_asset_repo_cls.return_value.advance_next_date.return_value = advanced

    uc = ProcessInterest(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result["matured"] is True
    assert "maturity_message" in result
    mock_asset_repo_cls.return_value.deactivate.assert_called_once()
    # Should NOT schedule another task
    mock_task_repo_cls.return_value.create.assert_not_called()
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.savings.process_interest.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.process_interest.SqliteAssetRepository")
async def test_process_interest_not_found(mock_asset_repo_cls, mock_task_repo_cls):
    uow = _mock_uow()
    mock_asset_repo_cls.return_value.get.return_value = None

    uc = ProcessInterest(uow)
    try:
        await uc.execute(FAKE_ID, USER_ID)
        assert False, "Expected ValueError"
    except ValueError:
        pass


@patch("flux_core.use_cases.savings.process_interest.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.process_interest.SqliteAssetRepository")
async def test_process_interest_inactive(mock_asset_repo_cls, mock_task_repo_cls):
    uow = _mock_uow()
    mock_asset_repo_cls.return_value.get.return_value = _make_asset(active=False)

    uc = ProcessInterest(uow)
    try:
        await uc.execute(FAKE_ID, USER_ID)
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ── WithdrawSavings ─────────────────────────────────────────────────────


@patch("flux_core.use_cases.savings.withdraw_savings.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.withdraw_savings.SqliteTransactionRepository")
@patch("flux_core.use_cases.savings.withdraw_savings.SqliteAssetRepository")
async def test_withdraw_savings(
    mock_asset_repo_cls, mock_txn_repo_cls, mock_task_repo_cls
):
    uow = _mock_uow()
    asset = _make_asset()
    txn_out = _make_txn_out()
    mock_asset_repo_cls.return_value.get.return_value = asset
    mock_txn_repo_cls.return_value.create.return_value = txn_out

    uc = WithdrawSavings(uow)
    result = await uc.execute(FAKE_ID, USER_ID, today=date(2026, 3, 7))

    assert result["withdrawn_amount"] == "10000.00"
    assert result["asset_name"] == "Term Deposit"
    mock_asset_repo_cls.return_value.deactivate.assert_called_once()
    mock_task_repo_cls.return_value.delete_by_asset.assert_called_once_with(
        str(FAKE_ID)
    )
    uow.commit.assert_called_once()


@patch("flux_core.use_cases.savings.withdraw_savings.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.withdraw_savings.SqliteTransactionRepository")
@patch("flux_core.use_cases.savings.withdraw_savings.SqliteAssetRepository")
async def test_withdraw_savings_not_found(
    mock_asset_repo_cls, mock_txn_repo_cls, mock_task_repo_cls
):
    uow = _mock_uow()
    mock_asset_repo_cls.return_value.get.return_value = None

    uc = WithdrawSavings(uow)
    try:
        await uc.execute(FAKE_ID, USER_ID)
        assert False, "Expected ValueError"
    except ValueError:
        pass


@patch("flux_core.use_cases.savings.withdraw_savings.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.withdraw_savings.SqliteTransactionRepository")
@patch("flux_core.use_cases.savings.withdraw_savings.SqliteAssetRepository")
async def test_withdraw_savings_inactive(
    mock_asset_repo_cls, mock_txn_repo_cls, mock_task_repo_cls
):
    uow = _mock_uow()
    mock_asset_repo_cls.return_value.get.return_value = _make_asset(active=False)

    uc = WithdrawSavings(uow)
    try:
        await uc.execute(FAKE_ID, USER_ID)
        assert False, "Expected ValueError"
    except ValueError:
        pass
