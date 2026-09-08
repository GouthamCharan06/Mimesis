"""Structured logging with correlation IDs and contextual metadata."""

from __future__ import annotations

import contextvars
import uuid
from typing import Any

import structlog

import logging

# Context variable for request correlation
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
project_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "project_id", default=""
)


def generate_request_id() -> str:
    """Generate a new unique request correlation ID."""
    return str(uuid.uuid4())


def add_correlation_context(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that injects correlation IDs into every log entry."""
    request_id = request_id_var.get("")
    if request_id:
        event_dict["request_id"] = request_id
    project_id = project_id_var.get("")
    if project_id:
        event_dict["project_id"] = project_id
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for the application."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_correlation_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer()
            if log_level == "DEBUG"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )



def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a named structured logger."""
    return structlog.get_logger(name)  # type: ignore[return-value]
