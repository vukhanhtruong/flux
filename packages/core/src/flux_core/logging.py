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

# Third-party loggers to suppress at WARNING unless explicitly overridden
_NOISY_LOGGERS = [
    "httpx",
    "httpcore",
    "telegram",
    "python_telegram_bot",
    "hpack",
    "fastembed",
    "huggingface_hub",
    "uvicorn",
    "fastapi",
]


def configure_logging() -> None:
    """Configure structlog with console renderer for development.

    Reads LOG_LEVEL from env (default: INFO).
    Reads LOG_LEVEL_<LAYER> overrides for per-layer control.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level_num = getattr(logging, log_level, logging.INFO)

    # Processors for formatting (no filter_by_level — stdlib handles that itself)
    formatting_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Configure structlog (for our code using structlog.get_logger)
    # Ends with wrap_for_formatter so the ProcessorFormatter does final rendering
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
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging through structlog's renderer too
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(),
        ],
        foreign_pre_chain=formatting_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level_num)

    # Suppress noisy third-party loggers
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Apply per-layer overrides
    for env_var, logger_name in LAYER_ENV_MAP.items():
        level = os.getenv(env_var)
        if level:
            logging.getLogger(logger_name).setLevel(getattr(logging, level.upper(), logging.DEBUG))
