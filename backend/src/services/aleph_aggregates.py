"""Metadata storage via Aleph Aggregates, with local JSON fallback."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

STORAGE_MODE = os.getenv("STORAGE_MODE", "local")
LOCAL_META_FILE = Path(
    os.getenv("LOCAL_META_FILE", "/tmp/aleph-fileshare-metadata.json")
)


async def store_metadata(key: str, content: dict[str, Any]) -> None:
    """Store file metadata keyed by hash.

    Args:
        key: File hash used as the aggregate key.
        content: Metadata dictionary.
    """
    if STORAGE_MODE == "aleph":
        await _store_aleph(key, content)
    else:
        await _store_local(key, content)


async def get_metadata(key: str) -> Optional[dict[str, Any]]:
    """Retrieve file metadata by hash.

    Args:
        key: File hash.

    Returns:
        Metadata dict or None if not found.
    """
    if STORAGE_MODE == "aleph":
        return await _get_aleph(key)
    else:
        return await _get_local(key)


async def delete_metadata(key: str) -> bool:
    """Delete file metadata.

    Args:
        key: File hash.

    Returns:
        True if deleted.
    """
    if STORAGE_MODE == "aleph":
        return await _delete_aleph(key)
    else:
        return await _delete_local(key)


async def list_metadata(
    uploader: str,
    limit: int = 20,
    offset: int = 0,
    sort: str = "uploaded_at_desc",
) -> tuple[list[dict[str, Any]], int]:
    """List metadata for a given uploader.

    Args:
        uploader: Wallet address of the uploader.
        limit: Max results.
        offset: Pagination offset.
        sort: Sort order.

    Returns:
        Tuple of (list of metadata dicts, total count).
    """
    if STORAGE_MODE == "aleph":
        return await _list_aleph(uploader, limit, offset, sort)
    else:
        return await _list_local(uploader, limit, offset, sort)


# --- Aleph Mode ---


async def _store_aleph(key: str, content: dict[str, Any]) -> None:
    """Store metadata as Aleph Aggregate."""
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
            result = await client.create_aggregate(
                key=key,
                content=content,
                channel=channel,
            )
            content["aleph_item_hash"] = result.item_hash
    except Exception as e:
        logger.error(f"Aleph aggregate store failed: {e}")
        raise


async def _get_aleph(key: str) -> Optional[dict[str, Any]]:
    """Get metadata from Aleph Aggregate."""
    try:
        from aleph.sdk.client import AlephHttpClient

        api_server = os.getenv("ALEPH_API_SERVER", "https://api1.aleph.im")
        private_key = os.getenv("ALEPH_PRIVATE_KEY", "")

        from aleph.sdk.chains.ethereum import ETHAccount

        account = ETHAccount(private_key=private_key)

        async with AlephHttpClient(api_server=api_server) as client:
            result = await client.fetch_aggregate(
                address=account.get_address(),
                key=key,
            )
            return result if result else None
    except Exception:
        return None


async def _delete_aleph(key: str) -> bool:
    """Delete via Aleph FORGET."""
    try:
        from aleph.sdk.client import AuthenticatedAlephHttpClient
        from aleph.sdk.chains.ethereum import ETHAccount

        private_key = os.getenv("ALEPH_PRIVATE_KEY", "")
        channel = os.getenv("ALEPH_CHANNEL", "ALEPH_FILESHARE")
        api_server = os.getenv("ALEPH_API_SERVER", "https://api1.aleph.im")

        # Fetch current metadata to get the item hash
        metadata = await _get_aleph(key)
        if not metadata:
            logger.warning(f"Cannot delete — metadata not found for key: {key}")
            return False

        item_hash = metadata.get("aleph_item_hash")
        if not item_hash:
            logger.warning(
                f"Cannot delete — no aleph_item_hash in metadata for key: {key}"
            )
            return False

        account = ETHAccount(private_key=private_key)
        async with AuthenticatedAlephHttpClient(
            account=account, api_server=api_server
        ) as client:
            await client.forget(
                hashes=[item_hash],
                channel=channel,
            )
        return True
    except Exception as e:
        logger.error(f"Aleph aggregate delete failed: {e}")
        return False


async def _list_aleph(
    uploader: str, limit: int, offset: int, sort: str
) -> tuple[list[dict[str, Any]], int]:
    """List aggregates for an uploader via Aleph AGGREGATE messages."""
    try:
        from aleph.sdk.client import AlephHttpClient
        from aleph_message.models import MessageType

        api_server = os.getenv("ALEPH_API_SERVER", "https://api1.aleph.im")
        channel = os.getenv("ALEPH_CHANNEL", "ALEPH_FILESHARE")

        async with AlephHttpClient(api_server=api_server) as client:
            response = await client.get_messages(
                message_type=MessageType.aggregate,
                addresses=[uploader],
                channels=[channel],
            )

        items = []
        for msg in response.messages:
            content = msg.content.content
            if isinstance(content, dict):
                items.append(content)
            else:
                # Aggregate content is keyed — flatten values
                for val in content.values():
                    if isinstance(val, dict):
                        items.append(val)

        # Sort
        reverse = sort.endswith("_desc")
        sort_key = sort.replace("_desc", "").replace("_asc", "")
        if sort_key == "size":
            sort_key = "size_bytes"
        items.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)

        total = len(items)
        items = items[offset : offset + limit]

        return items, total
    except Exception as e:
        logger.error(f"Aleph aggregate listing failed: {e}")
        return [], 0


# --- Local Mode ---


def _load_local_db() -> dict[str, Any]:
    """Load the local JSON metadata store."""
    if LOCAL_META_FILE.exists():
        with open(LOCAL_META_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_local_db(db: dict[str, Any]) -> None:
    """Persist the local JSON metadata store."""
    LOCAL_META_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCAL_META_FILE, "w") as f:
        json.dump(db, f, indent=2)


async def _store_local(key: str, content: dict[str, Any]) -> None:
    """Store metadata in local JSON file."""
    db = _load_local_db()
    db[key] = content
    _save_local_db(db)
    logger.info(f"Local metadata stored: {key}")


async def _get_local(key: str) -> Optional[dict[str, Any]]:
    """Get metadata from local JSON file."""
    db = _load_local_db()
    return db.get(key)


async def _delete_local(key: str) -> bool:
    """Delete metadata from local JSON file."""
    db = _load_local_db()
    if key in db:
        del db[key]
        _save_local_db(db)
        logger.info(f"Local metadata deleted: {key}")
        return True
    return False


async def _list_local(
    uploader: str, limit: int, offset: int, sort: str
) -> tuple[list[dict[str, Any]], int]:
    """List metadata from local JSON file filtered by uploader."""
    db = _load_local_db()

    # Filter by uploader
    items = [
        v for v in db.values() if v.get("uploader", "").lower() == uploader.lower()
    ]

    # Sort
    reverse = sort.endswith("_desc")
    sort_key = sort.replace("_desc", "").replace("_asc", "")
    if sort_key == "size":
        sort_key = "size_bytes"
    items.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)

    total = len(items)
    items = items[offset : offset + limit]

    return items, total
