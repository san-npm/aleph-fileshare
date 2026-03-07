# 🏗️ AlephFileShare — System Architecture

This document describes the full system design, component responsibilities, and data flows for AlephFileShare.

---

## Overview

AlephFileShare is a fully decentralized file sharing platform. There is no central server, no central database, and no central CDN. Every layer runs on Aleph Cloud's decentralized supercloud:

| Concern | Solution |
|---------|----------|
| Frontend hosting | Aleph Static Hosting (IPFS) |
| Backend API | Aleph Serverless Function |
| File storage | IPFS via Aleph Cloud pinning |
| Metadata & profiles | Aleph Aggregates (decentralized KV) |
| Event logs & search | Aleph Indexer Framework |
| AI agents | Aleph Persistent VMs (AMD SEV) |
| Authentication | Wallet signature (EVM / Solana) |

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER BROWSER                                │
│           Next.js 14 Frontend (Aleph Static Hosting)                │
│        Wallet Auth │ Upload UI │ File Browser │ AI Insights          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST / WebSocket
┌────────────────────────────▼────────────────────────────────────────┐
│                  BACKEND API (Aleph Serverless Function)             │
│             FastAPI · aleph-sdk-python · Wallet-based auth           │
│       File Routes │ Metadata │ Sharing Links │ Access Control         │
└─────┬──────────────────────┬──────────────────────────┬─────────────┘
      │                      │                          │
┌─────▼──────┐   ┌───────────▼────────────┐  ┌─────────▼──────────────┐
│  IPFS      │   │  ALEPH AGGREGATES      │  │  ALEPH INDEXING        │
│  Storage   │   │  (Metadata, settings,  │  │  (Access logs, search, │
│  (Files)   │   │   user profiles)       │  │   audit trail)         │
└────────────┘   └────────────────────────┘  └────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                  AUTONOMOUS AI AGENTS (Aleph Persistent VMs)         │
│  🔍 Scanner Agent   📑 Indexer Agent   🤝 Recommender Agent          │
│  🛡️ Guardian Agent  🔔 Notifier Agent                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Frontend

**Technology**: Next.js 14 (App Router), TypeScript, TailwindCSS, wagmi v2

**Hosting**: Deployed as a static export to Aleph Cloud Static Hosting. The build output (`out/`) is uploaded to IPFS and pinned by Aleph Cloud. It is served at:
- `https://{ipfs-cid-v1}.ipfs.aleph.sh` (default)
- Custom domain (optional)

**Responsibilities**:
- Wallet connection (MetaMask, WalletConnect via wagmi)
- File upload UI with drag-and-drop and progress tracking
- File browser (list own files via API)
- Shareable link generation and download page
- Display AI scan status badges and tags (Phase 2+)

**Auth model**: The frontend never holds a session token. Instead it signs a challenge message with the user's wallet on every authenticated request and sends the raw signature in the `X-Wallet-Signature` header.

---

## Backend API

**Technology**: Python 3.11, FastAPI, aleph-sdk-python

**Hosting**: Deployed as an Aleph Cloud Serverless Function. Invocations are routed through Aleph's compute network.

**Responsibilities**:
- Receive file uploads and forward them to IPFS via `aleph-sdk-python`
- Store file metadata as Aleph Aggregate messages (keyed by IPFS hash)
- Verify wallet signatures on write operations
- Generate and validate shareable download tokens
- Enforce file size and MIME type limits
- Write access log entries to Aleph Indexer

**API base URL (local)**: `http://localhost:8000`  
**API docs (local)**: `http://localhost:8000/docs`

See [api-reference.md](api-reference.md) for all endpoints.

---

## Storage Layer

### File Storage — IPFS

Files are uploaded to IPFS via the Aleph Cloud SDK:

```python
from aleph.sdk.client import AuthenticatedAlephHttpClient

async with AuthenticatedAlephHttpClient(account) as client:
    result = await client.create_store(
        file_content=file_bytes,
        storage_engine="ipfs",
        channel="ALEPH_FILESHARE",
        guess_mime_type=True,
        sync=True,
    )
    ipfs_hash = result.item_hash
```

Files are accessible at:
- `https://ipfs.aleph.cloud/ipfs/{hash}` — Aleph IPFS gateway
- Any public IPFS gateway as a fallback

### Metadata — Aleph Aggregates

File metadata is stored as an Aleph Aggregate (mutable key-value document), keyed by the IPFS hash:

```python
await client.create_aggregate(
    key=ipfs_hash,
    content={
        "filename": "report.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 204800,
        "uploader": wallet_address,
        "uploaded_at": timestamp,
        "public": True,
        "scan_status": "pending",
        "tags": [],
    },
    channel="ALEPH_FILESHARE",
)
```

---

## Authentication

AlephFileShare uses **wallet signature authentication** — no passwords, no JWTs, no sessions.

**Flow**:
1. Frontend requests a challenge from `GET /auth/challenge?address={wallet}`
2. Backend generates a time-bound nonce and caches it in an Aleph Aggregate
3. User signs the challenge with their wallet
4. Frontend sends the signature in `X-Wallet-Signature` and wallet address in `X-Wallet-Address` headers
5. Backend verifies the signature using `eth_account.messages.recover_message`
6. If valid and nonce not expired, the request proceeds

---

## AI Agents

Agents run as long-lived processes on **Aleph Persistent VMs** (AMD SEV confidential computing). They communicate with the rest of the system exclusively via Aleph messages — no direct API calls.

| Agent | Trigger | Output |
|-------|---------|--------|
| Scanner | New STORE message detected | `scan_status` Aggregate update |
| Indexer | `scan_status = clean` | `tags`, `description` Aggregate update |
| Recommender | User access log event | `/recommendations` Aggregate per user |
| Guardian | Continuous (cron-like) | Abuse flags, health Aggregate |
| Notifier | Guardian/Scanner alert | Aleph POST message to subscribers |

See [ai-agents.md](ai-agents.md) for detailed agent documentation.

---

## Data Flows

### Upload Flow

```
User selects file
  → Frontend signs upload request with wallet
  → POST /files/upload (multipart)
  → Backend verifies signature
  → Backend streams file to IPFS via aleph-sdk-python
  → Backend creates Aggregate (metadata)
  → Backend writes access log entry to Aleph Indexer
  → Returns { hash, share_url } to frontend
  → Scanner Agent detects new STORE message → scans file
  → Indexer Agent detects clean scan → tags file
```

### Download Flow

```
User visits share URL /d/{hash}
  → Frontend fetches metadata: GET /files/{hash}
  → If public: no auth required
  → If private: wallet signature required
  → Frontend fetches: GET /files/{hash}/download
  → Backend verifies access, streams from IPFS gateway
  → Backend logs download event to Aleph Indexer
```

---

## Security Considerations

- All write operations require a valid wallet signature
- Nonces are single-use and expire after 5 minutes
- File size and MIME type validation on the backend before IPFS upload
- Scanner Agent flags and blocks malicious files from being served
- Confidential VMs (AMD SEV) used for agents to protect LLM prompts and scan results
- All secrets live in environment variables — nothing hardcoded
