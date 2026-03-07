#!/usr/bin/env bash
# deploy.sh — Deploy AlephFileShare to Aleph Cloud
set -euo pipefail

echo "🚀 Deploying AlephFileShare to Aleph Cloud..."

# Load environment
if [ ! -f .env ]; then
  echo "❌ .env file not found. Copy .env.example and fill in your values."
  exit 1
fi
set -a && source .env && set +a

# Check Aleph CLI
command -v aleph >/dev/null 2>&1 || { echo "❌ aleph CLI not found. Run: pip install aleph-client"; exit 1; }

# --- Deploy Backend ---
echo "📦 Building backend package..."
mkdir -p dist
cd backend
zip -r ../dist/backend.zip src/ requirements.txt
cd ..

echo "☁️  Uploading backend as Aleph Serverless Function..."
BACKEND_HASH=$(aleph program upload \
  --path dist/backend.zip \
  --entrypoint src.main:app \
  --runtime python3.11 \
  --memory 512 \
  --channel "${ALEPH_CHANNEL:-ALEPH_FILESHARE}" \
  --output json | jq -r '.item_hash')

echo "✅ Backend deployed: https://${BACKEND_HASH}.aleph.run"

# --- Deploy Frontend ---
echo "🏗️  Building Next.js frontend..."
cd frontend
NEXT_PUBLIC_API_URL="https://${BACKEND_HASH}.aleph.run" npm run build

echo "☁️  Publishing frontend to Aleph Static Hosting..."
FRONTEND_URL=$(aleph website publish \
  --path out/ \
  --channel "${ALEPH_CHANNEL:-ALEPH_FILESHARE}" \
  --output json | jq -r '.url')
cd ..

echo ""
echo "🎉 Deployment complete!"
echo "   Frontend: ${FRONTEND_URL}"
echo "   Backend:  https://${BACKEND_HASH}.aleph.run"
echo "   API Docs: https://${BACKEND_HASH}.aleph.run/docs"
