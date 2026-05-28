#!/usr/bin/env bash
# OdooERP Kenya — Setup Helper Script
# Usage: bash scripts/setup.sh
set -euo pipefail

echo "Setting up OdooERP Kenya..."

# Check requirements
command -v docker >/dev/null 2>&1 || { echo "Docker required. Install: https://docs.docker.com/get-docker/"; exit 1; }
command -v git    >/dev/null 2>&1 || { echo "Git required."; exit 1; }

# Setup env
[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example — edit with your credentials"; }

# Start services
docker compose up -d
echo "Waiting for Odoo to start..."
sleep 20

echo ""
echo "Setup complete!"
echo "  URL:      http://localhost:8069"
echo "  Database: odoo_kenya"
echo "  Login:    admin / admin"
echo ""
echo "Edit .env to configure M-Pesa Daraja credentials"
