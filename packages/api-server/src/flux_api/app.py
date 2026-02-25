"""Main FastAPI application."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="flux API",
    description="Personal finance AI agent REST API",
    version="0.1.0",
)

_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
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
from flux_api.routes.transactions import router as transactions_router
from flux_api.routes.budgets import router as budgets_router
from flux_api.routes.goals import router as goals_router
from flux_api.routes.subscriptions import router as subscriptions_router
from flux_api.routes.assets import router as assets_router
from flux_api.routes.analytics import router as analytics_router
from flux_api.routes.profile import router as profile_router

app.include_router(transactions_router)
app.include_router(budgets_router)
app.include_router(goals_router)
app.include_router(subscriptions_router)
app.include_router(assets_router)
app.include_router(analytics_router)
app.include_router(profile_router)
