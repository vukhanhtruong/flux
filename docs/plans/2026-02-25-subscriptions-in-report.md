# Subscriptions in Spending Report — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `subscriptions` block to `generate_spending_report` showing active recurring commitments (count, monthly total, annual total, item list).

**Architecture:** `generate_spending_report` receives a new `sub_repo: SubscriptionRepository` parameter, calls `list_by_user(active_only=True)`, computes normalized monthly/annual totals, and appends a `subscriptions` key to the existing return dict. All callers (MCP layer and REST layer) are updated to pass the new repo.

**Tech Stack:** Python 3.12, asyncpg, Pydantic v2, pytest (asyncio_mode = "auto"), FastAPI, FastMCP

---

### Task 1: Update core tool — `generate_spending_report`

**Files:**
- Modify: `packages/core/src/flux_core/tools/analytics_tools.py:1-34`
- Test: `packages/core/tests/test_tools/test_analytics_tools.py`

**Step 1: Write the failing tests**

Open `packages/core/tests/test_tools/test_analytics_tools.py`.

Replace the existing `test_generate_spending_report` and add a second test:

```python
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock
import pytest

from flux_core.tools.analytics_tools import (
    generate_spending_report,
    forecast_budget,
    calculate_financial_health,
)


async def test_generate_spending_report():
    mock_txn_repo = AsyncMock()
    mock_txn_repo.get_summary.return_value = {
        "total_income": Decimal("5000.00"),
        "total_expenses": Decimal("3000.00"),
        "count": 25,
    }
    mock_txn_repo.get_category_breakdown.return_value = [
        {"category": "Food", "total": Decimal("800.00"), "count": 10},
        {"category": "Transport", "total": Decimal("400.00"), "count": 5},
    ]
    mock_sub_repo = AsyncMock()
    mock_sub_repo.list_by_user.return_value = []

    result = await generate_spending_report(
        user_id="test_user",
        start_date="2026-01-01",
        end_date="2026-01-31",
        txn_repo=mock_txn_repo,
        sub_repo=mock_sub_repo,
    )

    assert result["total_income"] == "5000.00"
    assert result["total_expenses"] == "3000.00"
    assert result["net"] == "2000.00"
    assert result["count"] == 25
    assert len(result["category_breakdown"]) == 2
    assert result["category_breakdown"][0]["category"] == "Food"
    assert "subscriptions" in result
    mock_txn_repo.get_summary.assert_called_once()
    mock_txn_repo.get_category_breakdown.assert_called_once()
    mock_sub_repo.list_by_user.assert_called_once_with("test_user", active_only=True)


async def test_generate_spending_report_with_subscriptions():
    mock_txn_repo = AsyncMock()
    mock_txn_repo.get_summary.return_value = {
        "total_income": Decimal("5000.00"),
        "total_expenses": Decimal("3000.00"),
        "count": 10,
    }
    mock_txn_repo.get_category_breakdown.return_value = []

    # monthly sub: 15.99/mo, yearly sub: 120.00/yr = 10.00/mo
    monthly_sub = type("Sub", (), {
        "name": "Netflix",
        "amount": Decimal("15.99"),
        "billing_cycle": "monthly",
        "category": "Entertainment",
        "next_date": date(2026, 2, 1),
    })()
    yearly_sub = type("Sub", (), {
        "name": "iCloud",
        "amount": Decimal("120.00"),
        "billing_cycle": "yearly",
        "category": "Storage",
        "next_date": date(2026, 6, 1),
    })()

    mock_sub_repo = AsyncMock()
    mock_sub_repo.list_by_user.return_value = [monthly_sub, yearly_sub]

    result = await generate_spending_report(
        user_id="test_user",
        start_date="2026-01-01",
        end_date="2026-01-31",
        txn_repo=mock_txn_repo,
        sub_repo=mock_sub_repo,
    )

    subs = result["subscriptions"]
    assert subs["active_count"] == 2
    # 15.99 + 120.00/12 = 15.99 + 10.00 = 25.99
    assert subs["monthly_total"] == "25.99"
    # 25.99 * 12 = 311.88
    assert subs["annual_total"] == "311.88"
    assert len(subs["items"]) == 2
    assert subs["items"][0]["name"] == "Netflix"
    assert subs["items"][0]["billing_cycle"] == "monthly"
    assert subs["items"][1]["name"] == "iCloud"
    assert subs["items"][1]["billing_cycle"] == "yearly"
```

