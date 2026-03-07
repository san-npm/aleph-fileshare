# 🚢 Deployment Guide

This guide covers deploying AlephFileShare to Aleph Cloud (production).

---

## Prerequisites

- Aleph CLI installed: `pip install aleph-client`
- Wallet funded with ALEPH tokens (≥ 2000 ALEPH recommended)
- `.env` file configured (copy from `.env.example`)

---

## Overview

| Service | Aleph Cloud Service | Command |
|---------|--------------------|---------|
| Frontend | Static Hosting (IPFS) | `aleph website publish` |
| Backend API | Serverless Function | `aleph program upload` |
| AI Agents | Persistent VM | `aleph instance create` |

---

## 1. Deploy the Backend (Serverless Function)

The backend runs as an Aleph Cloud Serverless Function — a stateless Python process invoked per-request.

```bash
cd backend

# Build the deployment package
zip -r ../dist/backend.zip src/ requirements.txt

# Upload to Aleph
aleph program upload \
  --path ../dist/backend.zip \
  --entrypoint src.main:app \
  --runtime python3.11 \
  --memory 512 \
  --channel ALEPH_FILESHARE
```

Note the returned **program hash** — you'll need it for the frontend `NEXT_PUBLIC_API_URL`.

The backend will be available at:
```
https://{program-hash}.aleph.run
```

---

## 2. Deploy the Frontend (Static Hosting)

The frontend is a Next.js static export deployed to Aleph IPFS hosting.

```bash
cd frontend

# Set production API URL
export NEXT_PUBLIC_API_URL=https://{your-program-hash}.aleph.run

# Build static export
npm run build

# Deploy to Aleph static hosting
aleph website publish \
  --path out/ \
  --channel ALEPH_FILESHARE
```

Your frontend will be available at:
```
https://{ipfs-cid-v1}.ipfs.aleph.sh
```

### Custom Domain (Optional)

To use a custom domain, configure a CNAME record pointing to `aleph.sh` and update your domain settings in the [Aleph Cloud Console](https://console.aleph.cloud).

### ENS Domain (Optional)

Set the `Content Hash` record in your ENS domain to `ipfs://{ipfs-cid-v1}`. Your dApp will then be accessible at `https://yourdomain.eth.limo`.

---

## 3. Deploy AI Agents (Persistent VMs)

> AI agents are required for Phase 2+ only. Skip this section for the Phase 1 MVP.

### Create the VM instance

```bash
# Login
aleph account config --private-key $ALEPH_PRIVATE_KEY

# Create a persistent VM (AMD SEV confidential)
aleph instance create \
  --image <debian-12-image-hash> \
  --memory 4096 \
  --vcpus 2 \
  --storage 40 \
  --name aleph-fileshare-agents
```

### Install and configure agents on the VM

```bash
# SSH into the VM
ssh user@<vm-ip>

# Clone the repo
git clone https://github.com/san-npm/aleph-fileshare.git
cd aleph-fileshare/agents

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp ../.env.example .env
# Edit .env with your values
```

### Run agents as systemd services

Create `/etc/systemd/system/scanner-agent.service`:

```ini
[Unit]
Description=AlephFileShare Scanner Agent
After=network.target

[Service]
Type=simple
User=aleph
WorkingDirectory=/home/aleph/aleph-fileshare/agents
ExecStart=/usr/bin/python3 src/scanner_agent.py
Restart=always
RestartSec=10
EnvironmentFile=/home/aleph/aleph-fileshare/.env

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable scanner-agent
systemctl start scanner-agent
systemctl status scanner-agent
```

Repeat for `indexer_agent`, `recommender_agent`, `guardian_agent`, `notifier_agent` when ready.

---

## 4. Deploy Everything with One Command

The `deploy.sh` script automates all three steps above:

```bash
bash scripts/deploy.sh
```

This script:
1. Builds the backend zip
2. Uploads backend as Aleph serverless function
3. Builds Next.js frontend with production API URL
4. Publishes frontend to Aleph static hosting
5. Prints the final frontend and backend URLs

---

## 5. Verify Deployment

```bash
# Check backend health
curl https://{program-hash}.aleph.run/health

# Should return:
# {"status": "ok", "version": "0.1.0", "aleph_connected": true}
```

Then open the frontend URL in your browser and test a file upload end-to-end.

---

## Updating a Deployment

### Backend update

```bash
cd backend
zip -r ../dist/backend.zip src/ requirements.txt
aleph program upload --path ../dist/backend.zip --entrypoint src.main:app
# New hash is generated — update NEXT_PUBLIC_API_URL in frontend if needed
```

### Frontend update

```bash
cd frontend
npm run build
aleph website publish --path out/
# New IPFS CID is generated — update custom domain CNAME if needed
```

---

## Useful Links

- [Aleph Cloud Console](https://console.aleph.cloud)
- [Aleph CLI Docs](https://docs.aleph.cloud/devhub/sdks-and-tools/aleph-cli/)
- [Aleph Static Hosting Docs](https://docs.aleph.cloud/devhub/deploying-and-hosting/web-hosting/)
- [Aleph Serverless Functions](https://docs.aleph.cloud/devhub/deploying-and-hosting/serverless/)
- [Aleph Persistent VMs](https://docs.aleph.cloud/devhub/deploying-and-hosting/persistent-vms/)
