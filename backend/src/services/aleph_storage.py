"""IPFS file storage via Aleph Cloud SDK, with local fallback."""

import hashlib
import os
import logging
from pathlib import Path
from typing import Optional

import aiofiles
import httpx

logger = logging.getLogger(__name__)

STORAGE_MODE = os.getenv("STORAGE_MODE", "local")
LOCAL_STORAGE_DIR = Path(os.getenv("LOCAL_STORAGE_DIR", "/tmp/aleph-fileshare-storage"))
IPFS_GATEWAY = "https://ipfs.aleph.cloud/ipfs"


async def upload_file(file_content: bytes, filename: str) -> str:
    """Upload file and return its hash.

    Args:
        file_content: Raw bytes of the file.
        filename: Original filename.

    Returns:
        Hash string (IPFS hash for aleph mode, sha256 for local mode).
    """
    if STORAGE_MODE == "aleph":
        return await _upload_aleph(file_content, filename)
    else:
        return await _upload_local(file_content, filename)


async def download_file(file_hash: str) -> Optional[bytes]:
    """Download file by hash.

    Args:
        file_hash: IPFS hash or local hash.

    Returns:
        File bytes or None if not found.
    """
    if STORAGE_MODE == "aleph":
        return await _download_aleph(file_hash)
    else:
        return await _download_local(file_hash)


async def delete_file(file_hash: str) -> bool:
    """Delete/forget a file.

    Args:
        file_hash: Hash of the file to delete.

    Returns:
        True if deleted successfully.
    """
    if STORAGE_MODE == "aleph":
        return await _delete_aleph(file_hash)
    else:
        return await _delete_local(file_hash)


# --- Aleph Mode ---

async def _upload_aleph(file_content: bytes, filename: str) -> str:
    """Upload to IPFS via aleph-sdk-python."""
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
            result = await client.create_store(
                file_content=file_content,
                storage_engine="ipfs",
                channel=channel,
                guess_mime_type=True,
                sync=True,
            )
            return result.item_hash
    except Exception as e:
        logger.error(f"Aleph upload failed: {e}")
        raise


async def _download_aleph(file_hash: str) -> Optional[bytes]:
    """Download from IPFS via Aleph gateway."""
    url = f"{IPFS_GATEWAY}/{file_hash}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            return resp.content
    return None


async def _delete_aleph(file_hash: str) -> bool:
    """Send FORGET message via aleph-sdk-python."""
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
            await client.forget(
                hashes=[file_hash],
                channel=channel,
            )
            return True
    except Exception as e:
        logger.error(f"Aleph delete failed: {e}")
        return False


# --- Local Mode ---

async def _upload_local(file_content: bytes, filename: str) -> str:
    """Store file locally and return sha256 hash."""
    LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    file_hash = hashlib.sha256(file_content).hexdigest()
    file_path = LOCAL_STORAGE_DIR / file_hash

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_content)

    logger.info(f"Local upload: {filename} -> {file_hash}")
    return file_hash


async def _download_local(file_hash: str) -> Optional[bytes]:
    """Read file from local storage."""
    file_path = LOCAL_STORAGE_DIR / file_hash
    if not file_path.exists():
        return None

    async with aiofiles.open(file_path, "rb") as f:
        return await f.read()


async def _delete_local(file_hash: str) -> bool:
    """Delete file from local storage."""
    file_path = LOCAL_STORAGE_DIR / file_hash
    if file_path.exists():
        file_path.unlink()
        logger.info(f"Local delete: {file_hash}")
        return True
    return False
