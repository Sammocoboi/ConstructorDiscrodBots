#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
archive="${1:?usage: restore.sh <backup.dump>}"

if [ ! -f "$archive" ]; then
    echo "backup not found: $archive" >&2
    exit 1
fi

echo "WARNING: this replaces the current database contents." >&2
echo "Stop backend/runtime before restoring a production database." >&2

pg_restore --clean --if-exists --no-owner --no-privileges \
    --dbname="$DATABASE_URL" "$archive"

echo "restore finished: $archive"
