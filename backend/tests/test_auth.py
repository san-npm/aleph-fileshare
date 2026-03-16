"""Tests for auth endpoints."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_challenge_returns_nonce() -> None:
    response = client.get("/auth/challenge", params={"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"})
    assert response.status_code == 200
    data = response.json()
    assert data["nonce"].startswith("afs_")
    assert "message" in data
    assert "expires_at" in data


def test_challenge_rejects_invalid_address() -> None:
    response = client.get("/auth/challenge", params={"address": "not_a_wallet"})
    assert response.status_code == 400
