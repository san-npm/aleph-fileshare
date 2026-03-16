"""Authentication routes."""

from fastapi import APIRouter, HTTPException, Query

from src.models.auth import ChallengeResponse
from src.services.auth_service import generate_nonce

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/challenge", response_model=ChallengeResponse)
async def get_challenge(
    address: str = Query(..., description="EVM wallet address"),
) -> ChallengeResponse:
    """Generate a time-bound nonce for wallet authentication.

    The client must sign the returned message with their wallet
    and include the signature in subsequent authenticated requests.
    """
    if not address or len(address) != 42 or not address.startswith("0x"):
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address format.",
        )

    result = generate_nonce(address)
    return ChallengeResponse(**result)
