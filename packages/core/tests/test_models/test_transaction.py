import pytest
from datetime import date
from decimal import Decimal
from pydantic import ValidationError
from flux_core.models.transaction import TransactionCreate


def test_valid_transaction():
    txn = TransactionCreate(
        user_id="tg:12345",
        date=date(2026, 2, 13),
        amount=Decimal("15.50"),
        category="Food",
        description="Lunch at Chipotle",
        type="expense",
        tags=["work"],
    )
    assert txn.amount == Decimal("15.50")
    assert txn.type == "expense"


def test_amount_must_be_positive():
    with pytest.raises(ValidationError, match="amount"):
        TransactionCreate(
            user_id="tg:12345",
            date=date.today(),
            amount=Decimal("-5"),
            category="Food",
            description="Test",
            type="expense",
        )


def test_amount_zero_rejected():
    with pytest.raises(ValidationError, match="amount"):
        TransactionCreate(
            user_id="tg:12345",
            date=date.today(),
            amount=Decimal("0"),
            category="Food",
            description="Test",
            type="expense",
        )


def test_type_must_be_income_or_expense():
    with pytest.raises(ValidationError, match="type"):
        TransactionCreate(
            user_id="tg:12345",
            date=date.today(),
            amount=Decimal("10"),
            category="Food",
            description="Test",
            type="transfer",
        )


def test_tags_default_empty():
    txn = TransactionCreate(
        user_id="tg:12345",
        date=date.today(),
        amount=Decimal("10"),
        category="Food",
        description="Test",
        type="expense",
    )
    assert txn.tags == []
