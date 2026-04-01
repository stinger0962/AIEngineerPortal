#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL backup script for AI Engineer Portal
# Run via cron: 0 3 * * * /opt/ai-engineer-portal/scripts/backup-db.sh

BACKUP_DIR="/opt/ai-engineer-portal/backups"
COMPOSE_FILE="/opt/ai-engineer-portal/infra/docker-compose.prod.yml"
ENV_FILE="/opt/ai-engineer-portal/infra/.env.production"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Load env vars
set -a
source "$ENV_FILE"
set +a

# Dump database
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --format=custom \
  > "${BACKUP_DIR}/portal_${DATE}.dump"

# Verify backup is not empty
BACKUP_SIZE=$(stat -c%s "${BACKUP_DIR}/portal_${DATE}.dump" 2>/dev/null || echo "0")
if [ "$BACKUP_SIZE" -lt 1000 ]; then
  echo "ERROR: Backup file is suspiciously small (${BACKUP_SIZE} bytes)"
  exit 1
fi

echo "Backup created: portal_${DATE}.dump (${BACKUP_SIZE} bytes)"

# Clean old backups
find "$BACKUP_DIR" -name "portal_*.dump" -mtime +${RETENTION_DAYS} -delete
echo "Cleaned backups older than ${RETENTION_DAYS} days"