**Step 2: Run tests to verify they fail**

```bash
cd packages/core
pytest tests/test_tools/test_analytics_tools.py::test_generate_spending_report \
       tests/test_tools/test_analytics_tools.py::test_generate_spending_report_with_subscriptions -v
```

Expected: FAIL — `generate_spending_report() got an unexpected keyword argument 'sub_repo'`

**Step 3: Update `generate_spending_report` in `analytics_tools.py`**

Replace lines 1–34 of `packages/core/src/flux_core/tools/analytics_tools.py`:

```python
from datetime import date
from decimal import Decimal

from flux_core.db.transaction_repo import TransactionRepository
from flux_core.db.budget_repo import BudgetRepository
from flux_core.db.goal_repo import GoalRepository
from flux_core.db.subscription_repo import SubscriptionRepository


async def generate_spending_report(
    user_id: str,
    start_date: str,
    end_date: str,
    txn_repo: TransactionRepository,
    sub_repo: SubscriptionRepository,
) -> dict:
    """Generate a spending report for a date range."""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    summary = await txn_repo.get_summary(user_id, start, end)
    breakdown = await txn_repo.get_category_breakdown(user_id, start, end)
    subs = await sub_repo.list_by_user(user_id, active_only=True)

    total_income = summary["total_income"] or Decimal("0")
    total_expenses = summary["total_expenses"] or Decimal("0")
    net = total_income - total_expenses

    monthly_total = sum(
        (s.amount if s.billing_cycle == "monthly" else s.amount / 12)
        for s in subs
    )
    annual_total = monthly_total * 12

    return {
        "total_income": str(total_income),
        "total_expenses": str(total_expenses),
        "net": str(net),
        "count": summary["count"],
        "category_breakdown": [
            {"category": row["category"], "total": str(row["total"]), "count": row["count"]}
            for row in breakdown
        ],
        "start_date": start_date,
        "end_date": end_date,
        "subscriptions": {
            "active_count": len(subs),
            "monthly_total": str(round(monthly_total, 2)),
            "annual_total": str(round(annual_total, 2)),
            "items": [
                {
                    "name": s.name,
                    "amount": str(s.amount),
                    "billing_cycle": s.billing_cycle,
                    "category": s.category,
                    "next_date": str(s.next_date),
                }
                for s in subs
            ],
        },
    }
```

**Step 4: Run tests to verify they pass**

```bash
cd packages/core
pytest tests/test_tools/test_analytics_tools.py -v
```

Expected: All tests PASS (including unchanged `test_forecast_budget` and `test_calculate_financial_health`).

**Step 5: Commit**

```bash
git add packages/core/src/flux_core/tools/analytics_tools.py \
        packages/core/tests/test_tools/test_analytics_tools.py
git commit -m "feat: include active subscriptions in spending report"
```

---

### Task 2: Update MCP server analytics tool

**Files:**
- Modify: `packages/mcp-server/src/flux_mcp/tools/analytics_tools.py:1-32`

**Step 1: Write the failing test**

Run the existing MCP e2e test to confirm it now fails (the call signature changed):

```bash
cd packages/mcp-server
pytest tests/ -v -k "spending"
```

Expected: FAIL — `generate_spending_report() missing 1 required positional argument: 'sub_repo'`

**Step 2: Update the MCP tool**

Replace the full content of `packages/mcp-server/src/flux_mcp/tools/analytics_tools.py`:

```python
from typing import Callable, Awaitable

from fastmcp import FastMCP
from flux_core.db.connection import Database
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.db.budget_repo import BudgetRepository
from flux_core.db.goal_repo import GoalRepository
from flux_core.db.subscription_repo import SubscriptionRepository
from flux_core.tools import analytics_tools as biz


def register_analytics_tools(
    mcp: FastMCP,
    get_db: Callable[[], Awaitable[Database]],
    get_user_id: Callable[[], str],
):
    @mcp.tool()
    async def generate_spending_report(start_date: str, end_date: str) -> dict:
        """Generate a spending report for a date range."""
        db = await get_db()
        return await biz.generate_spending_report(
            get_user_id(), start_date, end_date,
            TransactionRepository(db),
            SubscriptionRepository(db),
        )

    @mcp.tool()
    async def calculate_financial_health(start_date: str, end_date: str) -> dict:
        """Calculate a financial health score based on multiple factors."""
        db = await get_db()
        return await biz.calculate_financial_health(
            get_user_id(), start_date, end_date,
            TransactionRepository(db), BudgetRepository(db), GoalRepository(db),
        )
```

