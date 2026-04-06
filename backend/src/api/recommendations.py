"""Recommendations API — file recommendation endpoints.

Provides:
  GET /api/recommendations/similar/{hash}   — "Similar files" for a given file
  GET /api/recommendations/for-you          — Personalised recommendations (auth required)

Reads pre-computed recommendations produced by the Recommender Agent.
Falls back gracefully when no recommendation data is available yet.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from src.services.aleph_aggregates import get_metadata
from src.services.auth_service import verify_signature

logger = logging.getLogger("recommendations-api")

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])

# Paths written by the Recommender Agent
_RECOMMENDATIONS_FILE = Path(
    os.getenv(
        "RECOMMENDER_OUTPUT_FILE",
        "/tmp/aleph-fileshare-recommendations.json",
    )
)
_INTERACTIONS_FILE = Path(
    os.getenv(
        "RECOMMENDER_INTERACTIONS_FILE",
        "/tmp/aleph-fileshare-interactions.json",
    )
)

# Max items returned
MAX_SIMILAR = int(os.getenv("RECOMMENDER_MAX_SIMILAR", "5"))
MAX_FOR_YOU = int(os.getenv("RECOMMENDER_MAX_FOR_YOU", "10"))


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SimilarFileItem(BaseModel):
    hash: str
    filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: str
    tags: list[str]
    score: float


class SimilarFilesResponse(BaseModel):
    file_hash: str
    similar: list[SimilarFileItem]
    total: int


class RecommendationItem(BaseModel):
    hash: str
    filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: str
    tags: list[str]
    score: float
    reason: str


class PersonalisedRecommendationsResponse(BaseModel):
    wallet_address: str
    recommendations: list[RecommendationItem]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_recommendations() -> dict:
    """Load pre-computed recommendations from agent output file."""
    if _RECOMMENDATIONS_FILE.exists():
        try:
            return json.loads(_RECOMMENDATIONS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to load recommendations file")
    return {}


def _load_interactions() -> dict:
    """Load interaction data from agent output file."""
    if _INTERACTIONS_FILE.exists():
        try:
            return json.loads(_INTERACTIONS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _anonymise(address: str) -> str:
    """Stable anonymisation matching the Recommender Agent."""
    import hashlib

    salt = os.getenv("RECOMMENDER_ANON_SALT", "aleph-fileshare-anon")
    return hashlib.sha256(f"{salt}:{address}".encode()).hexdigest()[:16]


async def _enrich_peer(peer: dict) -> Optional[dict]:
    """Fetch live metadata for a peer recommendation entry."""
    peer_hash = peer.get("hash", "")
    meta = await get_metadata(peer_hash)
    if not meta:
        return None
    if not meta.get("public", True):
        return None
    if meta.get("scan_status") == "flagged":
        return None
    return {
        "hash": peer_hash,
        "filename": meta.get("filename", "unknown"),
        "mime_type": meta.get("mime_type", "application/octet-stream"),
        "size_bytes": meta.get("size_bytes", 0),
        "uploaded_at": meta.get("uploaded_at", ""),
        "tags": meta.get("tags", []),
        "score": peer.get("score", 0.0),
    }


async def _fallback_popular(limit: int) -> list[dict]:
    """Return globally popular public files as fallback recommendations.

    Reads directly from the local metadata store since list_metadata
    requires an uploader filter.
    """
    import json
    from pathlib import Path

    meta_file = Path(os.getenv("LOCAL_META_FILE", "/tmp/aleph-fileshare-metadata.json"))
    if not meta_file.exists():
        return []

    try:
        db: dict = json.loads(meta_file.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    items = [
        v
        for v in db.values()
        if v.get("public", True) and v.get("scan_status") != "flagged"
    ]
    # Sort by most recently uploaded
    items.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)

    result = []
    for item in items[:limit]:
        result.append(
            {
                "hash": item.get("hash", ""),
                "filename": item.get("filename", "unknown"),
                "mime_type": item.get("mime_type", "application/octet-stream"),
                "size_bytes": item.get("size_bytes", 0),
                "uploaded_at": item.get("uploaded_at", ""),
                "tags": item.get("tags", []),
                "score": 0.0,
                "reason": "recently_uploaded",
            }
        )
    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/similar/{file_hash}", response_model=SimilarFilesResponse)
async def get_similar_files(file_hash: str) -> SimilarFilesResponse:
    """Return files similar to the given hash.

    Uses pre-computed item-item collaborative filtering scores produced
    by the Recommender Agent.  Falls back to an empty list when no data
    is available yet.
    """
    # Verify the file exists and is public
    meta = await get_metadata(file_hash)
    if not meta:
        raise HTTPException(status_code=404, detail="File not found.")

    recommendations = _load_recommendations()
    raw_peers = recommendations.get(file_hash, [])

    similar: list[SimilarFileItem] = []
    for peer in raw_peers[:MAX_SIMILAR]:
        enriched = await _enrich_peer(peer)
        if enriched:
            similar.append(SimilarFileItem(**enriched))

    return SimilarFilesResponse(
        file_hash=file_hash,
        similar=similar,
        total=len(similar),
    )


@router.get("/for-you", response_model=PersonalisedRecommendationsResponse)
async def get_personalised_recommendations(
    limit: int = Query(10, ge=1, le=50),
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    x_wallet_signature: Optional[str] = Header(None, alias="X-Wallet-Signature"),
    x_wallet_nonce: Optional[str] = Header(None, alias="X-Wallet-Nonce"),
) -> PersonalisedRecommendationsResponse:
    """Return personalised file recommendations for the authenticated user.

    Requires wallet authentication.  Uses collaborative filtering based on
    the user's download and view history.  Falls back to globally popular
    files for new users with no history.
    """
    if not x_wallet_address or not x_wallet_signature or not x_wallet_nonce:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if not verify_signature(x_wallet_address, x_wallet_signature, x_wallet_nonce):
        raise HTTPException(status_code=401, detail="Invalid signature.")

    interactions = _load_interactions()
    actor_anon = _anonymise(x_wallet_address)
    user_items = set(interactions.get(actor_anon, {}).keys())

    recommendations = _load_recommendations()

    # Score candidates not already seen by the user
    from collections import defaultdict

    candidate_scores: dict[str, float] = defaultdict(float)
    for seen_hash in user_items:
        for peer in recommendations.get(seen_hash, []):
            peer_hash = peer["hash"]
            if peer_hash not in user_items:
                candidate_scores[peer_hash] += peer["score"]

    sorted_candidates = sorted(
        candidate_scores.items(), key=lambda x: x[1], reverse=True
    )[:limit]

    recs: list[RecommendationItem] = []
    for candidate_hash, score in sorted_candidates:
        meta = await get_metadata(candidate_hash)
        if not meta or not meta.get("public", True):
            continue
        if meta.get("scan_status") == "flagged":
            continue
        recs.append(
            RecommendationItem(
                hash=candidate_hash,
                filename=meta.get("filename", "unknown"),
                mime_type=meta.get("mime_type", "application/octet-stream"),
                size_bytes=meta.get("size_bytes", 0),
                uploaded_at=meta.get("uploaded_at", ""),
                tags=meta.get("tags", []),
                score=round(score, 3),
                reason="collaborative_filtering",
            )
        )

    # Fallback to popular files for users with no history
    if not recs:
        popular = await _fallback_popular(limit)
        recs = [
            RecommendationItem(**{**p, "reason": p.get("reason", "popular")})
            for p in popular
        ]

    return PersonalisedRecommendationsResponse(
        wallet_address=x_wallet_address,
        recommendations=recs[:limit],
        total=len(recs),
    )


@router.post("/track")
async def track_interaction(
    file_hash: str = Query(...),
    action: str = Query(..., regex="^(view|download)$"),
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
) -> dict:
    """Record an anonymised file interaction for the recommendation engine.

    This is a lightweight, fire-and-forget endpoint that stores interaction
    events to a local log which the Recommender Agent picks up on its next
    cycle.  Authentication is optional — unauthenticated interactions are
    logged under a fixed 'anonymous' token.

    The interaction is already captured via the main /files/{hash}/download
    and /files/{hash} access log; this endpoint provides an additional
    explicit signal for frontend tracking (e.g., extended reading time).
    """
    actor = x_wallet_address or "anonymous"

    # Verify file exists
    meta = await get_metadata(file_hash)
    if not meta:
        raise HTTPException(status_code=404, detail="File not found.")

    # Load and update interactions
    interactions = _load_interactions()
    anon_actor = _anonymise(actor)

    weight_map = {"view": 1.0, "download": 3.0}
    weight = weight_map.get(action, 0.5)

    if anon_actor not in interactions:
        interactions[anon_actor] = {}
    prev = interactions[anon_actor].get(file_hash, 0.0)
    interactions[anon_actor][file_hash] = prev + weight

    try:
        _INTERACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _INTERACTIONS_FILE.write_text(json.dumps(interactions, indent=2))
    except OSError as exc:
        logger.error(f"Failed to persist interaction: {exc}")

    return {"recorded": True, "file_hash": file_hash, "action": action}
