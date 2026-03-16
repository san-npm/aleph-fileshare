"""Tests for file endpoints."""

import io
import json
import os
import tempfile
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

# Mock auth headers — we'll patch verify_signature to always return True
MOCK_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
MOCK_AUTH_HEADERS = {
    "X-Wallet-Address": MOCK_ADDRESS,
    "X-Wallet-Signature": "0x" + "ab" * 65,
    "X-Wallet-Nonce": "afs_test_nonce_123",
}


@pytest.fixture(autouse=True)
def mock_auth():
    """Patch verify_signature to always return True for tests."""
    with patch("src.api.files.verify_signature", return_value=True):
        yield


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    """Use temporary directories for storage during tests."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    meta_file = tmp_path / "metadata.json"

    with patch.dict(os.environ, {
        "LOCAL_STORAGE_DIR": str(storage_dir),
        "LOCAL_META_FILE": str(meta_file),
        "STORAGE_MODE": "local",
    }):
        # Also patch the module-level constants
        with patch("src.services.aleph_storage.LOCAL_STORAGE_DIR", storage_dir), \
             patch("src.services.aleph_storage.STORAGE_MODE", "local"), \
             patch("src.services.aleph_aggregates.LOCAL_META_FILE", meta_file), \
             patch("src.services.aleph_aggregates.STORAGE_MODE", "local"):
            yield storage_dir, meta_file


def test_upload_file():
    """Test uploading a file returns 201 with correct metadata."""
    file_content = b"Hello, AlephFileShare!"
    response = client.post(
        "/files/upload",
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["mime_type"] == "text/plain"
    assert data["size_bytes"] == len(file_content)
    assert data["public"] is True
    assert "hash" in data
    assert "share_url" in data
    assert "uploaded_at" in data


def test_upload_file_sets_pending_scan_status():
    """Test that uploaded files start with scan_status='pending' and empty tags."""
    file_content = b"Scan me please"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("scan_test.pdf", io.BytesIO(file_content), "application/pdf")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    assert upload_resp.status_code == 201
    file_hash = upload_resp.json()["hash"]

    # Fetch metadata and verify scan_status
    meta_resp = client.get(f"/files/{file_hash}")
    assert meta_resp.status_code == 200
    meta = meta_resp.json()
    assert meta["scan_status"] == "pending"
    assert meta["tags"] == []
    assert meta["description"] == ""


def test_get_file_metadata():
    """Test retrieving file metadata by hash."""
    file_content = b"metadata test content"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("meta.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    response = client.get(f"/files/{file_hash}")
    assert response.status_code == 200
    data = response.json()
    assert data["hash"] == file_hash
    assert data["filename"] == "meta.txt"
    assert data["mime_type"] == "text/plain"
    assert data["uploader"] == MOCK_ADDRESS


def test_get_file_metadata_not_found():
    """Test 404 for non-existent file hash."""
    response = client.get("/files/nonexistenthash123")
    assert response.status_code == 404


def test_get_scan_status():
    """Test the scan-status quick-check endpoint."""
    file_content = b"scan status check"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("status.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    response = client.get(f"/files/{file_hash}/scan-status")
    assert response.status_code == 200
    data = response.json()
    assert data["hash"] == file_hash
    assert data["scan_status"] == "pending"
    assert data["tags"] == []
    assert data["description"] == ""


def test_get_scan_status_not_found():
    """Test 404 for scan-status of non-existent file."""
    response = client.get("/files/nonexistent/scan-status")
    assert response.status_code == 404


def test_list_files():
    """Test listing files for authenticated user."""
    # Upload two files with different content (same content = same hash)
    for i, name in enumerate(("list1.txt", "list2.txt")):
        client.post(
            "/files/upload",
            files={"file": (name, io.BytesIO(f"content {i}".encode()), "text/plain")},
            data={"public": "true"},
            headers=MOCK_AUTH_HEADERS,
        )

    response = client.get("/files", headers=MOCK_AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["files"]) >= 2
    # Verify scan_status and tags are in list response
    for file_item in data["files"]:
        assert "scan_status" in file_item
        assert "tags" in file_item


def test_list_files_requires_auth():
    """Test that listing files without auth returns 401."""
    response = client.get("/files")
    assert response.status_code == 401


def test_delete_file():
    """Test deleting a file."""
    file_content = b"delete me"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("delete.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    response = client.delete(f"/files/{file_hash}", headers=MOCK_AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["hash"] == file_hash

    # Verify file is gone
    get_resp = client.get(f"/files/{file_hash}")
    assert get_resp.status_code == 404


def test_delete_file_not_found():
    """Test deleting a non-existent file returns 404."""
    response = client.delete("/files/nonexistent", headers=MOCK_AUTH_HEADERS)
    assert response.status_code == 404


def test_download_file():
    """Test downloading a file."""
    file_content = b"download this content"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("download.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    response = client.get(f"/files/{file_hash}/download")
    assert response.status_code == 200
    assert response.content == file_content
    assert "download.txt" in response.headers.get("content-disposition", "")


def test_download_flagged_file_blocked():
    """Test that flagged files cannot be downloaded."""
    file_content = b"flagged content"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("bad.exe", io.BytesIO(file_content), "application/octet-stream")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    # Manually update metadata to flagged
    from src.services.aleph_aggregates import _load_local_db, _save_local_db
    db = _load_local_db()
    db[file_hash]["scan_status"] = "flagged"
    _save_local_db(db)

    response = client.get(f"/files/{file_hash}/download")
    assert response.status_code == 451
