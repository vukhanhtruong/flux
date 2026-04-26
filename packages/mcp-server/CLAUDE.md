# MCP Server

FastMCP 3.0 protocol server — thin adapter over Use Cases.

## Pattern

```
FastMCP tool registration → instantiate Use Case → call execute() → return dict
```

## Key Points

- Tools registered via `register_*_tools()` functions
- Each tools file exports a registration function called during server setup
- **NO AI provider dependency** — purely tools/data
- Agent orchestrator owns AI reasoning, not this server
- Tool functions return `dict`, not Pydantic models

## Tool Registration

```python
# In src/flux_mcp/tools/transactions.py
def register_transaction_tools(mcp: FastMCP, get_uow, get_embedding_svc):
    @mcp.tool()
    async def add_transaction(user_id: str, date: str, amount: str, ...):
        """Add a new transaction."""
        uow = get_uow()
        svc = get_embedding_svc()
        use_case = AddTransaction(uow, svc)
        txn = await use_case.execute(user_id, date, Decimal(amount), ...)
        return {"id": str(txn.id), "amount": str(txn.amount), ...}
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
fastmcp dev src/flux_mcp/server.py   # MCP inspector
```
