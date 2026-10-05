#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
umask 077
mkdir -p backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker compose --env-file server/.env exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "backups/database-$stamp.dump"
cp server/.env "backups/config-$stamp.env"
echo "备份完成：backups/database-$stamp.dump 和 config-$stamp.env"
