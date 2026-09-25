#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/var/www/projects/amilliontechies"
FRONTEND_ROOT="$PROJECT_ROOT/frontend"

cd "$FRONTEND_ROOT"

if [ ! -d node_modules ]; then
  npm install
fi

npm run build

echo "Frontend build completed. Static files are in $FRONTEND_ROOT/dist"
