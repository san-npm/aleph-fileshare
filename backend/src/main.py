"""AlephFileShare Backend — FastAPI application entry point."""

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from src.api import auth, files, health, recommendations

# Logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("aleph-fileshare")

# CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage_mode = os.getenv("STORAGE_MODE", "local")
    logger.info(f"AlephFileShare API starting — storage_mode={storage_mode}")

    # Validate critical env vars in production
    if storage_mode == "aleph":
        challenge_secret = os.getenv("CHALLENGE_SECRET", "")
        if not challenge_secret or len(challenge_secret) < 32:
            logger.error("CHALLENGE_SECRET must be set to a 32+ char string in production")
            raise RuntimeError("CHALLENGE_SECRET not configured for production")
        if not os.getenv("ALEPH_PRIVATE_KEY"):
            logger.warning("ALEPH_PRIVATE_KEY not set — Aleph storage will fail")

    max_file_size = int(os.getenv("MAX_FILE_SIZE_BYTES", "0"))
    if max_file_size < 0:
        logger.error("MAX_FILE_SIZE_BYTES must be a positive integer")
        raise RuntimeError("Invalid MAX_FILE_SIZE_BYTES")

    yield
    logger.info("AlephFileShare API shutting down")


# App
app = FastAPI(
    title="AlephFileShare API",
    description="Decentralized file sharing powered by Aleph Cloud",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- File-backed rate limiter (works across serverless restarts) ---
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "30"))


def _rate_limit_dir() -> Path:
    return Path(os.getenv("LOCAL_DATA_DIR", "/tmp/aleph-fileshare")) / "rate_limits"


def _get_rate_limit_count(client_ip: str) -> tuple[int, list[float]]:
    """Read rate limit entries from disk for a client IP."""
    safe_key = client_ip.replace(":", "_").replace(".", "_")
    path = _rate_limit_dir() / f"{safe_key}.json"
    now = time.time()

    if not path.exists():
        return 0, []

    try:
        entries = json.loads(path.read_text())
        # Prune expired entries
        valid = [t for t in entries if now - t < RATE_LIMIT_WINDOW]
        return len(valid), valid
    except (json.JSONDecodeError, OSError):
        return 0, []


def _record_rate_limit(client_ip: str, entries: list[float]) -> None:
    """Write rate limit entries to disk."""
    rl_dir = _rate_limit_dir()
    rl_dir.mkdir(parents=True, exist_ok=True)
    safe_key = client_ip.replace(":", "_").replace(".", "_")
    path = rl_dir / f"{safe_key}.json"

    entries.append(time.time())
    try:
        path.write_text(json.dumps(entries))
    except OSError:
        pass  # Best-effort — don't block requests on FS errors


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next) -> Response:
    """File-backed rate limiter based on client IP.

    Uses disk storage instead of in-memory dicts so that rate limits
    survive serverless cold starts and work across replicas sharing a volume.
    """
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"

    count, entries = _get_rate_limit_count(client_ip)
    if count >= RATE_LIMIT_MAX:
        return Response(
            content='{"detail":"Rate limit exceeded.","code":"RATE_LIMITED"}',
            status_code=429,
            media_type="application/json",
        )

    _record_rate_limit(client_ip, entries)
    response = await call_next(request)
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next) -> Response:
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if os.getenv("STORAGE_MODE") == "aleph":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Register routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(recommendations.router)

