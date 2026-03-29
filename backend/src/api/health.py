"""Health check and network monitoring routes.

Provides:
  GET /health                   — Basic service health (uptime, storage mode)
  GET /api/health/network       — Aleph network health (Guardian Agent data)
  GET /api/health/incidents     — Recent security incidents
  GET /api/health/throttled     — Currently throttled wallets (admin)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

router = APIRouter(tags=["Health"])

VERSION = "0.1.0"

# Guardian Agent output files (read-only here)
_HEALTH_FILE = Path(
    os.getenv("GUARDIAN_HEALTH_FILE", "/tmp/aleph-fileshare-network-health.json")
)
_INCIDENTS_FILE = Path(
    os.getenv("GUARDIAN_INCIDENTS_FILE", "/tmp/aleph-fileshare-incidents.json")
)
_THROTTLE_FILE = Path(
    os.getenv("GUARDIAN_THROTTLE_FILE", "/tmp/aleph-fileshare-throttled-wallets.json")
)

# Simple admin token for privileged health endpoints (not for production auth)
_ADMIN_TOKEN = os.getenv("HEALTH_ADMIN_TOKEN", "")


def _load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return default


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint for Docker Compose and monitoring."""
    storage_mode = os.getenv("STORAGE_MODE", "local")
    return {
        "status": "ok",
        "version": VERSION,
        "storage_mode": storage_mode,
        "aleph_connected": storage_mode == "aleph",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/health/network")
async def network_health() -> dict:
    """Return the latest Aleph network health report from the Guardian Agent.

    Includes node availability, average latency, and an overall health score.
    Returns a synthetic "no data yet" response when the Guardian Agent has
    not yet run.
    """
    data = _load_json(_HEALTH_FILE, None)
    if data is None:
        return {
            "status": "no_data",
            "message": "Guardian Agent has not yet produced a health report.",
            "health_score": None,
            "nodes_checked": 0,
            "nodes_healthy": 0,
            "nodes_degraded": 0,
            "nodes_down": 0,
            "avg_latency_ms": None,
            "timestamp": None,
        }

    # Classify overall status
    score = data.get("health_score", 100)
    if score >= 80:
        status = "healthy"
    elif score >= 50:
        status = "degraded"
    else:
        status = "critical"

    return {
        "status": status,
        "health_score": score,
        "nodes_checked": data.get("nodes_checked", 0),
        "nodes_healthy": data.get("nodes_healthy", 0),
        "nodes_degraded": data.get("nodes_degraded", 0),
        "nodes_down": data.get("nodes_down", 0),
        "avg_latency_ms": data.get("avg_latency_ms"),
        "timestamp": data.get("timestamp"),
        "simulated": data.get("simulated", False),
    }


@router.get("/api/health/incidents")
async def recent_incidents(
    limit: int = 20,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> dict:
    """Return recent security incidents detected by the Guardian Agent.

    Requires X-Admin-Token header when HEALTH_ADMIN_TOKEN env var is set.
    """
    _require_admin(x_admin_token)
    incidents = _load_json(_INCIDENTS_FILE, [])
    # Return most-recent first
    recent = list(reversed(incidents[-limit:]))
    return {
        "total": len(incidents),
        "returned": len(recent),
        "incidents": recent,
    }


@router.get("/api/health/throttled")
async def throttled_wallets(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> dict:
    """Return currently throttled wallets.

    Requires X-Admin-Token header when HEALTH_ADMIN_TOKEN env var is set.
    """
    _require_admin(x_admin_token)
    throttled = _load_json(_THROTTLE_FILE, {})

    # Filter out expired entries
    import time
    from datetime import datetime

    now = time.time()
    active = {}
    for wallet, data in throttled.items():
        expires_str = data.get("expires_at", "")
        try:
            expires_ts = datetime.fromisoformat(
                expires_str.replace("Z", "+00:00")
            ).timestamp()
            if expires_ts >= now:
                active[wallet] = data
        except (ValueError, AttributeError):
            pass

    return {
        "total_active": len(active),
        "throttled": active,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_admin(token: Optional[str]) -> None:
    """Raise 403 if admin token is configured and the provided token is wrong."""
    if not _ADMIN_TOKEN:
        return  # No admin auth configured — open access
    if token != _ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid or missing admin token.")
