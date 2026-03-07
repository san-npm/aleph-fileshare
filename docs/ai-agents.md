# 🤖 AI Agents

AlephFileShare runs five autonomous AI agents on **Aleph Cloud Persistent VMs** (AMD SEV confidential computing). Agents are long-lived Python processes that communicate with the rest of the system exclusively via Aleph messages — they never call the backend API directly.

---

## Architecture Principle

Agents follow an **event-driven, message-passing architecture**:

```
┌──────────────┐   STORE message   ┌──────────────────┐
│  Backend API │ ────────────────► │  Scanner Agent   │
└──────────────┘                   └────────┬─────────┘
                                            │ Aggregate update (scan_status)
                                   ┌────────▼─────────┐
                                   │  Indexer Agent   │
                                   └────────┬─────────┘
                                            │ Aggregate update (tags, description)
                                   ┌────────▼─────────┐
                                   │ Recommender Agent│
                                   └──────────────────┘

┌──────────────────┐  (continuous)  ┌──────────────────┐
│  Guardian Agent  │ ─────────────► │ Notifier Agent   │
└──────────────────┘                └──────────────────┘
```

---

## 1. Scanner Agent (`scanner_agent.py`)

**Purpose**: Scan every uploaded file for malware and policy violations.

**Trigger**: Polls Aleph for new STORE messages in channel `ALEPH_FILESHARE` with `scan_status: pending`.

**Actions**:
1. Fetch file from IPFS gateway
2. Compute file hash (SHA-256)
3. Query VirusTotal API with the hash
4. If no result: submit the file to VirusTotal for full scan (async)
5. Update file Aggregate: `scan_status = clean | flagged | error`
6. If flagged: post an alert Aleph POST message for the Notifier Agent

**Environment variables**:
- `VIRUSTOTAL_API_KEY` — VirusTotal API key

**Aleph VM config**:
- Type: Persistent VM
- Confidential: AMD SEV-SNP
- Internet access: Yes (required for VirusTotal)

---

## 2. Indexer Agent (`indexer_agent.py`)

**Purpose**: Enrich file metadata with AI-generated tags and descriptions.

**Trigger**: Polls Aleph for file Aggregates where `scan_status = clean` and `tags = []`.

**Actions**:
1. Fetch file from IPFS gateway
2. Detect MIME type and file category
3. For documents/images: generate a description using LibertAI (Mistral 7B)
4. Generate semantic tags from filename, MIME type, and description
5. Update file Aggregate: `tags = [...]`, `description = "..."`

**LibertAI integration**:
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.libertai.io/v1",
    api_key="libertai",  # No key needed for public models
)
response = client.chat.completions.create(
    model="mistral-7b-instruct",
    messages=[{"role": "user", "content": f"Generate 5 tags for this file: {filename}"}],
)
```

**Environment variables**:
- `LIBERTAI_API_URL` — defaults to `https://api.libertai.io`
- `LLM_MODEL` — defaults to `mistral-7b-instruct`

---

## 3. Recommender Agent (`recommender_agent.py`)

**Purpose**: Suggest relevant files to users based on their access history.

**Trigger**: Polls Aleph Indexer for new download events.

**Actions**:
1. Retrieve access history for the wallet address from Aleph Indexer
2. Build a co-occurrence matrix of file hashes (collaborative filtering)
3. Score unaccessed files by similarity to the user's history
4. Write top-10 recommendations to user's Aleph Aggregate: `recommendations`
5. Exposed via `GET /api/recommendations` on the backend

**Phase**: Phase 4 (Q4 2026)

---

## 4. Guardian Agent (`guardian_agent.py`)

**Purpose**: Monitor network health and detect abuse (bots, DDOS, spam uploads).

**Trigger**: Runs on a 5-minute cron loop.

**Actions**:
1. Query Aleph for upload volume per wallet in the last hour
2. Flag wallets exceeding `UPLOAD_RATE_LIMIT` uploads/hour
3. Write abuse flags to Aleph Aggregate: `blocked_wallets`
4. Monitor Aleph node availability and write health status
5. If anomaly detected: post alert POST message for Notifier Agent

**Environment variables**:
- `ALERT_WEBHOOK_URL` — optional webhook for external alerting

**Phase**: Phase 4 (Q4 2026)

---

## 5. Notifier Agent (`notifier_agent.py`)

**Purpose**: Fan out alerts from Scanner and Guardian agents to subscribers.

**Trigger**: Polls for alert POST messages in channel `ALEPH_FILESHARE_ALERTS`.

**Actions**:
1. Parse alert type (malware detected, abuse spike, node down)
2. Fetch subscriber list from Aleph Aggregate
3. Send Aleph POST message to each subscriber's address
4. If `ALERT_WEBHOOK_URL` is set: POST to webhook with alert payload

**Phase**: Phase 4 (Q4 2026)

---

## Deploying Agents to Aleph Cloud

Agents are deployed as Aleph Cloud Persistent VM instances using the Aleph CLI:

```bash
# Login with your wallet
aleph account config --private-key $ALEPH_PRIVATE_KEY

# Deploy scanner agent
aleph instance create \
  --image <debian-12-image-hash> \
  --memory 2048 \
  --vcpus 2 \
  --storage 20 \
  --name scanner-agent
```

Once the VM is running, SSH in and run the agent as a systemd service. See [deployment.md](deployment.md) for the full procedure.
