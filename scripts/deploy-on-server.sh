#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/ai-engineer-portal
REPO_URL=${REPO_URL:-https://github.com/stinger0962/AIEngineerPortal.git}
DEPLOY_REF=${DEPLOY_REF:-main}

mkdir -p "$APP_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

git fetch --all --tags --prune
git checkout "$DEPLOY_REF"
git reset --hard "$DEPLOY_REF"

if [ ! -f infra/.env.production ]; then
  echo "Missing infra/.env.production"
  exit 1
fi

docker compose --env-file infra/.env.production -f infra/docker-compose.prod.yml up -d --build --force-recreate --remove-orphans
