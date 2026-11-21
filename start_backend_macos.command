#!/usr/bin/env bash
cd "$(dirname "$0")/backend" || exit 1
echo "🔧 Orqentra Backend — starting..."
lsof -ti :8000 | xargs kill -9 2>/dev/null
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt 2>/dev/null
PYTHONPATH="$(pwd)" exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
