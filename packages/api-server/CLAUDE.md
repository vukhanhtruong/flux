# API Server

FastAPI REST API — thin adapter over Use Cases.

## Pattern

```
FastAPI route → instantiate Use Case → call execute() → return Pydantic response
```

## Structure

- Routes in `src/flux_api/routes/`
- Each route module handles one domain (transactions, budgets, goals, etc.)
- Dependency injection for UoW and services
- Request validation via Pydantic models
- Response models define API contract

## Example Route

```python
@router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    request: CreateTransactionRequest,
    uow: UnitOfWork = Depends(get_uow),
    embedding_svc: EmbeddingProvider = Depends(get_embedding_svc),
):
    use_case = AddTransaction(uow, embedding_svc)
    txn = await use_case.execute(
        user_id=request.user_id,
        date=request.date,
        amount=request.amount,
        ...
    )
    return TransactionResponse.from_model(txn)
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
uvicorn flux_api.app:app --reload    # Port 8000
```
