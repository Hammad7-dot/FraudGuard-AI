"""Request validation middleware for input sanitization and size limits."""
from __future__ import annotations

import json
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation and sanitization.

    - Enforces maximum request body size
    - Validates JSON content type for POST/PUT/PATCH
    - Sanitizes request headers
    """

    def __init__(
        self,
        app,
        max_body_size: Optional[int] = None,
        allowed_content_types: Optional[list[str]] = None,
    ) -> None:
        super().__init__(app)
        self.max_body_size = max_body_size or get_settings().max_request_bytes
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_body_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Request too large",
                            "message": f"Maximum request size is {self.max_body_size} bytes",
                            "max_size_bytes": self.max_body_size,
                        },
                    )
            except ValueError:
                pass  # Invalid content-length, let downstream handle it

        # Validate content type for mutating methods
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            if content_type and content_type not in self.allowed_content_types:
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "Unsupported media type",
                        "message": f"Content-Type '{content_type}' not supported",
                        "allowed_types": self.allowed_content_types,
                    },
                )

        # Sanitize headers (remove potentially sensitive ones from logs)
        # This is handled by the logging middleware's safe_extra function

        return await call_next(request)


def create_validation_middleware(app, max_body_size: int = None):
    """Factory function to create validation middleware with settings."""
    if max_body_size is None:
        max_body_size = get_settings().max_request_bytes
    return ValidationMiddleware(app, max_body_size=max_body_size)