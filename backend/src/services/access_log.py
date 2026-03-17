"""Access logging for file operations."""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STORAGE_MODE = os.getenv("STORAGE_MODE", "local")
LOCAL_ACCESS_LOG = Path(
    os.getenv("LOCAL_ACCESS_LOG", "/tmp/aleph-fileshare-access.jsonl")
)


async def log_access(
    file_hash: str,
    action: str,
    actor: str,
    ip: str,
) -> None:
    """Log a file access event.

    Args:
        file_hash: Hash of the file being accessed.
        action: One of "upload", "download", "delete", "view".
        actor: Wallet address or "anonymous".
        ip: Client IP address.
    """
    entry = {
        "file_hash": file_hash,
        "action": action,
        "actor": actor,
        "ip": ip,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if STORAGE_MODE == "aleph":
        await _log_aleph(entry)
    else:
        await _log_local(entry)


async def get_access_log(file_hash: str, limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve access log entries for a file.

    Args:
        file_hash: Hash of the file.
        limit: Max entries to return (most recent first).

    Returns:
        List of log entry dicts.
    """
    if STORAGE_MODE == "aleph":
        return await _get_log_aleph(file_hash, limit)
    else:
        return await _get_log_local(file_hash, limit)


# --- Aleph Mode ---

async def _log_aleph(entry: dict[str, Any]) -> None:
    """Post access log entry as an Aleph POST message."""
    try:
        from aleph.sdk.client import AuthenticatedAlephHttpClient
        from aleph.sdk.chains.ethereum import ETHAccount

        private_key = os.getenv("ALEPH_PRIVATE_KEY", "")
        channel = os.getenv("ALEPH_CHANNEL", "ALEPH_FILESHARE")
        api_server = os.getenv("ALEPH_API_SERVER", "https://api1.aleph.im")

        account = ETHAccount(private_key=private_key)
        async with AuthenticatedAlephHttpClient(
            account=account, api_server=api_server
        ) as client:
            await client.create_post(
                post_content=entry,
                post_type="FILESHARE_ACCESS_LOG",
                channel=channel,
            )
    except Exception as e:
        logger.error(f"Aleph access log failed: {e}")


async def _get_log_aleph(file_hash: str, limit: int) -> list[dict[str, Any]]:
    """Retrieve access log entries from Aleph POST messages."""
    try:
        from aleph.sdk.client import AlephHttpClient
        from aleph_message.models import MessageType

        api_server = os.getenv("ALEPH_API_SERVER", "https://api1.aleph.im")
        channel = os.getenv("ALEPH_CHANNEL", "ALEPH_FILESHARE")

        async with AlephHttpClient(api_server=api_server) as client:
            response = await client.get_messages(
                message_type=MessageType.post,
                channels=[channel],
                content_types=["FILESHARE_ACCESS_LOG"],
            )

        entries = []
        for msg in response.messages:
            content = msg.content.content
            if isinstance(content, dict) and content.get("file_hash") == file_hash:
                entries.append(content)

        # Sort by timestamp descending
        entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return entries[:limit]
    except Exception as e:
        logger.error(f"Aleph access log retrieval failed: {e}")
        return []


# --- Local Mode ---

async def _log_local(entry: dict[str, Any]) -> None:
    """Append access log entry to local JSONL file."""
    LOCAL_ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCAL_ACCESS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.debug(f"Access log: {entry['action']} on {entry['file_hash']} by {entry['actor']}")


async def _get_log_local(file_hash: str, limit: int) -> list[dict[str, Any]]:
    """Read access log entries from local JSONL file."""
    if not LOCAL_ACCESS_LOG.exists():
        return []

    entries = []
    with open(LOCAL_ACCESS_LOG, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("file_hash") == file_hash:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue

    # Most recent first
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return entries[:limit]
