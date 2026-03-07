# ⚙️ Configuration Reference

All configuration is done via environment variables. Copy `.env.example` to `.env` and fill in your values.

Variables prefixed with `NEXT_PUBLIC_` are **exposed to the browser** — never put secrets in them.

---

## Aleph Cloud

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALEPH_PRIVATE_KEY` | ✅ | — | EVM wallet private key used to sign Aleph messages. Never share this. |
| `ALEPH_API_SERVER` | — | `https://api1.aleph.im` | Aleph API node URL. Change if you want a specific node. |
| `ALEPH_CHANNEL` | — | `ALEPH_FILESHARE` | Channel namespace for all Aleph messages. Change to isolate envs (e.g., `ALEPH_FILESHARE_DEV`). |
| `ALEPH_STORAGE_ENGINE` | — | `ipfs` | Storage engine: `ipfs` or `storage`. Use `ipfs` for public files. |

---

## Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BACKEND_SECRET` | ✅ | — | Random secret used for internal HMAC signing. Generate with `openssl rand -hex 32`. |
| `MAX_FILE_SIZE_BYTES` | — | `2147483648` | Maximum upload size in bytes. Default is 2 GB. |
| `ALLOWED_MIME_TYPES` | — | `""` (allow all) | Comma-separated list of allowed MIME types. Empty string allows all types. Example: `image/jpeg,application/pdf`. |
| `CORS_ORIGINS` | — | `http://localhost:3000` | Comma-separated list of allowed CORS origins. |

---

## Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | ✅ | `http://localhost:8000` | Public URL of the backend API. In production, set to your Aleph serverless function URL. |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | ✅ | — | WalletConnect v2 Project ID. Get one free at [cloud.walletconnect.com](https://cloud.walletconnect.com). |
| `NEXT_PUBLIC_APP_NAME` | — | `AlephFileShare` | App name shown in wallet connection dialogs. |

---

## AI Agents

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LIBERTAI_API_URL` | — | `https://api.libertai.io` | LibertAI inference API endpoint. Default uses the public Aleph-hosted instance. |
| `VIRUSTOTAL_API_KEY` | Phase 2+ | — | VirusTotal API key for the Scanner Agent. Get a free key at [virustotal.com](https://www.virustotal.com). |
| `LLM_MODEL` | — | `mistral-7b-instruct` | LLM model name for the Indexer Agent. Must be a model available on LibertAI. |

---

## Monitoring

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALERT_WEBHOOK_URL` | — | `""` | Webhook URL for Guardian Agent and Scanner Agent alerts. Compatible with Slack, Discord, or any HTTP POST endpoint. |
| `LOG_LEVEL` | — | `INFO` | Logging verbosity. Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Use `DEBUG` during development. |

---

## Example `.env` for Local Development

```env
# Aleph Cloud
ALEPH_PRIVATE_KEY=0xyour_dev_wallet_private_key
ALEPH_API_SERVER=https://api1.aleph.im
ALEPH_CHANNEL=ALEPH_FILESHARE_DEV
ALEPH_STORAGE_ENGINE=ipfs

# Backend
BACKEND_SECRET=dev_secret_replace_in_production
MAX_FILE_SIZE_BYTES=104857600
CORS_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_walletconnect_id

# AI Agents
LIBERTAI_API_URL=https://api.libertai.io
LLM_MODEL=mistral-7b-instruct

# Monitoring
LOG_LEVEL=DEBUG
```

> 💡 Use `ALEPH_CHANNEL=ALEPH_FILESHARE_DEV` in development to avoid polluting the production channel with test data.
