#!/usr/bin/env bash
# setup.sh — Install all project dependencies
set -euo pipefail

echo "🔧 Setting up AlephFileShare development environment..."

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.11+ is required."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js 18+ is required."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required."; exit 1; }

# Copy .env if not present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "📋 .env created from .env.example — please fill in your values."
fi

# Backend
echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Frontend
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Agents
if [ -d agents ]; then
  echo "📦 Installing agent dependencies..."
  cd agents
  pip install -r requirements.txt
  cd ..
fi

echo "✅ Setup complete! Run 'docker-compose up --build' to start the stack."
