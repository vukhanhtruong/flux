"""Analytics use cases."""

from flux_core.use_cases.analytics.calculate_financial_health import CalculateFinancialHealth
from flux_core.use_cases.analytics.generate_spending_report import GenerateSpendingReport
from flux_core.use_cases.analytics.get_category_breakdown import GetCategoryBreakdown
from flux_core.use_cases.analytics.get_summary import GetSummary
from flux_core.use_cases.analytics.get_trends import GetTrends

__all__ = [
    "CalculateFinancialHealth",
    "GenerateSpendingReport",
    "GetCategoryBreakdown",
    "GetSummary",
    "GetTrends",
]
