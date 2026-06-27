#!/usr/bin/env bash
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root (use sudo)."
  exit 1
fi

EMAIL="admin@amilliontechies.com"
DOMAINS=("amilliontechies.com" "www.amilliontechies.com" "millibackend.amilliontechies.com")

apt-get update
apt-get install -y certbot python3-certbot-nginx

certbot --nginx --non-interactive --agree-tos --email "$EMAIL" \
  --domains "${DOMAINS[0]},${DOMAINS[1]},${DOMAINS[2]}" \
  --redirect \
  --expand

echo "SSL certificates installed and Nginx configured for HTTPS."
