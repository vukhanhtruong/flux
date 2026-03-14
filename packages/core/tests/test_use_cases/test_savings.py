"""Tests for savings use cases."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
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


def _setup_at_maturity_mocks(mock_asset_repo_cls, maturity, start):
    """Configure mocks for at_maturity ProcessInterest tests."""
    asset = _make_asset(
        amount=Decimal("200000000.00"),
        principal_amount=Decimal("200000000.00"),
        compound_frequency="at_maturity",
        frequency=AssetFrequency.at_maturity,
        next_date=maturity,
        maturity_date=maturity,
        start_date=start,
    )
    past_maturity = maturity.replace(year=maturity.year + 1)
    advanced = _make_asset(next_date=past_maturity, maturity_date=maturity)
    mock_asset_repo_cls.return_value.get.return_value = asset
    mock_asset_repo_cls.return_value.update_amount.return_value = None
    mock_asset_repo_cls.return_value.advance_next_date.return_value = advanced


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
async def test_create_savings_at_maturity_sets_next_date(
    mock_asset_repo_cls, mock_task_repo_cls
):
    """at_maturity: next_date = maturity_date, not start + 1 month."""
    uow = _mock_uow()
    mat = date(2026, 9, 14)
    expected = _make_asset(
        compound_frequency="at_maturity",
        frequency=AssetFrequency.at_maturity,
        next_date=mat,
        maturity_date=mat,
        start_date=date(2026, 3, 14),
    )
    mock_asset_repo_cls.return_value.create.return_value = expected

    uc = CreateSavings(uow)
    await uc.execute(
        USER_ID,
        "Term Deposit",
        Decimal("200000000.00"),
        Decimal("5.00"),
        "at_maturity",
        date(2026, 3, 14),
        mat,
        "savings",
    )

    call_kwargs = mock_task_repo_cls.return_value.create.call_args.kwargs
    assert call_kwargs["schedule_value"] == "2026-09-14"
    from datetime import UTC
    assert call_kwargs["next_run_at"] == datetime(2026, 9, 14, tzinfo=UTC)
    assert "matures today" in call_kwargs["prompt"]


@pytest.mark.parametrize(
    "months,expected_maturity",
    [
        (1, date(2026, 4, 14)),
        (2, date(2026, 5, 14)),
        (3, date(2026, 6, 14)),
        (4, date(2026, 7, 14)),
        (5, date(2026, 8, 14)),
        (6, date(2026, 9, 14)),
        (7, date(2026, 10, 14)),
        (8, date(2026, 11, 14)),
        (9, date(2026, 12, 14)),
        (10, date(2027, 1, 14)),
        (11, date(2027, 2, 14)),
        (12, date(2027, 3, 14)),
    ],
)
@patch("flux_core.use_cases.savings.create_savings.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.create_savings.SqliteAssetRepository")
async def test_create_savings_at_maturity_months(
    mock_asset_repo_cls, mock_task_repo_cls, months, expected_maturity
):
    """at_maturity: next_date always equals maturity_date for 1-12 month terms."""
    uow = _mock_uow()
    expected = _make_asset(
        compound_frequency="at_maturity",
        frequency=AssetFrequency.at_maturity,
        next_date=expected_maturity,
        maturity_date=expected_maturity,
        start_date=date(2026, 3, 14),
    )
    mock_asset_repo_cls.return_value.create.return_value = expected

    uc = CreateSavings(uow)
    await uc.execute(
        USER_ID,
        "Term Deposit",
        Decimal("200000000.00"),
        Decimal("5.00"),
        "at_maturity",
        date(2026, 3, 14),
        expected_maturity,
        "savings",
    )

    call_kwargs = mock_task_repo_cls.return_value.create.call_args.kwargs
    assert call_kwargs["schedule_value"] == expected_maturity.isoformat()


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


@patch("flux_core.use_cases.savings.process_interest.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.process_interest.SqliteAssetRepository")
async def test_process_interest_quarterly_compound(mock_asset_repo_cls, mock_task_repo_cls):
    """Quarterly compounding uses 4 periods — interest = amount * rate/100/4."""
    uow = _mock_uow()
    asset = _make_asset(
        compound_frequency="quarterly",
        frequency=AssetFrequency.quarterly,
        next_date=date(2026, 6, 7),
        maturity_date=date(2028, 3, 7),
    )
    advanced = _make_asset(next_date=date(2026, 9, 7))
    mock_asset_repo_cls.return_value.get.return_value = asset
    mock_asset_repo_cls.return_value.update_amount.return_value = None
    mock_asset_repo_cls.return_value.advance_next_date.return_value = advanced

    uc = ProcessInterest(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    # 10000 * (5/100/4) = 125.00
    assert result["interest_applied"] == "125.00"
    assert result["new_balance"] == "10125.00"
    assert result["matured"] is False
    mock_task_repo_cls.return_value.create.assert_called_once()


@patch("flux_core.use_cases.savings.process_interest.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.process_interest.SqliteAssetRepository")
async def test_process_interest_yearly_compound(mock_asset_repo_cls, mock_task_repo_cls):
    """Yearly compounding uses 1 period — interest = amount * rate/100."""
    uow = _mock_uow()
    asset = _make_asset(
        compound_frequency="yearly",
        frequency=AssetFrequency.yearly,
        next_date=date(2027, 3, 7),
        maturity_date=date(2028, 3, 7),
    )
    advanced = _make_asset(next_date=date(2028, 3, 7))
    mock_asset_repo_cls.return_value.get.return_value = asset
    mock_asset_repo_cls.return_value.update_amount.return_value = None
    mock_asset_repo_cls.return_value.advance_next_date.return_value = advanced

    uc = ProcessInterest(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    # 10000 * (5/100/1) = 500.00
    assert result["interest_applied"] == "500.00"
    assert result["new_balance"] == "10500.00"
    assert result["matured"] is False


@pytest.mark.parametrize(
    "months,expected_interest,expected_balance",
    [
        (1, "833333.33", "200833333.33"),
        (2, "1666666.67", "201666666.67"),
        (3, "2500000.00", "202500000.00"),
        (4, "3333333.33", "203333333.33"),
        (5, "4166666.67", "204166666.67"),
        (6, "5000000.00", "205000000.00"),
        (7, "5833333.33", "205833333.33"),
        (8, "6666666.67", "206666666.67"),
        (9, "7500000.00", "207500000.00"),
        (10, "8333333.33", "208333333.33"),
        (11, "9166666.67", "209166666.67"),
        (12, "10000000.00", "210000000.00"),
    ],
)
@patch("flux_core.use_cases.savings.process_interest.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.process_interest.SqliteAssetRepository")
async def test_process_interest_at_maturity_months(
    mock_asset_repo_cls, mock_task_repo_cls, months, expected_interest, expected_balance
):
    """at_maturity: interest = amount * rate/100 / 12 * months, then matured."""
    uow = _mock_uow()
    start = date(2026, 3, 14)
    mat_month = 3 + months
    mat_year = 2026 + (mat_month - 1) // 12
    mat_month = (mat_month - 1) % 12 + 1
    maturity = date(mat_year, mat_month, 14)
    _setup_at_maturity_mocks(mock_asset_repo_cls, maturity, start)

    uc = ProcessInterest(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result["interest_applied"] == expected_interest
    assert result["new_balance"] == expected_balance
    assert result["matured"] is True
    mock_asset_repo_cls.return_value.deactivate.assert_called_once()
    mock_task_repo_cls.return_value.create.assert_not_called()


@pytest.mark.parametrize(
    "years,expected_interest,expected_balance",
    [
        (1, "10000000.00", "210000000.00"),
        (2, "20000000.00", "220000000.00"),
        (3, "30000000.00", "230000000.00"),
        (4, "40000000.00", "240000000.00"),
        (5, "50000000.00", "250000000.00"),
        (6, "60000000.00", "260000000.00"),
        (7, "70000000.00", "270000000.00"),
        (8, "80000000.00", "280000000.00"),
        (9, "90000000.00", "290000000.00"),
        (10, "100000000.00", "300000000.00"),
    ],
)
@patch("flux_core.use_cases.savings.process_interest.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.process_interest.SqliteAssetRepository")
async def test_process_interest_at_maturity_years(
    mock_asset_repo_cls, mock_task_repo_cls, years, expected_interest, expected_balance
):
    """at_maturity: interest = amount * rate/100 * years, then matured."""
    uow = _mock_uow()
    start = date(2026, 3, 14)
    maturity = date(2026 + years, 3, 14)
    _setup_at_maturity_mocks(mock_asset_repo_cls, maturity, start)

    uc = ProcessInterest(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result["interest_applied"] == expected_interest
    assert result["new_balance"] == expected_balance
    assert result["matured"] is True
    mock_asset_repo_cls.return_value.deactivate.assert_called_once()
    mock_task_repo_cls.return_value.create.assert_not_called()


@patch("flux_core.use_cases.savings.process_interest.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.process_interest.SqliteAssetRepository")
async def test_process_interest_exact_maturity_creates_maturity_task(
    mock_asset_repo_cls, mock_task_repo_cls
):
    """When next_date == maturity_date, task should be created with maturity prompt."""
    uow = _mock_uow()
    mat = date(2027, 3, 7)
    asset = _make_asset(maturity_date=mat, next_date=date(2027, 2, 7))
    # After advance, next_date equals maturity_date exactly
    advanced = _make_asset(next_date=mat, maturity_date=mat, active=True)
    mock_asset_repo_cls.return_value.get.return_value = asset
    mock_asset_repo_cls.return_value.update_amount.return_value = None
    mock_asset_repo_cls.return_value.advance_next_date.return_value = advanced

    uc = ProcessInterest(uow)
    result = await uc.execute(FAKE_ID, USER_ID)

    assert result["matured"] is False
    # Should still create a task (next_date == maturity, not >)
    mock_task_repo_cls.return_value.create.assert_called_once()
    call_kwargs = mock_task_repo_cls.return_value.create.call_args.kwargs
    assert "matures today" in call_kwargs["prompt"]
    mock_asset_repo_cls.return_value.deactivate.assert_not_called()


@patch("flux_core.use_cases.savings.process_interest.SqliteBotScheduledTaskRepository")
@patch("flux_core.use_cases.savings.process_interest.SqliteAssetRepository")
async def test_process_interest_chained_task_params(mock_asset_repo_cls, mock_task_repo_cls):
    """Chained task must have correct schedule_value, next_run_at, and asset_id."""
    uow = _mock_uow()
    asset = _make_asset()
    next_d = date(2026, 5, 7)
    advanced = _make_asset(next_date=next_d)
    mock_asset_repo_cls.return_value.get.return_value = asset
    mock_asset_repo_cls.return_value.update_amount.return_value = None
    mock_asset_repo_cls.return_value.advance_next_date.return_value = advanced

    uc = ProcessInterest(uow)
    await uc.execute(FAKE_ID, USER_ID)

    call_kwargs = mock_task_repo_cls.return_value.create.call_args.kwargs
    assert call_kwargs["schedule_type"] == "once"
    assert call_kwargs["schedule_value"] == "2026-05-07"
    assert call_kwargs["asset_id"] == str(FAKE_ID)
    assert call_kwargs["user_id"] == USER_ID
    # next_run_at should be UTC midnight of 2026-05-07
    from datetime import UTC
    expected_run = datetime(2026, 5, 7, tzinfo=UTC)
    assert call_kwargs["next_run_at"] == expected_run


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
