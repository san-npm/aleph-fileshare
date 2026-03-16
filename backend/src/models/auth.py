"""Pydantic models for authentication."""

from pydantic import BaseModel, Field


class ChallengeResponse(BaseModel):
    """Response from GET /auth/challenge."""

    nonce: str = Field(..., description="Time-bound nonce prefixed with afs_")
    message: str = Field(..., description="Human-readable message to sign")
    expires_at: int = Field(..., description="Unix timestamp when the nonce expires")


class AuthHeaders(BaseModel):
    """Parsed authentication headers."""

    wallet_address: str
    wallet_signature: str
    wallet_nonce: str
