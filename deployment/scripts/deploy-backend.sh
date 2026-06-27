#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/var/www/projects/amilliontechies"
BACKEND_ROOT="$PROJECT_ROOT/backend"

source "$BACKEND_ROOT/venv/bin/activate"
pip install --upgrade pip
pip install -r "$BACKEND_ROOT/requirements.txt"

cd "$BACKEND_ROOT/backend"

python manage.py migrate
python manage.py collectstatic --noinput

echo "Backend migrations and static files completed."
