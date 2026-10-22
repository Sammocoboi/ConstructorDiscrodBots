#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
set -a
source .env
set +a

mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="backups/constructor-${stamp}.sql.gz"

docker compose exec -T db pg_dump \
    -U "${POSTGRES_USER:-constructor}" \
    -d "${POSTGRES_DB:-constructor}" \
    --clean --if-exists | gzip > "${target}"

find backups -type f -name '*.sql.gz' -mtime +14 -delete
echo "${target}"
