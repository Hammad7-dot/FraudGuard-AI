"""Custom exceptions and handlers that never leak stack traces to clients."""
from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class FraudGuardError(Exception):
    """Base application error."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)


class NotFoundError(FraudGuardError):
    status_code = status.HTTP_404_NOT_FOUND


class ValidationFailedError(FraudGuardError):
    status_code = status.HTTP_400_BAD_REQUEST


class UnauthorizedError(FraudGuardError):
    status_code = status.HTTP_401_UNAUTHORIZED


class RateLimitedError(FraudGuardError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


async def fraudguard_exception_handler(request: Request, exc: FraudGuardError) -> JSONResponse:
    logger.warning("handled_error path=%s message=%s", request.url.path, exc.message)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message, "path": str(request.url.path)})


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error path=%s type=%s", request.url.path, type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_server_error", "path": str(request.url.path)},
    )
