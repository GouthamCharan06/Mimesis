"""Retry utilities with bounded exponential backoff for transient provider failures."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.errors import ProviderError, ProviderTimeoutError
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# Default retry configuration for external provider calls
PROVIDER_RETRY_ATTEMPTS = 3
PROVIDER_RETRY_MIN_WAIT = 1  # seconds
PROVIDER_RETRY_MAX_WAIT = 30  # seconds
PROVIDER_RETRY_MULTIPLIER = 2


def log_retry_attempt(retry_state: RetryCallState) -> None:
    """Log each retry attempt with context."""
    logger.warning(
        "provider_retry",
        attempt=retry_state.attempt_number,
        wait=retry_state.next_action,
        fn=getattr(retry_state.fn, "__name__", str(retry_state.fn)),
    )


def with_provider_retry(
    max_attempts: int = PROVIDER_RETRY_ATTEMPTS,
    min_wait: float = PROVIDER_RETRY_MIN_WAIT,
    max_wait: float = PROVIDER_RETRY_MAX_WAIT,
) -> Callable[..., Any]:
    """Decorator for retrying external provider calls with exponential backoff."""
    return retry(
        retry=retry_if_exception_type((ProviderError, ProviderTimeoutError, ConnectionError)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=PROVIDER_RETRY_MULTIPLIER, min=min_wait, max=max_wait),
        before_sleep=log_retry_attempt,
        reraise=True,
    )
