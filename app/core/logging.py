"""Structured logging setup. Never log secrets or full PII payloads."""
import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Optional

from app.core.config import get_settings


# Context variable for correlation ID (request tracing)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class _StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if available
        corr_id = correlation_id_var.get()
        if corr_id:
            log_entry["correlation_id"] = corr_id

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info"
            }:
                log_entry[key] = value

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def configure_logging() -> None:
    """Configure root logger with structured JSON formatting."""
    settings = get_settings()
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(settings.log_level.upper())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_StructuredFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with structured logging configured."""
    configure_logging()
    return logging.getLogger(name)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID for current context (request tracing).

    Args:
        correlation_id: Optional correlation ID. If not provided, generates a new UUID.

    Returns:
        The correlation ID that was set.
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    correlation_id_var.set(None)


def safe_extra(**kwargs: Any) -> dict:
    """Redact anything that looks like a secret before logging.

    Args:
        **kwargs: Key-value pairs to sanitize.

    Returns:
        Dictionary with sensitive values redacted.
    """
    redacted = {}
    for k, v in kwargs.items():
        if any(s in k.lower() for s in ("password", "secret", "api_key", "token", "key")):
            redacted[k] = "***"
        else:
            redacted[k] = v
    return redacted


class LoggingContext:
    """Context manager for adding structured context to logs.

    Usage:
        with LoggingContext(user_id="123", transaction_id="tx-456"):
            logger.info("Processing transaction")
    """

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = safe_extra(**kwargs)
        self.old_factory = logging.getLogRecordFactory()

    def __enter__(self) -> "LoggingContext":
        def record_factory(*args: Any, **kw: Any) -> logging.LogRecord:
            record = self.old_factory(*args, **kw)
            for k, v in self.kwargs.items():
                setattr(record, k, v)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        logging.setLogRecordFactory(self.old_factory)
