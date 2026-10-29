#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_INTERVAL="${BACKUP_INTERVAL:-86400}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"

while true; do
    timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
    target="$BACKUP_DIR/constructor-$timestamp.dump"
    if pg_dump --format=custom --no-owner --no-privileges \
        --dbname="$DATABASE_URL" --file="$target"; then
        sha256sum "$target" > "$target.sha256"
        find "$BACKUP_DIR" -type f -name 'constructor-*.dump' \
            -mtime +"$BACKUP_RETENTION_DAYS" -delete
        find "$BACKUP_DIR" -type f -name 'constructor-*.dump.sha256' \
            -mtime +"$BACKUP_RETENTION_DAYS" -delete
        echo "backup written: $target"
    else
        echo "backup failed; removing partial file" >&2
        rm -f "$target" "$target.sha256"
    fi
    sleep "$BACKUP_INTERVAL"
done
