#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 backups/constructor-YYYYmmddTHHMMSSZ.sql.gz" >&2
    exit 2
fi

cd "$(dirname "$0")"
set -a
source .env
set +a

dump="$1"
if [[ ! -f "${dump}" ]]; then
    echo "backup not found: ${dump}" >&2
    exit 2
fi

echo "This will replace the current database. Press Ctrl+C to cancel."
sleep 5

gunzip -c "${dump}" | docker compose exec -T db psql \
    -U "${POSTGRES_USER:-constructor}" \
    -d "${POSTGRES_DB:-constructor}" \
    -v ON_ERROR_STOP=1
