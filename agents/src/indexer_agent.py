"""Indexer Agent — Automated file tagging and metadata enrichment.

Polls for clean, untagged files and enriches their metadata:
- Local mode: generates tags from filename and MIME type
- Aleph mode: stub for LibertAI API to generate smart tags + description

Updates file metadata with tags and description.
"""

import asyncio
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional

import httpx

from agents.src.utils import Config, MetadataClient

logger = logging.getLogger("indexer-agent")

# MIME type to tag mapping for local mode
MIME_TAG_MAP: dict[str, list[str]] = {
    "application/pdf": ["pdf", "document"],
    "application/msword": ["word", "document"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ["word", "document"],
    "application/vnd.ms-excel": ["excel", "spreadsheet"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ["excel", "spreadsheet"],
    "application/vnd.ms-powerpoint": ["powerpoint", "presentation"],
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ["powerpoint", "presentation"],
    "application/zip": ["archive", "compressed"],
    "application/x-tar": ["archive", "compressed"],
    "application/gzip": ["archive", "compressed"],
    "application/x-7z-compressed": ["archive", "compressed"],
    "application/x-rar-compressed": ["archive", "compressed"],
    "application/json": ["json", "data"],
    "application/xml": ["xml", "data"],
    "text/csv": ["csv", "data", "spreadsheet"],
    "text/plain": ["text", "document"],
    "text/html": ["html", "web"],
    "text/markdown": ["markdown", "document"],
}

# MIME prefix to tag mapping
MIME_PREFIX_TAGS: dict[str, list[str]] = {
    "image/": ["image"],
    "video/": ["video", "media"],
    "audio/": ["audio", "media"],
    "text/": ["text"],
    "font/": ["font"],
}

# Extension-based tags for common file types
EXTENSION_TAGS: dict[str, list[str]] = {
    ".py": ["python", "code"],
    ".js": ["javascript", "code"],
    ".ts": ["typescript", "code"],
    ".jsx": ["react", "code"],
    ".tsx": ["react", "typescript", "code"],
    ".rs": ["rust", "code"],
    ".go": ["go", "code"],
    ".java": ["java", "code"],
    ".cpp": ["c++", "code"],
    ".c": ["c", "code"],
    ".rb": ["ruby", "code"],
    ".php": ["php", "code"],
    ".sql": ["sql", "database"],
    ".sh": ["shell", "script"],
    ".yml": ["yaml", "config"],
    ".yaml": ["yaml", "config"],
    ".toml": ["toml", "config"],
    ".ini": ["ini", "config"],
    ".env": ["config", "environment"],
    ".svg": ["svg", "image", "vector"],
    ".md": ["markdown", "document"],
    ".log": ["log"],
}


class IndexerAgent:
    """Autonomous file indexing and tagging agent.

    Monitors clean, untagged files and enriches metadata with
    AI-generated tags and descriptions.
    """

    def __init__(self, config: Config, metadata_client: MetadataClient) -> None:
        self.config = config
        self.metadata = metadata_client
        self.poll_interval = config.indexer_poll_interval
        self._running = False

    async def start(self) -> None:
        """Start the indexing loop."""
        logger.info(
            f"Indexer Agent starting (mode={self.config.storage_mode}, "
            f"interval={self.poll_interval}s)"
        )
        self._running = True
        while self._running:
            try:
                await self._index_cycle()
            except Exception as e:
                logger.error(f"Index cycle error: {e}", exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Stop the indexing loop gracefully."""
        self._running = False
        logger.info("Indexer Agent stopped.")

    async def _index_cycle(self) -> None:
        """Single index cycle: fetch untagged clean files and enrich them."""
        untagged = self.metadata.get_untagged_clean_files()
        if not untagged:
            return

        logger.info(f"Found {len(untagged)} file(s) to index")

        for file_meta in untagged:
            file_hash = file_meta.get("hash", "")
            filename = file_meta.get("filename", "unknown")
            try:
                result = await self.index_file(file_hash, file_meta)
                self.metadata.update_metadata(file_hash, result)
                logger.info(
                    f"Indexed {filename} ({file_hash[:12]}...): "
                    f"tags={result.get('tags', [])}"
                )
            except Exception as e:
                logger.error(f"Failed to index {filename}: {e}")

    async def index_file(self, file_hash: str, file_meta: dict) -> dict:
        """Index a single file and return enriched metadata.

        Args:
            file_hash: Hash of the file.
            file_meta: Current file metadata.

        Returns:
            Dict with tags and description to merge into metadata.
        """
        if self.config.storage_mode == "aleph":
            return await self._index_aleph(file_hash, file_meta)
        else:
            return await self._index_local(file_hash, file_meta)

    async def _index_local(self, file_hash: str, file_meta: dict) -> dict:
        """Local mode indexing: generate tags from filename and MIME type."""
        filename = file_meta.get("filename", "unknown")
        mime_type = file_meta.get("mime_type", "application/octet-stream")

        tags = set()

        # Tags from exact MIME type match
        if mime_type in MIME_TAG_MAP:
            tags.update(MIME_TAG_MAP[mime_type])

        # Tags from MIME prefix
        for prefix, prefix_tags in MIME_PREFIX_TAGS.items():
            if mime_type.startswith(prefix):
                tags.update(prefix_tags)
                break

        # Tags from file extension
        ext = Path(filename).suffix.lower()
        if ext in EXTENSION_TAGS:
            tags.update(EXTENSION_TAGS[ext])

        # Add specific image format tags
        if mime_type.startswith("image/"):
            fmt = mime_type.split("/")[-1]
            if fmt in ("jpeg", "jpg", "png", "gif", "webp", "svg+xml", "bmp", "tiff"):
                tags.add(fmt.replace("+xml", ""))

        # Generate a basic description
        size_bytes = file_meta.get("size_bytes", 0)
        description = self._generate_local_description(filename, mime_type, size_bytes)

        # Simulate processing time
        await asyncio.sleep(1)

        return {
            "tags": sorted(tags) if tags else ["file"],
            "description": description,
        }

    def _generate_local_description(
        self, filename: str, mime_type: str, size_bytes: int
    ) -> str:
        """Generate a basic human-readable description."""
        # Friendly MIME category
        category = "file"
        if mime_type.startswith("image/"):
            category = "image"
        elif mime_type.startswith("video/"):
            category = "video"
        elif mime_type.startswith("audio/"):
            category = "audio"
        elif mime_type == "application/pdf":
            category = "PDF document"
        elif "spreadsheet" in mime_type or "excel" in mime_type:
            category = "spreadsheet"
        elif "presentation" in mime_type or "powerpoint" in mime_type:
            category = "presentation"
        elif "word" in mime_type or "document" in mime_type:
            category = "document"
        elif mime_type.startswith("text/"):
            category = "text file"
        elif "zip" in mime_type or "tar" in mime_type or "compressed" in mime_type:
            category = "archive"

        # Format size
        if size_bytes >= 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes} bytes"

        name = Path(filename).stem
        return f"{category.capitalize()} '{name}' ({size_str})"

    async def _index_aleph(self, file_hash: str, file_meta: dict) -> dict:
        """Aleph mode indexing: use LibertAI for smart tagging.

        Requires LIBERTAI_API_URL and LLM_MODEL environment variables.
        Falls back to local indexing if LibertAI is unavailable.
        """
        api_url = self.config.libertai_api_url
        model = self.config.llm_model

        if not api_url:
            logger.info("LIBERTAI_API_URL not set — falling back to local indexing")
            return await self._index_local(file_hash, file_meta)

        filename = file_meta.get("filename", "unknown")
        mime_type = file_meta.get("mime_type", "application/octet-stream")
        size_bytes = file_meta.get("size_bytes", 0)

        prompt = (
            f"Analyze this file and respond with ONLY valid JSON (no markdown, no explanation).\n"
            f"Filename: {filename}\n"
            f"MIME type: {mime_type}\n"
            f"Size: {size_bytes} bytes\n\n"
            f"Generate 3-7 descriptive tags and a one-sentence description.\n"
            f'Format: {{"tags": ["tag1", "tag2", ...], "description": "One sentence description."}}'
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{api_url}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 200,
                    },
                )

            if response.status_code != 200:
                logger.warning(f"LibertAI API error: {response.status_code} — falling back to local")
                return await self._index_local(file_hash, file_meta)

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Parse JSON response — handle potential markdown wrapping
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(content)
            tags = result.get("tags", [])
            description = result.get("description", "")

            # Validate
            if not isinstance(tags, list) or not tags:
                raise ValueError("Invalid tags from LLM")

            # Sanitize tags: lowercase, alphanumeric + hyphens only, max 20 chars
            clean_tags = []
            for tag in tags[:10]:
                clean = "".join(c for c in str(tag).lower() if c.isalnum() or c == "-")[:20]
                if clean:
                    clean_tags.append(clean)

            if not clean_tags:
                raise ValueError("No valid tags after sanitization")

            logger.info(f"LibertAI tagged {filename}: {clean_tags}")
            return {
                "tags": clean_tags,
                "description": str(description)[:500],
            }

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LibertAI response: {e} — falling back to local")
            return await self._index_local(file_hash, file_meta)
        except Exception as e:
            logger.error(f"LibertAI request failed: {e} — falling back to local")
            return await self._index_local(file_hash, file_meta)
