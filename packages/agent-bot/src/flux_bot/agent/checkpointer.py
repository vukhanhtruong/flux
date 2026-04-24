"""LangGraph SQLite checkpointer bound to the flux.db file."""

from contextlib import asynccontextmanager

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


@asynccontextmanager
async def build_checkpointer(db_path: str):
    async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
        yield saver
