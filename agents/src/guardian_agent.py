"""Guardian Agent — Network health monitoring and abuse prevention.

Monitors the Aleph node network and detects anomalous upload activity
that may indicate bot abuse or DDoS attempts.

- Polls Aleph node health endpoints and computes an aggregate health score
- Detects upload spike patterns over configurable rolling windows
- Auto-throttles abusive wallets by writing flags to Aleph Aggregates
- Emits automated incident reports as Aleph POST messages

Local mode:  writes all state to JSON files for development/testing.
Aleph mode:  reads node info from Aleph API, writes flags as Aggregates.
"""

import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from agents.src.utils import Config, MetadataClient

logger = logging.getLogger("guardian-agent")

# -------------------------------------------------------------------
# Tunable thresholds
# -------------------------------------------------------------------

# Uploads from a single wallet within SPIKE_WINDOW_SECONDS that triggers alert
SPIKE_UPLOAD_THRESHOLD = int(os.getenv("GUARDIAN_SPIKE_THRESHOLD", "20"))
SPIKE_WINDOW_SECONDS = int(os.getenv("GUARDIAN_SPIKE_WINDOW", "300"))  # 5 min

# Maximum bytes a single wallet can upload in SPIKE_WINDOW_SECONDS
SPIKE_BYTES_THRESHOLD = int(
    os.getenv("GUARDIAN_SPIKE_BYTES", str(500 * 1024 * 1024))  # 500 MB
)

# How long a throttle lasts (seconds)
THROTTLE_DURATION_SECONDS = int(os.getenv("GUARDIAN_THROTTLE_DURATION", "3600"))

# Aleph API endpoint
ALEPH_API_URL = os.getenv("ALEPH_API_URL", "https://official.aleph.cloud")

# Number of nodes to check in health probes
NODE_PROBE_COUNT = int(os.getenv("GUARDIAN_NODE_PROBE_COUNT", "5"))

# Node response time threshold (ms) above which a node is "degraded"
NODE_LATENCY_THRESHOLD_MS = int(
    os.getenv("GUARDIAN_NODE_LATENCY_MS", "2000")
)


