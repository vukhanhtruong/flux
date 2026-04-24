"""Smoke tests confirming new Phase 1 dependencies are importable."""


def test_deepagents_importable():
    import deepagents  # noqa: F401


def test_langgraph_checkpoint_sqlite_importable():
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver  # noqa: F401


def test_langchain_core_importable():
    from langchain_core.tools import tool  # noqa: F401


def test_cryptography_fernet_importable():
    from cryptography.fernet import Fernet  # noqa: F401


def test_rich_importable():
    import rich  # noqa: F401
