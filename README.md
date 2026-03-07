# 🌐 AlephFileShare

> **Decentralized, censorship-resistant file sharing — powered by Aleph Cloud, driven by autonomous AI agents.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Aleph Cloud](https://img.shields.io/badge/Powered%20by-Aleph%20Cloud-6C3CE1)](https://aleph.cloud)
[![Built with FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com)
[![Built with Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-000000)](https://nextjs.org)

---

## 🗺️ Overview

**AlephFileShare** is a full-stack, fully decentralized file sharing platform. It uses the complete Aleph Cloud infrastructure stack — IPFS storage, serverless functions, persistent VMs, confidential computing, and on-chain indexing — to provide a WeTransfer/Google Drive alternative with zero central points of failure.

AI agents run permanently on Aleph Cloud VMs to autonomously handle file scanning, metadata indexing, access recommendations, and network health monitoring — with no human in the loop required.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER BROWSER                                │
│           Next.js 14 Frontend (Aleph Static Hosting)                │
│        Wallet Auth │ Upload UI │ File Browser │ AI Insights          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST / WebSocket
┌────────────────────────────▼────────────────────────────────────────┐
│                  BACKEND API (Aleph Serverless Function)             │
│             FastAPI · aleph-sdk-python · JWT-less auth               │
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
│                                                                       │
│  🔍 Scanner Agent   📑 Indexer Agent   🤝 Recommender Agent          │
│  🛡️ Guardian Agent  🔔 Notifier Agent                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Stack Components

| Layer | Technology | Aleph Cloud Service |
|-------|-----------|---------------------|
| Frontend | Next.js 14, TypeScript, TailwindCSS, wagmi | Static Web Hosting |
| Backend API | Python 3.11, FastAPI, aleph-sdk-python | Serverless Function |
| File Storage | IPFS + Aleph pinning | IPFS + Storage |
| Metadata DB | Aleph Aggregates | Decentralized KV |
| AI Agents | Python, LangChain, LibertAI | Persistent VMs (AMD SEV) |
| Event Indexing | Aleph Indexer Framework | Indexing Service |
| Auth | Wallet signatures (EVM/Solana) | Aleph SDK auth |
| CI/CD | GitHub Actions | Aleph CLI deploy |

---

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- An Ethereum or Solana wallet
- Aleph Cloud account with ALEPH tokens

### 1. Clone and install

```bash
git clone https://github.com/san-npm/aleph-fileshare.git
cd aleph-fileshare

# Install backend
cd backend && pip install -r requirements.txt && cd ..

# Install frontend
cd frontend && npm install && cd ..

# Install agents
cd agents && pip install -r requirements.txt && cd ..
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your ALEPH_PRIVATE_KEY and other settings
```

### 3. Run locally (Docker Compose)

```bash
docker-compose up --build
```

Frontend: http://localhost:3000  
Backend API: http://localhost:8000  
API Docs: http://localhost:8000/docs

### 4. Deploy to Aleph Cloud

```bash
# Deploy all services to Aleph Cloud
bash scripts/deploy.sh
```

---

## 📁 Repository Structure

```
aleph-fileshare/
├── README.md                  # This file
├── ROADMAP.md                 # Project roadmap
├── CONTRIBUTING.md            # Contribution guide
├── .env.example               # Environment variable template
├── docker-compose.yml         # Local development stack
│
├── docs/                      # Full documentation
│   ├── architecture.md        # Detailed system architecture
│   ├── getting-started.md     # Developer onboarding guide
│   ├── api-reference.md       # API endpoint reference
│   ├── ai-agents.md           # AI agent documentation
│   ├── deployment.md          # Aleph Cloud deployment guide
│   └── configuration.md      # Config reference
│
├── frontend/                  # Next.js 14 web application
│   ├── src/app/               # App Router pages
│   ├── src/components/        # Reusable UI components
│   ├── src/hooks/             # Custom React hooks
│   └── src/lib/               # Aleph SDK integration
│
├── backend/                   # FastAPI application
│   ├── src/main.py            # Application entry point
│   ├── src/api/               # Route handlers
│   ├── src/services/          # Aleph Cloud service wrappers
│   └── src/models/            # Pydantic models
│
├── agents/                    # Autonomous AI agents
│   ├── src/scanner_agent.py   # File security scanner
│   ├── src/indexer_agent.py   # Metadata & tagging agent
│   ├── src/recommender_agent.py  # Recommendation engine
│   └── src/guardian_agent.py  # Network guardian
│
├── infrastructure/            # Deployment configs
│   ├── aleph/                 # Aleph Cloud deploy scripts
│   └── nginx/                 # Reverse proxy config
│
└── scripts/                   # Helper scripts
    ├── setup.sh
    ├── deploy.sh
    └── test.sh
```

---

## 📄 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | Full system design and data flows |
| [Getting Started](docs/getting-started.md) | Step-by-step dev setup |
| [API Reference](docs/api-reference.md) | All REST endpoints |
| [AI Agents](docs/ai-agents.md) | Agent design and capabilities |
| [Deployment](docs/deployment.md) | Aleph Cloud production deploy |
| [Configuration](docs/configuration.md) | All environment variables |
| [Roadmap](ROADMAP.md) | Project milestones and timeline |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We welcome issues, feature requests, and pull requests.

---

## 📜 License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  Built with ❤️ on <a href="https://aleph.cloud">Aleph Cloud</a> · Fully decentralized · Zero vendor lock-in
</p>
