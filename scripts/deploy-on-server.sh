#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/ai-engineer-portal
REPO_URL=${REPO_URL:-https://github.com/stinger0962/AIEngineerPortal.git}
DEPLOY_REF=${DEPLOY_REF:-main}
ENV_FILE=infra/.env.production
ENV_BACKUP=/tmp/ai-engineer-portal.env.production

mkdir -p "$APP_DIR"

if [ -f "$APP_DIR/$ENV_FILE" ]; then
  cp "$APP_DIR/$ENV_FILE" "$ENV_BACKUP"
fi

if [ ! -d "$APP_DIR/.git" ]; then
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_BACKUP" ]; then
  mkdir -p "$(dirname "$ENV_FILE")"
  cp "$ENV_BACKUP" "$ENV_FILE"
fi

# Remove any stale GitHub Actions tokens injected by actions/checkout.
# These expire immediately and block git fetch on public repos.
git config --unset-all http.https://github.com/.extraheader 2>/dev/null || true

git fetch --all --tags --prune
git checkout "$DEPLOY_REF"
git reset --hard "$DEPLOY_REF"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE"
  exit 1
fi

docker compose --env-file "$ENV_FILE" -f infra/docker-compose.prod.yml up -d --build --force-recreate --remove-orphans