class GuardianAgent:
    """Autonomous network guardian agent.

    Continuously monitors Aleph node health and detects anomalous
    upload activity, issuing throttle flags and incident reports.
    """

    def __init__(self, config: Config, metadata_client: MetadataClient) -> None:
        self.config = config
        self.metadata = metadata_client
        self.poll_interval = config.guardian_poll_interval
        self._running = False

        self._throttle_file = Path(
            os.getenv(
                "GUARDIAN_THROTTLE_FILE",
                "/tmp/aleph-fileshare-throttled-wallets.json",
            )
        )
        self._incidents_file = Path(
            os.getenv(
                "GUARDIAN_INCIDENTS_FILE",
                "/tmp/aleph-fileshare-incidents.json",
            )
        )
        self._health_file = Path(
            os.getenv(
                "GUARDIAN_HEALTH_FILE",
                "/tmp/aleph-fileshare-network-health.json",
            )
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the guardian monitoring loop."""
        logger.info(
            f"Guardian Agent starting (mode={self.config.storage_mode}, "
            f"interval={self.poll_interval}s)"
        )
        self._running = True
        while self._running:
            try:
                await self._guardian_cycle()
            except Exception as exc:
                logger.error(f"Guardian cycle error: {exc}", exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Stop the guardian loop gracefully."""
        self._running = False
        logger.info("Guardian Agent stopped.")

    # ------------------------------------------------------------------
    # Main cycle
    # ------------------------------------------------------------------

    async def _guardian_cycle(self) -> None:
        """Single guardian cycle: health probe + anomaly detection."""
        # 1. Probe node health
        health = await self._probe_node_health()
        self._save_health(health)

        # 2. Detect upload spikes
        incidents = self._detect_upload_spikes()

        # 3. Process incidents: throttle abusers, emit reports
        for incident in incidents:
            await self._handle_incident(incident)

        # 4. Expire old throttles
        self._expire_throttles()

        logger.debug(
            f"Guardian cycle done: nodes={health.get('nodes_checked', 0)}, "
            f"healthy={health.get('nodes_healthy', 0)}, "
            f"incidents={len(incidents)}"
        )

    # ------------------------------------------------------------------
    # Node health monitoring
    # ------------------------------------------------------------------

    async def _probe_node_health(self) -> dict:
        """Probe Aleph nodes and compute aggregate health metrics."""
        now = datetime.now(timezone.utc).isoformat()

        if self.config.storage_mode != "aleph":
            return self._simulate_node_health(now)

        node_list = await self._fetch_aleph_nodes()
        results = await asyncio.gather(
            *[self._ping_node(node) for node in node_list],
            return_exceptions=True,
        )

        nodes_checked = len(node_list)
        nodes_healthy = 0
        nodes_degraded = 0
        nodes_down = 0
        total_latency_ms = 0.0

        node_statuses = []
        for node, result in zip(node_list, results):
            if isinstance(result, Exception):
                nodes_down += 1
                node_statuses.append(
                    {"url": node, "status": "down", "latency_ms": None, "error": str(result)}
                )
            else:
                latency_ms, ok = result
                total_latency_ms += latency_ms
                if not ok or latency_ms > NODE_LATENCY_THRESHOLD_MS:
                    nodes_degraded += 1
                    node_statuses.append(
                        {"url": node, "status": "degraded", "latency_ms": latency_ms}
                    )
                else:
                    nodes_healthy += 1
                    node_statuses.append(
                        {"url": node, "status": "healthy", "latency_ms": latency_ms}
                    )

        avg_latency = (
            total_latency_ms / max(1, nodes_checked - nodes_down)
            if nodes_checked > nodes_down
            else None
        )

        health_score = (
            round(nodes_healthy / nodes_checked * 100, 1) if nodes_checked else 100.0
        )

        return {
            "timestamp": now,
            "health_score": health_score,
            "nodes_checked": nodes_checked,
            "nodes_healthy": nodes_healthy,
            "nodes_degraded": nodes_degraded,
            "nodes_down": nodes_down,
            "avg_latency_ms": round(avg_latency, 1) if avg_latency else None,
            "node_statuses": node_statuses,
        }

    def _simulate_node_health(self, timestamp: str) -> dict:
        """Simulate node health for local mode (deterministic mock)."""
        import random

        random.seed(int(time.time()) // 60)  # stable per minute
        nodes_checked = 5
        nodes_down = random.randint(0, 1)
        nodes_degraded = random.randint(0, 1)
        nodes_healthy = nodes_checked - nodes_down - nodes_degraded
        avg_latency = random.uniform(50, 400)

        return {
            "timestamp": timestamp,
            "health_score": round(nodes_healthy / nodes_checked * 100, 1),
            "nodes_checked": nodes_checked,
            "nodes_healthy": max(0, nodes_healthy),
            "nodes_degraded": nodes_degraded,
            "nodes_down": nodes_down,
            "avg_latency_ms": round(avg_latency, 1),
            "node_statuses": [],
            "simulated": True,
        }

    async def _fetch_aleph_nodes(self) -> list[str]:
        """Fetch a list of active Aleph CRN nodes from the network."""
        url = f"{ALEPH_API_URL}/api/v0/nodes?status=active&limit={NODE_PROBE_COUNT}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                nodes = data.get("nodes", [])
                return [n.get("address") for n in nodes if n.get("address")]
        except Exception as exc:
            logger.warning(f"Failed to fetch node list: {exc}")
            return [ALEPH_API_URL]

    async def _ping_node(self, node_url: str) -> tuple[float, bool]:
        """Ping a node and return (latency_ms, ok)."""
        health_url = f"{node_url.rstrip('/')}/status"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(health_url)
                latency_ms = (time.monotonic() - start) * 1000
                return latency_ms, resp.status_code == 200
        except Exception:
            latency_ms = (time.monotonic() - start) * 1000
            return latency_ms, False

    # ------------------------------------------------------------------
    # Upload spike detection
    # ------------------------------------------------------------------

    def _detect_upload_spikes(self) -> list[dict]:
        """Scan recent upload events and detect anomalous patterns.

        Returns a list of incident dicts for wallets that exceeded thresholds.
        """
        db = self.metadata._load_db()
        now = time.time()
        window_start = now - SPIKE_WINDOW_SECONDS

        # wallet → {"count": int, "bytes": int, "files": list}
        wallet_activity: dict[str, dict] = defaultdict(
            lambda: {"count": 0, "bytes": 0, "files": []}
        )

        for file_hash, meta in db.items():
            uploader = meta.get("uploader", "")
            if not uploader:
                continue

            uploaded_at_str = meta.get("uploaded_at", "")
            try:
                uploaded_ts = datetime.fromisoformat(
                    uploaded_at_str.replace("Z", "+00:00")
                ).timestamp()
            except ValueError:
                continue

            if uploaded_ts < window_start:
                continue

            wallet_activity[uploader]["count"] += 1
            wallet_activity[uploader]["bytes"] += meta.get("size_bytes", 0)
            wallet_activity[uploader]["files"].append(file_hash)

        incidents = []
        throttled = self._load_throttled()

        for wallet, activity in wallet_activity.items():
            # Skip already throttled
            if wallet in throttled:
                continue

            reasons = []
            if activity["count"] >= SPIKE_UPLOAD_THRESHOLD:
                reasons.append(
                    f"upload_count={activity['count']} >= threshold={SPIKE_UPLOAD_THRESHOLD}"
                )
            if activity["bytes"] >= SPIKE_BYTES_THRESHOLD:
                mb = activity["bytes"] // (1024 * 1024)
                reasons.append(
                    f"upload_bytes={mb}MB >= threshold={SPIKE_BYTES_THRESHOLD // (1024*1024)}MB"
                )

            if reasons:
                incidents.append(
                    {
                        "type": "upload_spike",
                        "wallet": wallet,
                        "window_seconds": SPIKE_WINDOW_SECONDS,
                        "upload_count": activity["count"],
                        "upload_bytes": activity["bytes"],
                        "files": activity["files"],
                        "reasons": reasons,
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                logger.warning(
                    f"Upload spike detected: wallet={wallet[:10]}... "
                    f"count={activity['count']} bytes={activity['bytes']}"
                )

        return incidents

    # ------------------------------------------------------------------
    # Incident handling
    # ------------------------------------------------------------------

    async def _handle_incident(self, incident: dict) -> None:
        """Process an incident: throttle wallet and emit report."""
        wallet = incident["wallet"]

        # 1. Set throttle flag
        throttled = self._load_throttled()
        throttled[wallet] = {
            "throttled_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(
                time.time() + THROTTLE_DURATION_SECONDS, tz=timezone.utc
            ).isoformat(),
            "reason": incident.get("reasons", []),
        }
        self._save_throttled(throttled)

        if self.config.storage_mode == "aleph":
            await self._write_aleph_throttle_flag(wallet, throttled[wallet])

        # 2. Save incident record
        incidents = self._load_incidents()
        incidents.append(incident)
        # Keep last 500 incidents
        if len(incidents) > 500:
            incidents = incidents[-500:]
        self._save_incidents(incidents)

        # 3. Emit incident report
        await self._emit_incident_report(incident)

        logger.info(
            f"Wallet throttled: {wallet[:10]}... for {THROTTLE_DURATION_SECONDS}s"
        )

    async def _emit_incident_report(self, incident: dict) -> None:
        """Post an incident report (local file or Aleph message)."""
        if self.config.storage_mode == "aleph":
            await self._post_aleph_message(
                {
                    "type": "guardian_incident",
                    "incident": incident,
                }
            )
        else:
            logger.warning(
                f"[Incident Report] {incident['type']} — "
                f"wallet={incident['wallet'][:10]}... "
                f"reasons={incident.get('reasons', [])}"
            )

    async def _write_aleph_throttle_flag(
        self, wallet: str, throttle_data: dict
    ) -> None:
        """Write throttle flag to Aleph Aggregates."""
        private_key = os.getenv("ALEPH_PRIVATE_KEY", "")
        if not private_key:
            logger.warning("[Aleph] ALEPH_PRIVATE_KEY not set — skipping throttle write")
            return

        try:
            from aleph.sdk.chains.ethereum import ETHAccount
            from aleph.sdk.client import AuthenticatedAlephHttpClient

            account = ETHAccount(private_key=private_key)
            channel = os.getenv("ALEPH_CHANNEL", "ALEPH_FILESHARE")

            async with AuthenticatedAlephHttpClient(
                account=account,
                api_server=os.getenv("ALEPH_API_SERVER", "https://api1.aleph.im"),
            ) as client:
                await client.create_aggregate(
                    key=f"throttle:{wallet}",
                    content=throttle_data,
                    channel=channel,
                )
            logger.info(f"[Aleph] Wrote throttle aggregate for {wallet[:10]}...")
        except ImportError:
            logger.warning("[Aleph] aleph-sdk-python not installed — skipping throttle write")
        except Exception as e:
            logger.error(f"[Aleph] Failed to write throttle flag: {e}")

    async def _post_aleph_message(self, payload: dict) -> None:
        """Post a message to Aleph network."""
        private_key = os.getenv("ALEPH_PRIVATE_KEY", "")
        if not private_key:
            logger.warning("[Aleph] ALEPH_PRIVATE_KEY not set — skipping POST message")
            return

        try:
            from aleph.sdk.chains.ethereum import ETHAccount
            from aleph.sdk.client import AuthenticatedAlephHttpClient

            account = ETHAccount(private_key=private_key)
            channel = os.getenv("ALEPH_CHANNEL", "ALEPH_FILESHARE")

            async with AuthenticatedAlephHttpClient(
                account=account,
                api_server=os.getenv("ALEPH_API_SERVER", "https://api1.aleph.im"),
            ) as client:
                await client.create_post(
                    post_content=payload,
                    post_type="aleph-fileshare:guardian",
                    channel=channel,
                )
            logger.info(f"[Aleph] Posted message: type={payload.get('type')}")
        except ImportError:
            logger.warning("[Aleph] aleph-sdk-python not installed — skipping POST")
        except Exception as e:
            logger.error(f"[Aleph] Failed to post message: {e}")

    # ------------------------------------------------------------------
    # Throttle management
    # ------------------------------------------------------------------

    def _expire_throttles(self) -> None:
        """Remove expired throttle entries."""
        throttled = self._load_throttled()
        now = time.time()
        expired = [
            wallet
            for wallet, data in throttled.items()
            if _parse_ts(data.get("expires_at", "")) < now
        ]
        for wallet in expired:
            del throttled[wallet]
            logger.info(f"Throttle expired for wallet {wallet[:10]}...")
        if expired:
            self._save_throttled(throttled)

    def is_throttled(self, wallet: str) -> bool:
        """Return True if the wallet is currently throttled."""
        throttled = self._load_throttled()
        if wallet not in throttled:
            return False
        expires_at = _parse_ts(throttled[wallet].get("expires_at", ""))
        if expires_at < time.time():
            return False
        return True

    # ------------------------------------------------------------------
    # Public helpers (used by backend health endpoint)
    # ------------------------------------------------------------------

    def get_health_report(self) -> dict:
        """Return the latest health report."""
        return self._load_health()

    def get_incidents(self, limit: int = 50) -> list[dict]:
        """Return recent incidents."""
        return self._load_incidents()[-limit:]

    def get_throttled_wallets(self) -> dict:
        """Return currently active throttle entries."""
        throttled = self._load_throttled()
        now = time.time()
        return {
            wallet: data
            for wallet, data in throttled.items()
            if _parse_ts(data.get("expires_at", "")) >= now
        }

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_throttled(self) -> dict:
        return _load_json(self._throttle_file, {})

    def _save_throttled(self, data: dict) -> None:
        _save_json(self._throttle_file, data)

    def _load_incidents(self) -> list:
        return _load_json(self._incidents_file, [])

    def _save_incidents(self, data: list) -> None:
        _save_json(self._incidents_file, data)

    def _load_health(self) -> dict:
        return _load_json(self._health_file, {})

    def _save_health(self, data: dict) -> None:
        _save_json(self._health_file, data)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _parse_ts(ts_str: str) -> float:
    """Parse ISO timestamp string to Unix float; returns 0 on error."""
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return 0.0
