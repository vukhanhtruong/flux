# Savings with Interest — Design Document

**Date:** 2026-03-01
**Status:** Approved

## Overview

Add savings deposit tracking with compound interest to the assets system. Users can create term deposits (e.g., "100M in bank for 3 years at 5%/year") and the scheduler automatically applies interest at each compounding period until maturity.

## Example

> "saving 100M in bank for 3 years with interest rate 5%/year, start on Mar 1st, 2026"

| Date | Event | Calculation | Balance |
|------|-------|-------------|---------|
| Mar 1, 2026 | Deposit | Principal | 100M |
| Mar 1, 2027 | Year 1 interest | 100M x 5% = 5M | 105M |
| Mar 1, 2028 | Year 2 interest | 105M x 5% = 5.25M | 110.25M |
| Mar 1, 2029 | Year 3 interest | 110.25M x 5% = 5.5125M | 115.76M |
| Mar 1, 2029 | Maturity | Auto-deactivate + notify | Final: 115.76M |

## Approach

Extend the existing `assets` table with savings-specific columns. Reuse the existing `bot_scheduled_tasks` scheduler system.

## Data Model

### New columns on `assets` table (migration 005)

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `asset_type` | `TEXT NOT NULL` | `'income'` | `'income'` (regular) or `'savings'` (interest-bearing) |
| `principal_amount` | `NUMERIC(12,2)` | `NULL` | Original deposit (savings only). `amount` tracks current balance. |
| `compound_frequency` | `TEXT` | `NULL` | `'monthly'`, `'quarterly'`, `'yearly'` |
| `maturity_date` | `DATE` | `NULL` | When the savings term ends |
| `start_date` | `DATE` | `NULL` | When the savings term started |

### How existing fields are reused

- `amount` = current balance (starts at principal, grows with interest)
- `interest_rate` = annual rate (already exists, currently unused for processing)
- `next_date` = next interest application date
- `active` = `false` when matured or early-closed

### Asset types

| Aspect | Income | Savings |
|--------|--------|---------|
| Amount meaning | Fixed payment per period | Current balance (grows) |
| Interest | N/A | Compounds on balance |
| Duration | Indefinite | Fixed term (maturity date) |
| End behavior | Manual deactivation | Auto-deactivates at maturity |

### Model changes

- New enum `AssetType`: `income`, `savings`
- Add `quarterly` to `AssetFrequency`
- `AssetCreate` gains optional fields: `asset_type`, `principal_amount`, `compound_frequency`, `maturity_date`, `start_date`
- `AssetOut` gains the same fields

## Interest Calculation

**Formula:**
```
interest = current_amount x (annual_rate / 100 / compound_periods_per_year)
```

**Compound frequency mapping:**

| Frequency | Periods/year | Example cron (start Mar 1) |
|-----------|-------------|---------------------------|
| monthly | 12 | `0 0 1 * *` |
| quarterly | 4 | `0 0 1 */3 *` |
| yearly | 1 | `0 0 1 3 *` |

## Double-Counting Prevention

**Decision:** Interest updates the asset balance only — no income transaction is created.

When user asks "total money":
- Cash = sum of all transactions = 90M
- Savings = asset current balance = 105M
- Total = 90M + 105M = 195M (no double-counting)

No expense transaction is created when depositing into savings (no validation against cash balance — this is a tracker, not a bank).

## Scheduler Flow

When triggered for a savings asset:

1. Fetch savings asset by ID, verify `asset_type='savings'` and `active=True`
2. Calculate interest: `amount x (interest_rate / 100 / periods_per_year)`
3. Update `amount` += interest
4. Advance `next_date` to next compound period
5. If `next_date > maturity_date`: set `active=False`, send maturity notification
6. Log the interest application

**Maturity notification** (injected as synthetic bot message):
> "Your savings '[name]' has matured! Final balance: 115.76M (started at 100M on Mar 1, 2026). The savings has been deactivated."

## MCP Tools

### New tools

| Tool | Description |
|------|-------------|
| `create_savings_deposit` | Create savings asset + scheduler task. Params: name, amount, interest_rate, compound_frequency, start_date, maturity_date, category |
| `process_savings_interest` | Called by scheduler. Calculates/applies interest, checks maturity. |
| `list_savings` | List savings deposits (filter `asset_type='savings'`). Shows principal, current balance, interest earned, maturity date. |
| `close_savings_early` | Deactivate savings before maturity. Stops scheduler, marks inactive. |

### Modified tools

| Tool | Change |
|------|--------|
| `list_assets` | Add `asset_type` filter parameter |
| `delete_asset` | Also delete associated scheduler task |

## Testing Strategy

| Layer | Tests | Coverage |
|-------|-------|----------|
| Unit (models) | `test_models/test_asset.py` | New field validation |
| Unit (tools) | `test_tools/test_financial_tools.py` | create_savings_deposit, process_savings_interest, close_savings_early |
| Integration (DB) | `test_db/test_asset_repo.py` | New repo methods |
| Interest math | `test_tools/test_financial_tools.py` | Compound interest: monthly, quarterly, yearly. Maturity detection. |

### Key test cases

- 100M at 5%/year, annual compound, 3 years = 115.76M
- Monthly compounding verification
- Maturity auto-deactivation
- Early close stops scheduler

## Migration

File: `packages/core/src/flux_core/migrations/005_asset_savings.sql`

```sql
ALTER TABLE assets ADD COLUMN asset_type TEXT NOT NULL DEFAULT 'income'
    CHECK (asset_type IN ('income', 'savings'));
ALTER TABLE assets ADD COLUMN principal_amount NUMERIC(12,2);
ALTER TABLE assets ADD COLUMN compound_frequency TEXT
    CHECK (compound_frequency IN ('monthly', 'quarterly', 'yearly'));
ALTER TABLE assets ADD COLUMN maturity_date DATE;
ALTER TABLE assets ADD COLUMN start_date DATE;
```

## Follow-up (out of scope)

- Wire up scheduler automation for regular income assets (`asset_type='income'`) — e.g., auto-create rent income transactions monthly
