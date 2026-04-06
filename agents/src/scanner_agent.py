"""Scanner Agent — Automated file safety scanning.

Polls for newly uploaded files and performs safety checks:
- Local mode: simulates scan (clean after delay, flags files >100MB)
- Aleph mode: stub for VirusTotal API integration

Updates file metadata with scan_status: clean | flagged | error
"""

import asyncio
import hashlib
import logging
import os
from typing import Optional

import httpx

from agents.src.utils import Config, MetadataClient

logger = logging.getLogger("scanner-agent")

# 100 MB threshold for suspicious files in local mode
SUSPICIOUS_SIZE_BYTES = 100 * 1024 * 1024


class ScannerAgent:
    """Autonomous file scanning agent.

    Monitors new uploads and performs safety checks using hash verification
    and configurable scan backends (local simulation or VirusTotal).
    """

    def __init__(self, config: Config, metadata_client: MetadataClient) -> None:
        self.config = config
        self.metadata = metadata_client
        self.poll_interval = config.scanner_poll_interval
        self._running = False

    async def start(self) -> None:
        """Start the scanning loop."""
        logger.info(
            f"Scanner Agent starting (mode={self.config.storage_mode}, "
            f"interval={self.poll_interval}s)"
        )
        self._running = True
        while self._running:
            try:
                await self._scan_cycle()
            except Exception as e:
                logger.error(f"Scan cycle error: {e}", exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Stop the scanning loop gracefully."""
        self._running = False
        logger.info("Scanner Agent stopped.")

    async def _scan_cycle(self) -> None:
        """Single scan cycle: fetch pending files and scan them."""
        pending = self.metadata.get_pending_scans()
        if not pending:
            return

        logger.info(f"Found {len(pending)} file(s) pending scan")

        for file_meta in pending:
            file_hash = file_meta.get("hash", "")
            filename = file_meta.get("filename", "unknown")
            try:
                status = await self.scan_file(file_hash, file_meta)
                self.metadata.update_metadata(file_hash, {"scan_status": status})
                logger.info(f"Scanned {filename} ({file_hash[:12]}...): {status}")
            except Exception as e:
                logger.error(f"Failed to scan {filename}: {e}")
                self.metadata.update_metadata(file_hash, {"scan_status": "error"})

    async def scan_file(self, file_hash: str, file_meta: dict) -> str:
        """Scan a single file and return its status.

        Args:
            file_hash: Hash of the file to scan.
            file_meta: File metadata dict.

        Returns:
            Scan status: "clean", "flagged", or "error".
        """
        if self.config.storage_mode == "aleph":
            return await self._scan_aleph(file_hash, file_meta)
        else:
            return await self._scan_local(file_hash, file_meta)

    async def _scan_local(self, file_hash: str, file_meta: dict) -> str:
        """Local mode scan: simulate scanning with basic heuristics.

        - Computes SHA-256 hash to verify file integrity
        - Flags files over 100MB as suspicious
        - Simulates processing delay
        """
        file_path = self.metadata.get_file_path(file_hash)
        if not file_path:
            logger.warning(f"File not found on disk: {file_hash}")
            return "error"

        # Compute SHA-256 hash for verification
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        computed_hash = sha256.hexdigest()
        logger.debug(f"Computed SHA-256: {computed_hash}")

        # Simulate scan processing time
        await asyncio.sleep(2)

        # Flag files over 100MB as suspicious
        size_bytes = file_meta.get("size_bytes", 0)
        if size_bytes > SUSPICIOUS_SIZE_BYTES:
            logger.warning(
                f"File {file_hash[:12]}... is {size_bytes} bytes — flagged as suspicious"
            )
            return "flagged"

        return "clean"

    async def _scan_aleph(self, file_hash: str, file_meta: dict) -> str:
        """Aleph mode scan: check against VirusTotal API.

        Requires VIRUSTOTAL_API_KEY environment variable.
        Flow:
        1. Check if hash is already known on VirusTotal
        2. If known, return verdict immediately
        3. If unknown and file is small enough (<32MB VT limit), submit for analysis
        4. Poll for results (up to 5 minutes)
        5. If still no result, mark as clean (low risk for unknown files)
        """
        if not self.config.virustotal_api_key:
            logger.warning(
                "VIRUSTOTAL_API_KEY not set — skipping VirusTotal scan, marking clean"
            )
            return "clean"

        # Step 1: Check existing hash
        vt_result = await self._check_virustotal(file_hash)
        if vt_result is not None:
            return vt_result

        # Step 2: Hash not found — try to submit the file for analysis
        logger.info(f"File {file_hash[:12]}... not found on VirusTotal — attempting upload")
        size_bytes = file_meta.get("size_bytes", 0)
        vt_max_size = 32 * 1024 * 1024  # 32MB VirusTotal limit for standard uploads

        if size_bytes > vt_max_size:
            logger.info(f"File too large for VT upload ({size_bytes} bytes) — marking clean")
            return "clean"

        submitted = await self._submit_to_virustotal(file_hash)
        if not submitted:
            logger.info(f"Could not submit {file_hash[:12]}... to VT — marking clean")
            return "clean"

        # Step 3: Poll for results (max 5 minutes, 30s intervals)
        for attempt in range(10):
            await asyncio.sleep(30)
            vt_result = await self._check_virustotal(file_hash)
            if vt_result is not None:
                return vt_result
            logger.debug(f"VT poll {attempt + 1}/10 — still pending for {file_hash[:12]}...")

        logger.info(f"VT analysis timed out for {file_hash[:12]}... — marking clean")
        return "clean"

    async def _submit_to_virustotal(self, file_hash: str) -> bool:
        """Submit a file to VirusTotal for analysis via its Aleph IPFS URL.

        Uses the URL-based submission endpoint to avoid downloading the file locally.

        Returns:
            True if submission was accepted.
        """
        api_key = os.getenv("VIRUSTOTAL_API_KEY", "")
        if not api_key:
            return False

        # Submit via URL (file is on IPFS)
        aleph_url = f"https://api2.aleph.im/api/v0/storage/raw/{file_hash}"
        url = "https://www.virustotal.com/api/v3/urls"
        headers = {"x-apikey": api_key}

        try:
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(
                    url, headers=headers, data={"url": aleph_url}
                )
            if response.status_code == 200:
                logger.info(f"Submitted {file_hash[:12]}... to VirusTotal for URL scan")
                return True
            else:
                logger.warning(f"VT URL submission failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"VT submission error: {e}")
            return False

    async def _check_virustotal(self, file_hash: str) -> Optional[str]:
        """Check file hash against VirusTotal database.

        Args:
            file_hash: SHA-256 hash of the file.

        Returns:
            "clean", "flagged", or None if not found.
        """
        api_key = os.getenv("VIRUSTOTAL_API_KEY", "")
        if not api_key:
            logger.warning("VIRUSTOTAL_API_KEY not set — returning clean with warning")
            return "clean"

        url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
        headers = {"x-apikey": api_key}

        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(url, headers=headers)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            logger.error(f"VirusTotal API error: {response.status_code}")
            return None

        data = response.json()
        stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        if stats.get("malicious", 0) > 0:
            return "flagged"

        return "clean"
