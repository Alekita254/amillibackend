#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/var/www/projects/amilliontechies"
BACKEND_ROOT="$PROJECT_ROOT/backend"
SERVICE_TEMPLATE="$BACKEND_ROOT/deployment/systemd/amilliontechies-backend.service.example"
NGINX_TEMPLATE="$BACKEND_ROOT/deployment/nginx/amilliontechies.conf.example"
SERVICE_TARGET="/etc/systemd/system/amilliontechies-backend.service"
NGINX_TARGET="/etc/nginx/conf.d/amilliontechies.conf"

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run with sudo" >&2
  exit 1
fi

mkdir -p /etc/systemd/system /etc/nginx/conf.d "$BACKEND_ROOT/staticfiles" "$BACKEND_ROOT/media"

install -m 644 "$SERVICE_TEMPLATE" "$SERVICE_TARGET"
install -m 644 "$NGINX_TEMPLATE" "$NGINX_TARGET"

systemctl daemon-reload
systemctl enable --now amilliontechies-backend

if command -v nginx >/dev/null 2>&1; then
  nginx -t
  systemctl reload nginx || true
fi

echo "Deployment templates installed."
echo "Next: ensure Nginx is installed, then verify the service and the nginx config."
