"""LangChain tools for the deepagents runner.

This package mirrors the MCP server's tool surface but runs in-process:
each tool wraps a flux_core Use Case with ``user_id`` closed over, so the
model literally cannot query another user's data.

Domain modules land here incrementally; see the Phase 2 plan for the full
roster. Task 2.10 will add a top-level ``build_tools`` assembler that
aggregates all domain builders.
"""
from .transactions import build_transaction_tools

__all__ = ["build_transaction_tools"]