**Step 3: Run MCP tests**

```bash
cd packages/mcp-server
pytest tests/ -v
```

Expected: All tests PASS.

**Step 4: Commit**

```bash
git add packages/mcp-server/src/flux_mcp/tools/analytics_tools.py
git commit -m "fix: pass sub_repo to generate_spending_report in MCP layer"
```

---

### Task 3: Update API server analytics route

**Files:**
- Modify: `packages/api-server/src/flux_api/routes/analytics.py:1-27`
- Test: `packages/api-server/tests/test_routes_analytics.py`

**Step 1: Write the failing test**

Run the existing API tests to confirm the route now fails:

```bash
cd packages/api-server
pytest tests/test_routes_analytics.py::test_spending_report -v
```

Expected: FAIL — `generate_spending_report() missing 1 required positional argument: 'sub_repo'`

**Step 2: Update the route**

Replace the full content of `packages/api-server/src/flux_api/routes/analytics.py`:

```python
"""Analytics REST routes."""
from typing import Annotated

from fastapi import APIRouter, Depends

from flux_api.deps import get_db
from flux_core.db.connection import Database
from flux_core.db.transaction_repo import TransactionRepository
from flux_core.db.budget_repo import BudgetRepository
from flux_core.db.goal_repo import GoalRepository
from flux_core.db.subscription_repo import SubscriptionRepository
from flux_core.tools import analytics_tools

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/spending-report")
async def generate_spending_report(
    user_id: str,
    start_date: str,
    end_date: str,
    db: Annotated[Database, Depends(get_db)],
) -> dict:
    """Generate a spending report for a date range."""
    return await analytics_tools.generate_spending_report(
        user_id, start_date, end_date,
        TransactionRepository(db),
        SubscriptionRepository(db),
    )


@router.get("/financial-health")
async def calculate_financial_health(
    user_id: str,
    start_date: str,
    end_date: str,
    db: Annotated[Database, Depends(get_db)],
) -> dict:
    """Calculate a financial health score based on multiple factors."""
    return await analytics_tools.calculate_financial_health(
        user_id, start_date, end_date,
        TransactionRepository(db), BudgetRepository(db), GoalRepository(db),
    )
```

**Step 3: Update the API route test**

In `packages/api-server/tests/test_routes_analytics.py`, replace `test_spending_report`:

```python
def test_spending_report(client):
    """Test GET /analytics/spending-report returns report dict with subscriptions block."""
    expected = {
        "total_income": "5000.00",
        "total_expenses": "3000.00",
        "net": "2000.00",
        "count": 25,
        "category_breakdown": [],
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "subscriptions": {
            "active_count": 0,
            "monthly_total": "0",
            "annual_total": "0",
            "items": [],
        },
    }

    with patch(
        "flux_api.routes.analytics.analytics_tools.generate_spending_report",
        new=AsyncMock(return_value=expected),
    ):
        response = client.get(
            "/analytics/spending-report?user_id=user-1&start_date=2024-01-01&end_date=2024-01-31"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_income"] == "5000.00"
    assert "subscriptions" in data
    assert data["subscriptions"]["active_count"] == 0
```

**Step 4: Run all API tests**

```bash
cd packages/api-server
pytest tests/ -v
```

Expected: All tests PASS.

**Step 5: Commit**

```bash
git add packages/api-server/src/flux_api/routes/analytics.py \
        packages/api-server/tests/test_routes_analytics.py
git commit -m "fix: pass sub_repo to generate_spending_report in API layer"
```

---

### Task 4: Final verification — run all tests across all packages

**Step 1: Run core tests**

```bash
cd packages/core && pytest tests/ -v
```

Expected: All PASS.

**Step 2: Run MCP server tests**

```bash
cd packages/mcp-server && pytest tests/ -v
```

Expected: All PASS.

**Step 3: Run API server tests**

```bash
cd packages/api-server && pytest tests/ -v
```

Expected: All PASS.
