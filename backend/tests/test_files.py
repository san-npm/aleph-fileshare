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
def clear_rate_limit():
    """Clear the in-memory rate limiter between tests."""
    from src.main import _rate_limit_store
    _rate_limit_store.clear()
    yield
    _rate_limit_store.clear()


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    """Use temporary directories for storage during tests."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    meta_file = tmp_path / "metadata.json"

    access_log_file = tmp_path / "access.jsonl"

    with patch.dict(os.environ, {
        "LOCAL_STORAGE_DIR": str(storage_dir),
        "LOCAL_META_FILE": str(meta_file),
        "LOCAL_ACCESS_LOG": str(access_log_file),
        "STORAGE_MODE": "local",
    }):
        # Also patch the module-level constants
        with patch("src.services.aleph_storage.LOCAL_STORAGE_DIR", storage_dir), \
             patch("src.services.aleph_storage.STORAGE_MODE", "local"), \
             patch("src.services.aleph_aggregates.LOCAL_META_FILE", meta_file), \
             patch("src.services.aleph_aggregates.STORAGE_MODE", "local"), \
             patch("src.services.access_log.LOCAL_ACCESS_LOG", access_log_file), \
             patch("src.services.access_log.STORAGE_MODE", "local"):
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


def test_upload_with_expiry():
    """Test uploading a file with expires_in_hours sets expires_at."""
    file_content = b"expiry test"
    response = client.post(
        "/files/upload",
        files={"file": ("expire.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true", "expires_in_hours": "24"},
        headers=MOCK_AUTH_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["expires_at"] is not None
    assert "T" in data["expires_at"]  # ISO format


def test_upload_without_expiry():
    """Test uploading without expires_in_hours leaves expires_at null."""
    file_content = b"no expiry"
    response = client.post(
        "/files/upload",
        files={"file": ("noexpire.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    assert response.status_code == 201
    assert response.json()["expires_at"] is None


def test_download_expired_file_returns_410():
    """Test that downloading an expired file returns 410 Gone."""
    file_content = b"will expire"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("expired.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true", "expires_in_hours": "1"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    # Manually set expires_at to the past
    from src.services.aleph_aggregates import _load_local_db, _save_local_db
    db = _load_local_db()
    db[file_hash]["expires_at"] = "2020-01-01T00:00:00Z"
    _save_local_db(db)

    response = client.get(f"/files/{file_hash}/download")
    assert response.status_code == 410
    assert "expired" in response.json()["detail"].lower()


def test_metadata_is_expired_field():
    """Test that metadata endpoint includes is_expired computed field."""
    file_content = b"check expired field"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("expfield.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true", "expires_in_hours": "1"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    # Not expired yet
    meta_resp = client.get(f"/files/{file_hash}")
    assert meta_resp.status_code == 200
    assert meta_resp.json()["is_expired"] is False

    # Set to past
    from src.services.aleph_aggregates import _load_local_db, _save_local_db
    db = _load_local_db()
    db[file_hash]["expires_at"] = "2020-01-01T00:00:00Z"
    _save_local_db(db)

    meta_resp = client.get(f"/files/{file_hash}")
    assert meta_resp.status_code == 200
    assert meta_resp.json()["is_expired"] is True


def test_password_protected_upload_and_download():
    """Test uploading with password and downloading with correct/wrong password."""
    file_content = b"secret content"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("secret.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true", "password": "hunter2"},
        headers=MOCK_AUTH_HEADERS,
    )
    assert upload_resp.status_code == 201
    file_hash = upload_resp.json()["hash"]

    # Metadata should show password_protected=True but no password_hash
    meta_resp = client.get(f"/files/{file_hash}")
    assert meta_resp.status_code == 200
    meta = meta_resp.json()
    assert meta["password_protected"] is True
    assert "password_hash" not in meta

    # Download without password → 401
    resp_no_pw = client.get(f"/files/{file_hash}/download")
    assert resp_no_pw.status_code == 401
    assert "required" in resp_no_pw.json()["detail"].lower()

    # Download with wrong password → 401
    resp_bad_pw = client.get(
        f"/files/{file_hash}/download",
        headers={"X-Download-Password": "wrongpassword"},
    )
    assert resp_bad_pw.status_code == 401
    assert "Invalid password" in resp_bad_pw.json()["detail"]

    # Download with correct password → 200
    resp_ok = client.get(
        f"/files/{file_hash}/download",
        headers={"X-Download-Password": "hunter2"},
    )
    assert resp_ok.status_code == 200
    assert resp_ok.content == file_content


def test_upload_without_password_no_protection():
    """Test that files uploaded without password are not password-protected."""
    file_content = b"open content"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("open.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    assert upload_resp.status_code == 201
    file_hash = upload_resp.json()["hash"]

    meta_resp = client.get(f"/files/{file_hash}")
    assert meta_resp.json()["password_protected"] is False

    # Download without password → 200
    resp = client.get(f"/files/{file_hash}/download")
    assert resp.status_code == 200
    assert resp.content == file_content


def test_list_files_shows_expiry():
    """Test that list endpoint includes expiry fields."""
    file_content = b"list expiry test"
    client.post(
        "/files/upload",
        files={"file": ("listexp.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true", "expires_in_hours": "24"},
        headers=MOCK_AUTH_HEADERS,
    )

    response = client.get("/files", headers=MOCK_AUTH_HEADERS)
    assert response.status_code == 200
    files = response.json()["files"]
    # Find our file with expiry
    expiry_files = [f for f in files if f.get("expires_at") is not None]
    assert len(expiry_files) > 0
    assert "is_expired" in expiry_files[0]


# --- Phase 3c: Access Log Tests ---


def test_access_log_records_upload():
    """Test that uploading a file creates an access log entry."""
    file_content = b"access log upload test"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("logtest.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    assert upload_resp.status_code == 201
    file_hash = upload_resp.json()["hash"]

    # Fetch access log as owner
    log_resp = client.get(
        f"/files/{file_hash}/access-log",
        headers=MOCK_AUTH_HEADERS,
    )
    assert log_resp.status_code == 200
    entries = log_resp.json()
    upload_entries = [e for e in entries if e["action"] == "upload"]
    assert len(upload_entries) >= 1
    assert upload_entries[0]["actor"] == MOCK_ADDRESS
    assert upload_entries[0]["file_hash"] == file_hash


def test_access_log_records_view_and_download():
    """Test that viewing metadata and downloading create log entries."""
    file_content = b"view and download log test"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("vdlog.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    # View metadata (creates a "view" entry)
    client.get(f"/files/{file_hash}")

    # Download (creates a "download" entry)
    client.get(f"/files/{file_hash}/download")

    log_resp = client.get(
        f"/files/{file_hash}/access-log",
        headers=MOCK_AUTH_HEADERS,
    )
    assert log_resp.status_code == 200
    entries = log_resp.json()
    actions = [e["action"] for e in entries]
    assert "upload" in actions
    assert "view" in actions
    assert "download" in actions


def test_access_log_records_delete():
    """Test that deleting a file creates a delete log entry."""
    file_content = b"delete log test"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("dellog.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    # Delete the file
    client.delete(f"/files/{file_hash}", headers=MOCK_AUTH_HEADERS)

    # Access log should still have entries even though file metadata is gone
    # But the endpoint requires the file to exist, so we check the service directly
    from src.services.access_log import get_access_log
    import asyncio
    entries = asyncio.get_event_loop().run_until_complete(get_access_log(file_hash))
    actions = [e["action"] for e in entries]
    assert "delete" in actions


def test_access_log_requires_auth():
    """Test that access log endpoint requires authentication."""
    response = client.get("/files/somehash/access-log")
    assert response.status_code == 401


def test_access_log_requires_owner():
    """Test that non-owners cannot view access log."""
    file_content = b"owner only log test"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("ownerlog.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    # Try with a different wallet address
    other_headers = {
        "X-Wallet-Address": "0x1234567890abcdef1234567890abcdef12345678",
        "X-Wallet-Signature": "0x" + "cd" * 65,
        "X-Wallet-Nonce": "afs_other_nonce_456",
    }
    log_resp = client.get(
        f"/files/{file_hash}/access-log",
        headers=other_headers,
    )
    assert log_resp.status_code == 403


def test_access_log_file_not_found():
    """Test that access log for non-existent file returns 404."""
    log_resp = client.get(
        "/files/nonexistenthash/access-log",
        headers=MOCK_AUTH_HEADERS,
    )
    assert log_resp.status_code == 404


# --- Phase 3d: Revoke Shared Link Tests ---


def test_revoke_link():
    """Test that revoking a shared link disables downloads."""
    file_content = b"revoke link test"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("revoke.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    assert upload_resp.status_code == 201
    file_hash = upload_resp.json()["hash"]

    # Download works before revoke
    resp = client.get(f"/files/{file_hash}/download")
    assert resp.status_code == 200

    # Revoke the link
    patch_resp = client.patch(
        f"/files/{file_hash}/link",
        json={"link_enabled": False},
        headers=MOCK_AUTH_HEADERS,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["link_enabled"] is False

    # Download should now return 403
    resp = client.get(f"/files/{file_hash}/download")
    assert resp.status_code == 403
    assert "revoked" in resp.json()["detail"].lower()


def test_restore_link():
    """Test that re-enabling a revoked link restores downloads."""
    file_content = b"restore link test"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("restore.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    # Revoke
    client.patch(
        f"/files/{file_hash}/link",
        json={"link_enabled": False},
        headers=MOCK_AUTH_HEADERS,
    )

    # Restore
    patch_resp = client.patch(
        f"/files/{file_hash}/link",
        json={"link_enabled": True},
        headers=MOCK_AUTH_HEADERS,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["link_enabled"] is True

    # Download should work again
    resp = client.get(f"/files/{file_hash}/download")
    assert resp.status_code == 200
    assert resp.content == file_content


def test_revoke_link_requires_auth():
    """Test that revoking a link requires authentication."""
    resp = client.patch(
        "/files/somehash/link",
        json={"link_enabled": False},
    )
    assert resp.status_code == 401


def test_revoke_link_requires_owner():
    """Test that only the file owner can revoke a link."""
    file_content = b"owner only revoke test"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("ownerrevoke.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    other_headers = {
        "X-Wallet-Address": "0x1234567890abcdef1234567890abcdef12345678",
        "X-Wallet-Signature": "0x" + "cd" * 65,
        "X-Wallet-Nonce": "afs_other_nonce_789",
    }
    resp = client.patch(
        f"/files/{file_hash}/link",
        json={"link_enabled": False},
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_revoke_link_file_not_found():
    """Test revoking a link for a non-existent file returns 404."""
    resp = client.patch(
        "/files/nonexistent/link",
        json={"link_enabled": False},
        headers=MOCK_AUTH_HEADERS,
    )
    assert resp.status_code == 404


def test_metadata_shows_link_enabled():
    """Test that metadata endpoint includes link_enabled field."""
    file_content = b"link enabled field test"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("linkfield.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    # Default should be True
    meta_resp = client.get(f"/files/{file_hash}")
    assert meta_resp.status_code == 200
    assert meta_resp.json()["link_enabled"] is True

    # Revoke and check
    client.patch(
        f"/files/{file_hash}/link",
        json={"link_enabled": False},
        headers=MOCK_AUTH_HEADERS,
    )
    meta_resp = client.get(f"/files/{file_hash}")
    assert meta_resp.json()["link_enabled"] is False


def test_list_files_shows_link_enabled():
    """Test that list endpoint includes link_enabled field."""
    file_content = b"list link enabled test"
    upload_resp = client.post(
        "/files/upload",
        files={"file": ("listlink.txt", io.BytesIO(file_content), "text/plain")},
        data={"public": "true"},
        headers=MOCK_AUTH_HEADERS,
    )
    file_hash = upload_resp.json()["hash"]

    response = client.get("/files", headers=MOCK_AUTH_HEADERS)
    assert response.status_code == 200
    files = response.json()["files"]
    our_file = [f for f in files if f["hash"] == file_hash]
    assert len(our_file) == 1
    assert our_file[0]["link_enabled"] is True
