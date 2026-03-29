"""Shared utilities for AI agents — config, logging, metadata client."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional


def setup_logging(name: str = "agents") -> logging.Logger:
    """Configure structured logging for agents.

    Args:
        name: Logger name.

    Returns:
        Configured logger instance.
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    return logging.getLogger(name)


class Config:
    """Agent configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.storage_mode: str = os.getenv("STORAGE_MODE", "local")
        self.local_storage_dir: Path = Path(
            os.getenv("LOCAL_STORAGE_DIR", "/tmp/aleph-fileshare-storage")
        )
        self.local_meta_file: Path = Path(
            os.getenv("LOCAL_META_FILE", "/tmp/aleph-fileshare-metadata.json")
        )
        self.scanner_poll_interval: int = int(
            os.getenv("SCANNER_POLL_INTERVAL_SECONDS", "10")
        )
        self.indexer_poll_interval: int = int(
            os.getenv("INDEXER_POLL_INTERVAL_SECONDS", "15")
        )
        self.recommender_poll_interval: int = int(
            os.getenv("RECOMMENDER_POLL_INTERVAL_SECONDS", "3600")
        )
        # How many cycles between weekly digest sends (1 cycle = poll_interval)
        self.recommender_digest_interval: int = int(
            os.getenv("RECOMMENDER_DIGEST_INTERVAL_CYCLES", "168")
        )
        self.guardian_poll_interval: int = int(
            os.getenv("GUARDIAN_POLL_INTERVAL_SECONDS", "60")
        )
        # Aleph mode settings
        self.virustotal_api_key: str = os.getenv("VIRUSTOTAL_API_KEY", "")
        self.libertai_api_url: str = os.getenv(
            "LIBERTAI_API_URL", "https://api.libertai.io"
        )
        self.llm_model: str = os.getenv("LLM_MODEL", "mistral-7b-instruct")


class MetadataClient:
    """Client for reading and updating file metadata.

    Works with the same local JSON format used by the backend.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.logger = logging.getLogger("metadata-client")

    def _load_db(self) -> dict[str, Any]:
        """Load the local JSON metadata store."""
        if self.config.local_meta_file.exists():
            with open(self.config.local_meta_file, "r") as f:
                return json.load(f)
        return {}

    def _save_db(self, db: dict[str, Any]) -> None:
        """Persist the local JSON metadata store."""
        self.config.local_meta_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.local_meta_file, "w") as f:
            json.dump(db, f, indent=2)

    def get_pending_scans(self) -> list[dict[str, Any]]:
        """Return all files with scan_status='pending'."""
        db = self._load_db()
        return [
            v for v in db.values()
            if v.get("scan_status") == "pending"
        ]

    def get_untagged_clean_files(self) -> list[dict[str, Any]]:
        """Return files with scan_status='clean' and empty tags."""
        db = self._load_db()
        return [
            v for v in db.values()
            if v.get("scan_status") == "clean"
            and (not v.get("tags") or v.get("tags") == [])
        ]

    def update_metadata(self, file_hash: str, updates: dict[str, Any]) -> bool:
        """Update specific fields in a file's metadata.

        Args:
            file_hash: The file hash key.
            updates: Dictionary of fields to update.

        Returns:
            True if the file was found and updated.
        """
        db = self._load_db()
        if file_hash not in db:
            self.logger.warning(f"File not found in metadata: {file_hash}")
            return False
        db[file_hash].update(updates)
        self._save_db(db)
        self.logger.debug(f"Updated metadata for {file_hash}: {updates}")
        return True

    def get_metadata(self, file_hash: str) -> Optional[dict[str, Any]]:
        """Get metadata for a specific file."""
        db = self._load_db()
        return db.get(file_hash)

    def get_file_path(self, file_hash: str) -> Optional[Path]:
        """Get the local storage path for a file."""
        path = self.config.local_storage_dir / file_hash
        return path if path.exists() else None
