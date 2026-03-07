#!/usr/bin/env bash
# test.sh — Run all tests
set -euo pipefail

echo "🧪 Running AlephFileShare tests..."

EXIT_CODE=0

# --- Backend tests ---
if [ -d backend ]; then
  echo "\n🐍 Running backend tests..."
  cd backend
  if python -m pytest --tb=short -q; then
    echo "✅ Backend tests passed."
  else
    echo "❌ Backend tests failed."
    EXIT_CODE=1
  fi
  cd ..
fi

# --- Frontend tests ---
if [ -d frontend ]; then
  echo "\n⚛️  Running frontend tests..."
  cd frontend
  if npm run test -- --passWithNoTests; then
    echo "✅ Frontend tests passed."
  else
    echo "❌ Frontend tests failed."
    EXIT_CODE=1
  fi
  cd ..
fi

# --- Agent tests ---
if [ -d agents ]; then
  echo "\n🤖 Running agent tests..."
  cd agents
  if python -m pytest --tb=short -q; then
    echo "✅ Agent tests passed."
  else
    echo "❌ Agent tests failed."
    EXIT_CODE=1
  fi
  cd ..
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
  echo "🎉 All tests passed!"
else
  echo "💥 Some tests failed. See output above."
fi

exit $EXIT_CODE
