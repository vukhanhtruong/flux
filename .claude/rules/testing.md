---
paths:
  - "**/tests/**/*.py"
  - "**/tests/**/*.ts"
  - "**/*.test.ts"
  - "**/test_*.py"
---

# Testing Patterns

## Test Categories

| Category | Location | Purpose | Dependencies |
|----------|----------|---------|--------------|
| Unit | `test_models/` | Pydantic validation | None |
| Repository | `test_repositories/` | SQLite repos | temp SQLite file |
| Vector | `test_vector/` | SqliteVecStore | same SQLite DB |
| UoW | `test_uow/` | Single-transaction, rollback | temp SQLite |
| Event | `test_events/` | EventBus pub/sub | None |
| Use Case | `test_use_cases/` | Business logic | Mocked repos |
| E2E | `test_e2e/` | Full protocol | Seeded SQLite |
| Performance | `test_perf/` | Latency, concurrency | pytest-benchmark |

## pytest-asyncio Configuration

All async tests use `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` decorator needed.

```python
# Correct - no decorator needed
async def test_something():
    result = await async_function()
    assert result == expected
```

## Fixtures

- Use `tmp_path` fixture for tests needing real SQLite files
- Use `tmp_path_factory` for session-scoped temp directories

```python
def test_with_temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    db.connect()
    # ...
```

## Coverage

**Minimum 90% test coverage — non-negotiable.** CI will fail below this threshold.

```bash
./test-all.sh --coverage    # Run with coverage
```
