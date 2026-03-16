"""Tests for health endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_returns_storage_mode() -> None:
    response = client.get("/health")
    data = response.json()
    assert "storage_mode" in data
