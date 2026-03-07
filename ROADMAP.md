# 🗺️ AlephFileShare — Project Roadmap

This document outlines the development phases, milestones, and priorities for AlephFileShare. The project is built iteratively, with each phase shipping a working, deployable product.

---

## 🔭 Vision

AlephFileShare aims to be the go-to decentralized alternative to WeTransfer and Google Drive — with full data sovereignty, autonomous AI moderation, and zero reliance on centralized infrastructure. Every component runs on Aleph Cloud's decentralized supercloud.

---

## Phase 0 — Foundation ✅ *Current*

> **Goal**: Establish the project structure, documentation, and infrastructure scaffolding.

- [x] GitHub repository created
- [x] Full architecture documentation written
- [x] Technology stack finalized (Next.js 14 + FastAPI + Aleph Cloud)
- [x] Developer environment (Docker Compose) defined
- [x] CI/CD pipeline skeleton (GitHub Actions)
- [x] AI agent design documentation
- [x] Contribution guidelines written

**Deliverable**: Cloneable repo, runnable Docker environment, no feature functionality yet.

---

## Phase 1 — Core File Sharing MVP 🔨 *Q2 2026*

> **Goal**: Working file upload, storage on IPFS via Aleph Cloud, and download via shareable link.

### Backend
- [ ] FastAPI application with Aleph Cloud serverless deployment
- [ ] `POST /files/upload` — upload file to IPFS via aleph-sdk-python
- [ ] `GET /files/{hash}` — retrieve file metadata
- [ ] `GET /files/{hash}/download` — stream file from IPFS
- [ ] `DELETE /files/{hash}` — forget file message from Aleph
- [ ] Wallet-based authentication (EVM signature verification)
- [ ] File metadata stored in Aleph Aggregates
- [ ] Rate limiting and file size validation

### Frontend
- [ ] Next.js 14 app with App Router and TypeScript
- [ ] Wallet connection (wagmi + MetaMask, WalletConnect)
- [ ] Drag-and-drop file upload with progress bar
- [ ] Shareable link generation
- [ ] File download page
- [ ] Basic file browser (list your own files)
- [ ] Deploy frontend as Aleph static website

### Infrastructure
- [ ] Backend deployed as Aleph Cloud serverless function
- [ ] Frontend deployed as Aleph static hosting
- [ ] `.env.example` fully documented
- [ ] Docker Compose for local dev

**Deliverable**: Functional MVP — upload, share link, download. Fully on Aleph Cloud.

---

## Phase 2 — AI Scanner & Indexer Agents 🤖 *Q3 2026*

> **Goal**: Deploy the first two autonomous AI agents on Aleph Cloud Persistent VMs.

### Scanner Agent
- [ ] Deploy Scanner Agent on Aleph Cloud Persistent VM (AMD SEV confidential)
- [ ] File hash analysis and malware signature matching
- [ ] Integration with VirusTotal API (via VM internet access)
- [ ] Publish scan results as Aleph POST messages
- [ ] Block flagged files from being served
- [ ] Admin alert mechanism via Aleph messaging

### Indexer Agent
- [ ] Deploy Indexer Agent on Aleph Cloud Persistent VM
- [ ] File type detection (MIME analysis)
- [ ] Automatic tag generation using LibertAI (open-source LLM on Aleph)
- [ ] Auto-generate file descriptions for images/documents
- [ ] Write enriched metadata to Aleph Aggregates
- [ ] Full-text search index via Aleph Indexer

### Frontend Updates
- [ ] Show scan status badges on files (clean / scanning / flagged)
- [ ] Display AI-generated tags and descriptions
- [ ] Search bar powered by Aleph Indexer

**Deliverable**: Files are automatically scanned and tagged by AI agents after upload.

---

## Phase 3 — Access Control & Privacy 🔐 *Q3 2026*

> **Goal**: Add granular access control, private files, and encrypted uploads.

