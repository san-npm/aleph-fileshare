"""Recommender Agent — Personalized file recommendation engine.

Tracks anonymized user interaction patterns and builds a collaborative
filtering model to surface similar files and personalized recommendations.

- Local mode: stores interaction graph in a JSON sidecar file
- Aleph mode: persists interaction patterns as Aleph Aggregates and
              sends weekly digest notifications as Aleph POST messages

Exposes recommendations consumed by the backend /api/recommendations
endpoint and the frontend "Similar files" sidebar.
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

from agents.src.utils import Config, MetadataClient

logger = logging.getLogger("recommender-agent")

# Interaction types and their weights
INTERACTION_WEIGHTS: dict[str, float] = {
    "download": 3.0,
    "view": 1.0,
    "upload": 2.0,
}

# How many days of history to consider
HISTORY_DAYS = 30

# Minimum co-interaction count to surface a recommendation
MIN_CO_INTERACTIONS = 2

# Max similar files to surface per file
MAX_SIMILAR = 5


class RecommenderAgent:
    """Autonomous recommendation engine agent.

    Builds an item-item collaborative filtering model from anonymized
    interaction patterns and surfaces similar-file recommendations.
    """

    def __init__(self, config: Config, metadata_client: MetadataClient) -> None:
        self.config = config
        self.metadata = metadata_client
        self.poll_interval = config.recommender_poll_interval
        self._running = False

        # Local path for storing interaction data
        self._interactions_file = Path(
            os.getenv(
                "RECOMMENDER_INTERACTIONS_FILE",
                "/tmp/aleph-fileshare-interactions.json",
            )
        )
        # Local path for recommendations output
        self._recommendations_file = Path(
            os.getenv(
                "RECOMMENDER_OUTPUT_FILE",
                "/tmp/aleph-fileshare-recommendations.json",
            )
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the recommendation loop."""
        logger.info(
            f"Recommender Agent starting (mode={self.config.storage_mode}, "
            f"interval={self.poll_interval}s)"
        )
        self._running = True
        cycle = 0
        while self._running:
            try:
                await self._recommend_cycle()
                # Send weekly digest every ~168 cycles (if poll=3600s that's weekly)
                cycle += 1
                if cycle % max(1, self.config.recommender_digest_interval) == 0:
                    await self._send_weekly_digest()
            except Exception as exc:
                logger.error(f"Recommender cycle error: {exc}", exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Stop the recommendation loop gracefully."""
        self._running = False
        logger.info("Recommender Agent stopped.")

    # ------------------------------------------------------------------
    # Main cycle
    # ------------------------------------------------------------------

    async def _recommend_cycle(self) -> None:
        """Single cycle: ingest new interactions and rebuild recommendations."""
        # 1. Collect fresh interactions from access logs
        await self._ingest_interactions()

        # 2. Build item-item similarity matrix
        recommendations = self._build_item_item_recommendations()

        # 3. Persist recommendations
        self._save_recommendations(recommendations)

        logger.debug(
            f"Recommendations built for {len(recommendations)} files"
        )

    # ------------------------------------------------------------------
    # Interaction ingestion
    # ------------------------------------------------------------------

    async def _ingest_interactions(self) -> None:
        """Read access logs and update the anonymized interaction store."""
        interactions = self._load_interactions()
        db = self.metadata._load_db()
        cutoff = time.time() - (HISTORY_DAYS * 86400)

        for file_hash, file_meta in db.items():
            access_log: list[dict] = file_meta.get("_access_log", [])
            for entry in access_log:
                ts = entry.get("timestamp", 0)
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(
                            ts.replace("Z", "+00:00")
                        ).timestamp()
                    except ValueError:
                        continue

                if ts < cutoff:
                    continue

                action = entry.get("action", "")
                # Anonymise: hash the actor address
                actor_raw = entry.get("actor", "anonymous")
                actor_anon = _anonymise(actor_raw)

                weight = INTERACTION_WEIGHTS.get(action, 0.5)

                # interactions[actor][file_hash] = cumulative weight
                if actor_anon not in interactions:
                    interactions[actor_anon] = {}
                prev = interactions[actor_anon].get(file_hash, 0.0)
                interactions[actor_anon][file_hash] = prev + weight

        self._save_interactions(interactions)

    # ------------------------------------------------------------------
    # Collaborative filtering
    # ------------------------------------------------------------------

    def _build_item_item_recommendations(self) -> dict[str, list[dict]]:
        """Item-item collaborative filtering.

        For each pair of files (A, B), compute a similarity score equal to
        the number of distinct users who interacted with both, weighted by
        their interaction intensities.

        Returns:
            Dict mapping file_hash → list of {"hash": str, "score": float}
        """
        interactions = self._load_interactions()

        # Build item → {actor: weight} map
        item_actors: dict[str, dict[str, float]] = defaultdict(dict)
        for actor, items in interactions.items():
            for item_hash, weight in items.items():
                item_actors[item_hash][actor] = weight

        # Compute pairwise similarity
        co_scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for actor, items in interactions.items():
            item_list = list(items.items())
            for i, (hash_a, weight_a) in enumerate(item_list):
                for hash_b, weight_b in item_list[i + 1 :]:
                    if hash_a == hash_b:
                        continue
                    sim = (weight_a * weight_b) ** 0.5  # geometric mean
                    co_scores[hash_a][hash_b] += sim
                    co_scores[hash_b][hash_a] += sim

        # Build recommendations: top-K by score, minimum threshold
        recommendations: dict[str, list[dict]] = {}
        db = self.metadata._load_db()

        for file_hash, peers in co_scores.items():
            # Only recommend files that actually exist in metadata
            scored = [
                {"hash": peer, "score": round(score, 3)}
                for peer, score in peers.items()
                if score >= MIN_CO_INTERACTIONS and peer in db
            ]
            scored.sort(key=lambda x: x["score"], reverse=True)
            recommendations[file_hash] = scored[:MAX_SIMILAR]

        return recommendations

    # ------------------------------------------------------------------
    # Weekly digest
    # ------------------------------------------------------------------

    async def _send_weekly_digest(self) -> None:
        """Send a weekly digest of top-downloaded files.

        Local mode: write digest to a JSON file.
        Aleph mode: post as an Aleph message.
        """
        db = self.metadata._load_db()
        now = time.time()
        week_start = now - (7 * 86400)

        # Tally downloads per file over the past 7 days
        download_counts: dict[str, int] = defaultdict(int)
        for file_hash, meta in db.items():
            for entry in meta.get("_access_log", []):
                if entry.get("action") != "download":
                    continue
                ts = entry.get("timestamp", 0)
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(
                            ts.replace("Z", "+00:00")
                        ).timestamp()
                    except ValueError:
                        continue
                if ts >= week_start:
                    download_counts[file_hash] += 1

        top_files = sorted(
            download_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        digest = {
            "type": "weekly_digest",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_start": datetime.fromtimestamp(week_start, tz=timezone.utc).isoformat(),
            "period_end": datetime.now(timezone.utc).isoformat(),
            "top_files": [
                {
                    "hash": fh,
                    "downloads": cnt,
                    "filename": db.get(fh, {}).get("filename", "unknown"),
                }
                for fh, cnt in top_files
            ],
        }

        if self.config.storage_mode == "aleph":
            await self._post_aleph_message(digest)
        else:
            digest_path = Path(
                os.getenv(
                    "RECOMMENDER_DIGEST_FILE",
                    "/tmp/aleph-fileshare-weekly-digest.json",
                )
            )
            digest_path.write_text(json.dumps(digest, indent=2))
            logger.info(
                f"Weekly digest written to {digest_path} — "
                f"top file: {top_files[0] if top_files else 'none'}"
            )

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
                    post_type="aleph-fileshare:recommender",
                    channel=channel,
                )
            logger.info(f"[Aleph] Posted recommender message: type={payload.get('type')}")
        except ImportError:
            logger.warning("[Aleph] aleph-sdk-python not installed — skipping POST")
        except Exception as e:
            logger.error(f"[Aleph] Failed to post message: {e}")

    # ------------------------------------------------------------------
    # Public helpers (used by backend endpoint)
    # ------------------------------------------------------------------

    def get_similar_files(self, file_hash: str) -> list[dict]:
        """Return similar file metadata for a given hash.

        Enriches each recommendation entry with filename and mime_type
        from the metadata store.
        """
        recommendations = self._load_recommendations()
        peers = recommendations.get(file_hash, [])
        db = self.metadata._load_db()

        result = []
        for peer in peers:
            peer_hash = peer["hash"]
            meta = db.get(peer_hash, {})
            if not meta:
                continue
            # Only surface public, clean files
            if not meta.get("public", True):
                continue
            if meta.get("scan_status") == "flagged":
                continue
            result.append(
                {
                    "hash": peer_hash,
                    "filename": meta.get("filename", "unknown"),
                    "mime_type": meta.get("mime_type", "application/octet-stream"),
                    "size_bytes": meta.get("size_bytes", 0),
                    "uploaded_at": meta.get("uploaded_at", ""),
                    "tags": meta.get("tags", []),
                    "score": peer["score"],
                }
            )

        return result[:MAX_SIMILAR]

    def get_user_recommendations(
        self, wallet_address: str, limit: int = 10
    ) -> list[dict]:
        """Return personalised recommendations for a wallet address.

        Uses the interaction history to find files the user hasn't seen
        but that are popular with users who share their taste.
        """
        interactions = self._load_interactions()
        actor_anon = _anonymise(wallet_address)
        user_items = set(interactions.get(actor_anon, {}).keys())

        if not user_items:
            return self._get_globally_popular(limit)

        recommendations = self._load_recommendations()
        db = self.metadata._load_db()

        # Score candidate files not yet seen by this user
        candidate_scores: dict[str, float] = defaultdict(float)
        for seen_hash in user_items:
            for peer in recommendations.get(seen_hash, []):
                peer_hash = peer["hash"]
                if peer_hash not in user_items:
                    candidate_scores[peer_hash] += peer["score"]

        sorted_candidates = sorted(
            candidate_scores.items(), key=lambda x: x[1], reverse=True
        )

        result = []
        for candidate_hash, score in sorted_candidates[:limit]:
            meta = db.get(candidate_hash, {})
            if not meta or not meta.get("public", True):
                continue
            if meta.get("scan_status") == "flagged":
                continue
            result.append(
                {
                    "hash": candidate_hash,
                    "filename": meta.get("filename", "unknown"),
                    "mime_type": meta.get("mime_type", "application/octet-stream"),
                    "size_bytes": meta.get("size_bytes", 0),
                    "uploaded_at": meta.get("uploaded_at", ""),
                    "tags": meta.get("tags", []),
                    "score": round(score, 3),
                    "reason": "collaborative_filtering",
                }
            )

        if not result:
            return self._get_globally_popular(limit)
        return result

    def _get_globally_popular(self, limit: int) -> list[dict]:
        """Fallback: return most-interacted public files globally."""
        interactions = self._load_interactions()
        db = self.metadata._load_db()

        # Tally total interaction weight per file
        file_scores: dict[str, float] = defaultdict(float)
        for actor_items in interactions.values():
            for file_hash, weight in actor_items.items():
                file_scores[file_hash] += weight

        sorted_files = sorted(
            file_scores.items(), key=lambda x: x[1], reverse=True
        )

        result = []
        for file_hash, score in sorted_files[:limit]:
            meta = db.get(file_hash, {})
            if not meta or not meta.get("public", True):
                continue
            if meta.get("scan_status") == "flagged":
                continue
            result.append(
                {
                    "hash": file_hash,
                    "filename": meta.get("filename", "unknown"),
                    "mime_type": meta.get("mime_type", "application/octet-stream"),
                    "size_bytes": meta.get("size_bytes", 0),
                    "uploaded_at": meta.get("uploaded_at", ""),
                    "tags": meta.get("tags", []),
                    "score": round(score, 3),
                    "reason": "globally_popular",
                }
            )

        return result

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_interactions(self) -> dict[str, dict[str, float]]:
        if self._interactions_file.exists():
            try:
                return json.loads(self._interactions_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_interactions(self, interactions: dict) -> None:
        self._interactions_file.parent.mkdir(parents=True, exist_ok=True)
        self._interactions_file.write_text(json.dumps(interactions, indent=2))

    def _load_recommendations(self) -> dict[str, list[dict]]:
        if self._recommendations_file.exists():
            try:
                return json.loads(self._recommendations_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_recommendations(self, recommendations: dict) -> None:
        self._recommendations_file.parent.mkdir(parents=True, exist_ok=True)
        self._recommendations_file.write_text(
            json.dumps(recommendations, indent=2)
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _anonymise(address: str) -> str:
    """Produce a stable but non-reversible token from a wallet address."""
    import hashlib

    salt = os.getenv("RECOMMENDER_ANON_SALT", "aleph-fileshare-anon")
    return hashlib.sha256(f"{salt}:{address}".encode()).hexdigest()[:16]
