"""FastAPI application entrypoint for FraudGuard AI."""
from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import analytics, health, risk, transactions, users
from app.core.config import get_settings
from app.core.exceptions import FraudGuardError, fraudguard_exception_handler, unhandled_exception_handler
from app.core.logging import configure_logging, get_logger, set_correlation_id, clear_correlation_id
from app.core.rate_limiter import create_rate_limiter_middleware
from app.core.validation import create_validation_middleware
from app.db.session import init_db

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_fraudguard_ai environment=%s", settings.environment)
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware for request logging and correlation ID tracking."""
    # Generate or extract correlation ID
    correlation_id = request.headers.get("x-correlation-id") or set_correlation_id()
    set_correlation_id(correlation_id)

    start_time = time.perf_counter()

    # Log request
    logger.info(
        "request_started",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_host": request.client.host if request.client else None,
        }
    )

    try:
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000

        # Log response
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time_ms": round(process_time, 2),
            }
        )

        # Add correlation ID to response headers
        response.headers["x-correlation-id"] = correlation_id
        return response
    except Exception as exc:
        process_time = (time.perf_counter() - start_time) * 1000
        logger.error(
            "request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(exc),
                "process_time_ms": round(process_time, 2),
            },
            exc_info=True
        )
        raise
    finally:
        clear_correlation_id()


# Add validation middleware (first, to reject invalid requests early)
app.add_middleware(create_validation_middleware)

# Add rate limiting middleware (before CORS so it applies to all requests)
app.add_middleware(create_rate_limiter_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(FraudGuardError, fraudguard_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(risk.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/health")
def root_health() -> dict:
    return {"status": "ok"}


# Risk Copilot single-page UI — served same-origin so it can call the API
# without needing CORS. Visit http://localhost:8000/ui/
app.mount("/ui", StaticFiles(directory="dashboard/static", html=True), name="ui")
