#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/var/www/projects/amilliontechies"
DEPLOYMENT_ROOT="$PROJECT_ROOT/backend/deployment"

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root (use sudo)."
  exit 1
fi

install -m 0644 "$DEPLOYMENT_ROOT/systemd/amilliontechies-backend.service.example" /etc/systemd/system/amilliontechies-backend.service
install -m 0644 "$DEPLOYMENT_ROOT/nginx/amilliontechies.conf.example" /etc/nginx/conf.d/amilliontechies.conf

systemctl daemon-reload
systemctl enable amilliontechies-backend.service

echo "Deployment templates installed."
