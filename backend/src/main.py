"""AlephFileShare Backend — FastAPI application entry point."""

import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from src.api import auth, files, health

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


# --- Simple in-memory rate limiter ---
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 30  # requests per window


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next) -> Response:
    """Simple in-memory rate limiter based on client IP."""
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Clean old entries
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX:
        return Response(
            content='{"detail":"Rate limit exceeded.","code":"RATE_LIMITED"}',
            status_code=429,
            media_type="application/json",
        )

    _rate_limit_store[client_ip].append(now)
    response = await call_next(request)
    return response


# Register routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(files.router)



