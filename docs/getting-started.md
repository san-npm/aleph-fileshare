# 🚀 Getting Started

This guide walks you through setting up AlephFileShare for local development from scratch.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Python | 3.11+ | [python.org](https://python.org) |
| Docker | 24+ | [docker.com](https://docker.com) |
| Docker Compose | 2.20+ | Included with Docker Desktop |
| Git | Any | |
| Ethereum wallet | — | MetaMask or any EVM wallet |
| ALEPH tokens | ≥ 2000 | Required for Aleph Cloud storage |

> **Tip**: You don't need ALEPH tokens for local development — the Docker Compose stack uses local stubs for Aleph services.

---

## 1. Clone the Repository

```bash
git clone https://github.com/san-npm/aleph-fileshare.git
cd aleph-fileshare
```

---

## 2. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in the required values:

```env
# Required for Aleph Cloud integration
ALEPH_PRIVATE_KEY=0xyour_private_key_here

# Required for wallet login UI
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id
```

Get a free WalletConnect Project ID at [cloud.walletconnect.com](https://cloud.walletconnect.com).

See [configuration.md](configuration.md) for every variable explained in detail.

---

## 3. Install Dependencies

### Backend

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### Frontend

```bash
cd frontend
npm install
cd ..
```

### Agents (optional for Phase 1)

```bash
cd agents
pip install -r requirements.txt
cd ..
```

---

## 4. Run with Docker Compose

The fastest way to start the full local stack:

```bash
docker-compose up --build
```

This starts:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (Redoc) | http://localhost:8000/redoc |

To run in detached mode:

```bash
docker-compose up -d --build
```

To stop:

```bash
docker-compose down
```

---

## 5. Run Without Docker (Development Mode)

### Backend

```bash
cd backend
uvicorn src.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm run dev
```

---

## 6. Verify the Setup

1. Open http://localhost:3000
2. Click **Connect Wallet** and connect MetaMask
3. Drag and drop any file onto the upload area
4. You should see an upload progress bar, and then a shareable link
5. Open the shareable link in a new tab — the file should download

If anything fails, check `docker-compose logs backend` or `docker-compose logs frontend`.

---

## 7. Running Tests

```bash
# All tests
bash scripts/test.sh

# Backend only
cd backend && pytest

# Frontend only
cd frontend && npm run test
```

---

## 8. Branching & Contributing

All development happens on the `dev` branch. Never push directly to `main`.

```bash
git checkout dev
git checkout -b feat/my-feature
# ... make changes ...
git commit -m "feat: describe your change"
git push origin feat/my-feature
# Open a PR targeting dev
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full contribution guide.

---

## Useful Links

- [Aleph Cloud Docs](https://docs.aleph.cloud)
- [aleph-sdk-python](https://github.com/aleph-im/aleph-sdk-python)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Next.js 14 Docs](https://nextjs.org/docs)
- [wagmi Docs](https://wagmi.sh)
- [WalletConnect Cloud](https://cloud.walletconnect.com)
- [LibertAI](https://libertai.io)
