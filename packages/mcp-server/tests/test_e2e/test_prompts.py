"""Tests for MCP prompt pure functions."""
from flux_mcp.prompts import analyze_spending_prompt, budget_advice_prompt


def test_analyze_spending_prompt_structure():
    result = analyze_spending_prompt("user1", "monthly")
    assert "name" in result
    assert "description" in result
    assert "arguments" in result
    assert "template" in result
    assert "user1" in result["description"]


def test_analyze_spending_prompt_period():
    result = analyze_spending_prompt("u", "weekly")
    assert "weekly" in result["description"]


def test_budget_advice_prompt_structure():
    result = budget_advice_prompt("user1", "Food")
    assert "name" in result
    assert "description" in result
    assert "arguments" in result
    assert "template" in result
    assert "Food" in result["description"]


def test_budget_advice_prompt_category():
    result = budget_advice_prompt("u", "Transport")
    assert "Transport" in result["description"]
