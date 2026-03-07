"""Main FastAPI application."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flux_api.deps import get_db
from flux_core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise SQLite+zvec on startup, clean up on shutdown."""
    configure_logging()
    get_db()
    yield


app = FastAPI(
    title="flux API",
    description="Personal finance AI agent REST API",
    version="0.1.0",
    lifespan=lifespan,
)

_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174")
_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


# Register routes
from flux_api.routes.transactions import router as transactions_router  # noqa: E402
from flux_api.routes.budgets import router as budgets_router  # noqa: E402
from flux_api.routes.goals import router as goals_router  # noqa: E402
from flux_api.routes.subscriptions import router as subscriptions_router  # noqa: E402
from flux_api.routes.assets import router as assets_router  # noqa: E402
from flux_api.routes.analytics import router as analytics_router  # noqa: E402
from flux_api.routes.profile import router as profile_router  # noqa: E402
from flux_api.routes.scheduled_tasks import router as scheduled_tasks_router  # noqa: E402

app.include_router(transactions_router)
app.include_router(budgets_router)
app.include_router(goals_router)
app.include_router(subscriptions_router)
app.include_router(assets_router)
app.include_router(analytics_router)
app.include_router(profile_router)
app.include_router(scheduled_tasks_router)

from flux_api.routes.backups import router as backups_router  # noqa: E402

app.include_router(backups_router)
