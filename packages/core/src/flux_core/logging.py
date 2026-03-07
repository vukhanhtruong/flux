"""Structured logging configuration for all flux packages."""

from __future__ import annotations

import logging
import os

import structlog


LAYER_ENV_MAP = {
    "LOG_LEVEL_SQL": "flux_core.sqlite",
    "LOG_LEVEL_ZVEC": "flux_core.vector",
    "LOG_LEVEL_UOW": "flux_core.uow",
    "LOG_LEVEL_EVENTS": "flux_core.events",
    "LOG_LEVEL_BOT": "flux_bot",
}


def configure_logging() -> None:
    """Configure structlog with console renderer for development.

    Reads LOG_LEVEL from env (default: INFO).
    Reads LOG_LEVEL_<LAYER> overrides for per-layer control.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib root logger level
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level, logging.INFO),
    )

    # Apply per-layer overrides
    for env_var, logger_name in LAYER_ENV_MAP.items():
        level = os.getenv(env_var)
        if level:
            logging.getLogger(logger_name).setLevel(getattr(logging, level.upper(), logging.DEBUG))