- [ ] Private vs public file toggle
- [ ] Password-protected download links
- [ ] Encrypted file storage using Aleph encrypted volumes
- [ ] Expiry dates on shared links
- [ ] Access log stored on Aleph Indexer (who accessed what, when)
- [ ] Confidential VM for sensitive file processing (AMD SEV-SNP)
- [ ] Revoke access / delete shared link
- [ ] Multi-signature access (require multiple wallet approvals)

**Deliverable**: Files can be private, encrypted, time-limited, or multi-party gated.

---

## Phase 4 — Recommender & Guardian Agents 🛡️ *Q4 2026*

> **Goal**: Deploy the remaining two AI agents for personalization and network defense.

### Recommender Agent
- [ ] Deploy on Aleph Cloud Persistent VM
- [ ] Track user file interaction patterns (anonymized, stored on Aleph)
- [ ] Collaborative filtering model for file recommendations
- [ ] Expose recommendations via `/api/recommendations` endpoint
- [ ] "Similar files" sidebar on download page
- [ ] Weekly digest notifications via Aleph messaging

### Guardian Agent
- [ ] Deploy on Aleph Cloud Persistent VM
- [ ] Monitor Aleph network node health
- [ ] Detect unusual upload spikes (bot activity, DDOS patterns)
- [ ] Auto-throttle abusive wallets via Aleph Aggregate flags
- [ ] Health dashboard endpoint
- [ ] Automated incident reports posted as Aleph messages

**Deliverable**: The platform is self-managing — AI handles moderation, health, and personalization autonomously.

---

## Phase 5 — Collections & Collaboration 📂 *Q1 2027*

> **Goal**: Shared folders, collaborative workspaces, and batch operations.

- [ ] File collections (folders) backed by Aleph Aggregates
- [ ] Invite collaborators by wallet address
- [ ] Real-time activity feed (watch messages on Aleph)
- [ ] Batch upload / batch download as ZIP
- [ ] File versioning (update STORE message with `ref`)
- [ ] Collection-level access control
- [ ] Public gallery mode (showcase collections publicly)

**Deliverable**: Teams can collaborate on file collections, all decentralized.

---

## Phase 6 — Mobile & Advanced AI *Q2 2027*

> **Goal**: Mobile-first experience and advanced AI capabilities.

- [ ] Progressive Web App (PWA) for mobile
- [ ] Native mobile apps (React Native)
- [ ] AI-powered file deduplication across users
- [ ] On-device preview generation (thumbnails, PDF previews)
- [ ] GPU-accelerated AI processing via Aleph GPU marketplace
- [ ] Semantic search (vector embeddings via LibertAI)
- [ ] Multi-language support (i18n)

---

## Phase 7 — DAO Governance & Token Integration *Q3 2027*

> **Goal**: Community governance and ALEPH token utility.

- [ ] Governance proposals via Aleph messaging
- [ ] ALEPH token staking to unlock premium storage quotas
- [ ] On-chain payment for large storage using ALEPH Pay-As-You-Go
- [ ] Community-curated file moderation (DAO voting)
- [ ] Public API with rate limits enforced via token holding
- [ ] Plugin system for community extensions

---

## 📊 Milestone Summary

| Phase | Name | Target | Status |
|-------|------|--------|--------|
| 0 | Foundation | Q1 2026 | ✅ Complete |
| 1 | Core File Sharing MVP | Q2 2026 | 🔨 In Progress |
| 2 | AI Scanner & Indexer | Q3 2026 | 📋 Planned |
| 3 | Access Control & Privacy | Q3 2026 | 📋 Planned |
| 4 | Recommender & Guardian | Q4 2026 | 📋 Planned |
| 5 | Collections & Collaboration | Q1 2027 | 📋 Planned |
| 6 | Mobile & Advanced AI | Q2 2027 | 📋 Planned |
| 7 | DAO Governance | Q3 2027 | 📋 Planned |

---

## 🙋 How to Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md). Phase 1 tasks are labeled `good first issue` in GitHub Issues.
