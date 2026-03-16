"""Wallet signature verification and nonce management."""

import os
import secrets
import time
from typing import Optional

from eth_account.messages import encode_defunct
from web3 import Web3

# In-memory nonce store: { nonce: { address, expires_at } }
_nonce_store: dict[str, dict] = {}

NONCE_TTL_SECONDS = 300  # 5 minutes


def generate_nonce(address: str) -> dict:
    """Generate a time-bound nonce for wallet authentication.

    Args:
        address: EVM wallet address requesting the challenge.

    Returns:
        Dict with nonce, message, and expires_at.
    """
    nonce = f"afs_{secrets.token_hex(12)}"
    expires_at = int(time.time()) + NONCE_TTL_SECONDS
    message = (
        f"Sign this message to authenticate with AlephFileShare.\n"
        f"Nonce: {nonce}\n"
        f"Expires in 5 minutes."
    )

    _nonce_store[nonce] = {
        "address": address.lower(),
        "expires_at": expires_at,
        "message": message,
    }

    # Prune expired nonces
    _prune_expired()

    return {
        "nonce": nonce,
        "message": message,
        "expires_at": expires_at,
    }


def verify_signature(
    address: str, signature: str, nonce: str
) -> bool:
    """Verify an EVM wallet signature against a stored nonce.

    Args:
        address: Claimed wallet address.
        signature: Hex-encoded signature.
        nonce: The nonce that was signed.

    Returns:
        True if signature is valid and nonce is fresh.
    """
    stored = _nonce_store.get(nonce)
    if not stored:
        return False

    if time.time() > stored["expires_at"]:
        _nonce_store.pop(nonce, None)
        return False

    if stored["address"] != address.lower():
        return False

    message = stored["message"]

    try:
        msg = encode_defunct(text=message)
        w3 = Web3()
        recovered = w3.eth.account.recover_message(msg, signature=signature)
        valid = recovered.lower() == address.lower()
    except Exception:
        return False

    # Nonce is single-use — consume it
    if valid:
        _nonce_store.pop(nonce, None)

    return valid


def _prune_expired() -> None:
    """Remove expired nonces from the store."""
    now = time.time()
    expired = [k for k, v in _nonce_store.items() if now > v["expires_at"]]
    for k in expired:
        del _nonce_store[k]
