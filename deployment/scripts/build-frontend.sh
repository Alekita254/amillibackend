#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/var/www/projects/amilliontechies"
FRONTEND_ROOT="$PROJECT_ROOT/frontend"

cd "$FRONTEND_ROOT"
npm install
npm run build

echo "Frontend build completed."
