# Design: Subscriptions in Spending Report

**Date:** 2026-02-25
**Status:** Approved

## Problem

`generate_spending_report` (and the REST/MCP endpoints that wrap it) only queries the `transactions` table. Active subscriptions — Netflix, Google One, etc. — are tracked in a separate `subscriptions` table and are completely invisible in any report.

## Decision

Add a dedicated `subscriptions` block to the `generate_spending_report` output. Subscriptions are **not** merged into the transaction totals — they appear as a separate section showing active recurring commitments.

**Rejected alternatives:**
- *Auto-generate transactions on `advance_subscription()`* — risks double-counting if the user also manually logs subscription payments as transactions.
- *Project subscriptions into the date range* — overly complex date math, especially for yearly billing cycles.

## Output Shape

```python
{
  # existing fields unchanged
  "total_income": "...",
  "total_expenses": "...",
  "net": "...",
  "count": ...,
  "category_breakdown": [...],
  "start_date": "...",
  "end_date": "...",

  # NEW
  "subscriptions": {
    "active_count": 3,
    "monthly_total": "34.97",   # monthly + yearly/12, normalized
    "annual_total": "419.64",   # monthly_total * 12
    "items": [
      {
        "name": "Netflix",
        "amount": "15.99",
        "billing_cycle": "monthly",
        "category": "Entertainment",
        "next_date": "2026-03-01"
      }
    ]
  }
}
```

`monthly_total` normalizes all amounts: monthly subscriptions at face value, yearly subscriptions divided by 12. This is a snapshot of active recurring commitments — no date-range projection.

## Layers Changed

| Layer | Change |
|---|---|
| `packages/core/src/flux_core/tools/analytics_tools.py` | `generate_spending_report` accepts `sub_repo`; fetches active subs, computes totals, appends `subscriptions` block |
| `packages/mcp-server/src/flux_mcp/tools/analytics_tools.py` | Pass `sub_repo` when calling `generate_spending_report` |
| `packages/api-server/src/flux_api/routes/analytics.py` | Pass `sub_repo` when calling `generate_spending_report` |
| Tests | Update existing tests + add cases for `subscriptions` block |

No DB changes. No migrations. No new models.
