"""MCP Prompts for flux.

Prompts are templated instructions for AI agents working with financial data.
"""


def analyze_spending_prompt(
    user_id: str,
    period: str = "monthly"
) -> dict:
    """Generate a prompt for spending analysis.

    This prompt guides the AI to analyze spending patterns and provide insights.
    """
    return {
        "name": "analyze_spending",
        "description": f"Analyze {period} spending patterns for user {user_id}",
        "arguments": [
            {
                "name": "user_id",
                "description": "The user ID to analyze",
                "required": True,
                "type": "string",
                "default": user_id
            },
            {
                "name": "period",
                "description": "Time period for analysis (daily, weekly, monthly, yearly)",
                "required": False,
                "type": "string",
                "default": period
            }
        ],
        "template": f"""
Analyze the spending patterns for user {user_id} over the {period} period.

Please provide:
1. Total spending breakdown by category
2. Comparison to budgets (if set)
3. Unusual or noteworthy transactions
4. Spending trends and patterns
5. Actionable recommendations

Use the available tools to:
- List recent transactions
- Get budget summary
- Generate spending report
- Calculate financial health score
"""
    }


def budget_advice_prompt(
    user_id: str,
    category: str
) -> dict:
    """Generate a prompt for budget advice.

    This prompt guides the AI to provide budget recommendations.
    """
    return {
        "name": "budget_advice",
        "description": f"Provide budget advice for {category} spending",
        "arguments": [
            {
                "name": "user_id",
                "description": "The user ID to advise",
                "required": True,
                "type": "string",
                "default": user_id
            },
            {
                "name": "category",
                "description": "The spending category to focus on",
                "required": True,
                "type": "string",
                "default": category
            }
        ],
        "template": f"""
Provide budget advice for user {user_id}'s {category} spending.

Please analyze:
1. Current spending in this category
2. Budget limit (if set)
3. Spending trends over time
4. Comparison to typical benchmarks

Provide:
1. Assessment of current budget health
2. Specific recommendations for this category
3. Suggested budget limit (if none is set)
4. Tips for reducing spending (if over budget)

Use the available tools to:
- List transactions in this category
- Get current budget for this category
- Forecast budget usage
- Search for similar transactions
"""
    }
