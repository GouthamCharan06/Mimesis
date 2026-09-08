"""Centralized exception handling and API error responses."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorCode(StrEnum):
    """Application-level error codes."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CANCELLED = "CANCELLED"


class ErrorResponse(BaseModel):
    """Standardized API error response."""
    error_code: ErrorCode
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class MimesisError(Exception):
    """Base exception for all Mimesis application errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details


class NotFoundError(MimesisError):
    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(message, ErrorCode.NOT_FOUND, 404, **kwargs)


class ValidationError(MimesisError):
    def __init__(self, message: str = "Validation failed", **kwargs: Any) -> None:
        super().__init__(message, ErrorCode.VALIDATION_ERROR, 422, **kwargs)


class ProviderError(MimesisError):
    def __init__(self, message: str = "External provider error", **kwargs: Any) -> None:
        super().__init__(message, ErrorCode.PROVIDER_ERROR, 502, **kwargs)


class ProviderTimeoutError(MimesisError):
    def __init__(self, message: str = "Provider timeout", **kwargs: Any) -> None:
        super().__init__(message, ErrorCode.PROVIDER_TIMEOUT, 504, **kwargs)


class WorkflowError(MimesisError):
    def __init__(self, message: str = "Workflow execution error", **kwargs: Any) -> None:
        super().__init__(message, ErrorCode.WORKFLOW_ERROR, 500, **kwargs)


class InvalidStateTransitionError(MimesisError):
    def __init__(self, message: str = "Invalid state transition", **kwargs: Any) -> None:
        super().__init__(message, ErrorCode.INVALID_STATE_TRANSITION, 409, **kwargs)


async def mimesis_error_handler(request: Request, exc: MimesisError) -> JSONResponse:
    """Handle MimesisError exceptions with structured responses."""
    logger.error(
        "application_error",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        ).model_dump(),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected exceptions."""
    logger.exception("unhandled_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred",
        ).model_dump(),
    )
