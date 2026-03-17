#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/ai-engineer-portal

mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ ! -f infra/.env.production ]; then
  echo "Missing infra/.env.production"
  exit 1
fi

docker compose --env-file infra/.env.production -f infra/docker-compose.prod.yml up -d --build
