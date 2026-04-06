"""Wallet signature verification with stateless HMAC-signed challenge tokens.

Uses HMAC-signed tokens instead of an in-memory nonce store so that
authentication works across stateless serverless replicas.

Compound nonce format: {random_nonce}.{expires_at}.{hmac_signature}
"""

import hashlib
import hmac
import json
import os
import secrets
import time

from eth_account.messages import encode_defunct
from web3 import Web3

NONCE_TTL_SECONDS = 300  # 5 minutes

# Server-side secret used to sign challenge tokens.
# MUST be set in production via CHALLENGE_SECRET env var.
# In dev, a random value is generated per process start (acceptable).
_CHALLENGE_SECRET = os.getenv(
    "CHALLENGE_SECRET",
    secrets.token_hex(32),
)


def _sign_payload(payload: dict) -> str:
    """Create an HMAC-SHA256 signature for a JSON payload."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        _CHALLENGE_SECRET.encode(), raw.encode(), hashlib.sha256
    ).hexdigest()


def _verify_payload(payload: dict, signature: str) -> bool:
    """Verify an HMAC-SHA256 signature (constant-time comparison)."""
    expected = _sign_payload(payload)
    return hmac.compare_digest(expected, signature)


def generate_nonce(address: str) -> dict:
    """Generate a stateless, HMAC-signed challenge token.

    No server-side storage is needed — the HMAC signature guarantees
    the token was issued by this server and hasn't been tampered with.

    Args:
        address: EVM wallet address requesting the challenge.

    Returns:
        Dict with nonce (compound token), message, and expires_at.
    """
    random_part = secrets.token_hex(12)
    random_nonce = f"afs_{random_part}"
    expires_at = int(time.time()) + NONCE_TTL_SECONDS

    message = (
        f"Sign this message to authenticate with AlephFileShare.\n"
        f"Nonce: {random_nonce}\n"
        f"Expires in 5 minutes."
    )

    payload = {
        "address": address.lower(),
        "nonce": random_nonce,
        "expires_at": expires_at,
    }
    token_sig = _sign_payload(payload)

    # Compound nonce: afs_random.expires_at.hmac
    compound_nonce = f"{random_nonce}.{expires_at}.{token_sig}"

    return {
        "nonce": compound_nonce,
        "message": message,
        "expires_at": expires_at,
    }


def verify_signature(
    address: str, signature: str, nonce: str
) -> bool:
    """Verify an EVM wallet signature against a stateless challenge token.

    Validates:
    1. Compound nonce format (random.expires_at.hmac)
    2. HMAC integrity (token was issued by this server, not tampered)
    3. Token hasn't expired
    4. Wallet signature recovers to the claimed address

    Args:
        address: Claimed wallet address.
        signature: Hex-encoded wallet signature.
        nonce: Compound nonce from generate_nonce.

    Returns:
        True if all checks pass.
    """
    # Parse compound nonce
    parts = nonce.split(".")
    if len(parts) != 3:
        return False

    random_nonce, expires_at_str, token_sig = parts

    try:
        expires_at = int(expires_at_str)
    except ValueError:
        return False

    # Check expiry first (cheap check)
    if time.time() > expires_at:
        return False

    # Verify HMAC — proves the token was issued by this server and not forged
    payload = {
        "address": address.lower(),
        "nonce": random_nonce,
        "expires_at": expires_at,
    }
    if not _verify_payload(payload, token_sig):
        return False

    # Reconstruct the message the user signed
    message = (
        f"Sign this message to authenticate with AlephFileShare.\n"
        f"Nonce: {random_nonce}\n"
        f"Expires in 5 minutes."
    )

    # Verify wallet signature
    try:
        msg = encode_defunct(text=message)
        w3 = Web3()
        recovered = w3.eth.account.recover_message(msg, signature=signature)
        return recovered.lower() == address.lower()
    except Exception:
        return False
