#!/usr/bin/env bash
# VoiceHire AI — one-command launcher (from the project root)
set -e
cd backend
if [ ! -d .venv ]; then python3 -m venv .venv; fi
./.venv/bin/pip install -q -r requirements.txt httpx
echo "Starting backend on :8000 and frontend on :5173"
./.venv/bin/uvicorn app.main:app --port 8000 &
BACK=$!
cd ../frontend
npm install --no-audit --no-fund --silent
npm run dev &
FRONT=$!
echo "VoiceHire AI: http://localhost:5173  (API docs: http://localhost:8000/docs)"
trap "kill $BACK $FRONT 2>/dev/null" INT
wait
