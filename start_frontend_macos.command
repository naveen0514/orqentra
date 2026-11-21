#!/usr/bin/env bash
cd "$(dirname "$0")/frontend" || exit 1
echo "🌐 Orqentra Frontend — starting..."
lsof -ti :5173 | xargs kill -9 2>/dev/null
if [ ! -d "node_modules" ]; then
  npm install
fi
exec npm run dev
