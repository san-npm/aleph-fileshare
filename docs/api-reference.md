# 📡 API Reference

All endpoints are served by the FastAPI backend, deployed as an Aleph Cloud Serverless Function.

**Local base URL**: `http://localhost:8000`  
**Production base URL**: set in `NEXT_PUBLIC_API_URL`

---

## Authentication

Write operations (upload, delete) require wallet signature authentication.

Add the following headers to authenticated requests:

| Header | Description |
|--------|-------------|
| `X-Wallet-Address` | Sender's EVM wallet address (checksummed) |
| `X-Wallet-Signature` | Hex signature of the challenge nonce |
| `X-Wallet-Nonce` | The nonce obtained from `GET /auth/challenge` |

### Get a Challenge Nonce

```
GET /auth/challenge
```

**Query params**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `address` | string | ✅ | Wallet address |

**Response `200`**:
```json
{
  "nonce": "afs_1a2b3c4d5e6f",
  "message": "Sign this message to authenticate with AlephFileShare.\nNonce: afs_1a2b3c4d5e6f\nExpires in 5 minutes.",
  "expires_at": 1712345678
}
```

---

## Files

### Upload a File

```
POST /files/upload
```

🔒 Requires authentication headers.

**Request**: `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | ✅ | File to upload (max size from `MAX_FILE_SIZE_BYTES`) |
| `public` | bool | — | Whether the file is publicly accessible (default: `true`) |
| `filename_override` | string | — | Custom display name |

**Response `201`**:
```json
{
  "hash": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
  "filename": "report.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 204800,
  "public": true,
  "share_url": "https://yourapp.aleph.sh/d/QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
  "uploaded_at": "2026-04-01T10:00:00Z"
}
```

**Error responses**:

| Code | Meaning |
|------|---------|
| `400` | File too large or MIME type not allowed |
| `401` | Missing or invalid wallet signature |
| `429` | Rate limit exceeded |

---

### Get File Metadata

```
GET /files/{hash}
```

🔓 Public files: no auth required.  
🔒 Private files: requires authentication headers.

**Path params**:

| Param | Type | Description |
|-------|------|-------------|
| `hash` | string | IPFS hash of the file |

**Response `200`**:
```json
{
  "hash": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
  "filename": "report.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 204800,
  "public": true,
  "uploader": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
  "uploaded_at": "2026-04-01T10:00:00Z",
  "scan_status": "clean",
  "tags": ["document", "pdf", "report"],
  "description": "Quarterly financial report for Q1 2026"
}
```

---

### Download a File

```
GET /files/{hash}/download
```

🔓 Public files: no auth required.  
🔒 Private files: requires authentication headers.

Streams the raw file bytes from IPFS. Sets `Content-Disposition: attachment; filename="{filename}"` and the appropriate `Content-Type`.

**Response `200`**: Binary file stream.

**Error responses**:

| Code | Meaning |
|------|---------|
| `404` | File not found on IPFS |
| `403` | File is private and caller is not the owner |
| `451` | File flagged by Scanner Agent |

---

### List Your Files

```
GET /files
```

🔒 Requires authentication headers.

**Query params**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | `20` | Max results (max `100`) |
| `offset` | int | `0` | Pagination offset |
| `sort` | string | `uploaded_at_desc` | `uploaded_at_asc`, `uploaded_at_desc`, `size_asc`, `size_desc` |

**Response `200`**:
```json
{
  "total": 42,
  "limit": 20,
  "offset": 0,
  "files": [
    {
      "hash": "Qm...",
      "filename": "report.pdf",
      "size_bytes": 204800,
      "uploaded_at": "2026-04-01T10:00:00Z",
      "scan_status": "clean"
    }
  ]
}
```

---

### Delete a File

```
DELETE /files/{hash}
```

🔒 Requires authentication headers. Only the file owner can delete.

> ⚠️ This sends an Aleph FORGET message to remove the file from the network. Due to the P2P nature of IPFS, content may persist on external nodes that have pinned it.

**Response `200`**:
```json
{
  "message": "File forget message submitted.",
  "hash": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco"
}
```

---

## Health

### Health Check

```
GET /health
```

🔓 No auth required. Used by Docker Compose and monitoring tools.

**Response `200`**:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "aleph_connected": true
}
```

---

## Error Format

All error responses follow this format:

```json
{
  "detail": "Human-readable error message",
  "code": "ERROR_CODE_SLUG"
}
```
