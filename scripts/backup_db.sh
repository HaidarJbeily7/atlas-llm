#!/usr/bin/env bash
#
# backup_db.sh — Create a local backup of the ATLAS PostgreSQL database.
#
# Supports both local and Fly.io remote databases.
#
# Usage:
#   ./scripts/backup_db.sh                          # auto-detect from .env
#   ./scripts/backup_db.sh --fly atlas-llm-db       # backup from Fly.io app
#   ./scripts/backup_db.sh --url postgres://...      # explicit connection URL
#
set -euo pipefail

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/atlas_db_${TIMESTAMP}.sql.gz"
FLY_APP=""
DB_URL=""

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --fly)
            FLY_APP="$2"
            shift 2
            ;;
        --url)
            DB_URL="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--fly <fly-app-name>] [--url <postgres-url>]"
            echo ""
            echo "Options:"
            echo "  --fly APP    Backup from a Fly.io Postgres app via proxy"
            echo "  --url URL    Use explicit PostgreSQL connection URL"
            echo "  (default)    Read DATABASE_URL from annotation_platform/backend/.env"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

mkdir -p "$BACKUP_DIR"

# Find the newest pg_dump available (Homebrew installs versioned ones)
PG_DUMP="pg_dump"
for v in 17 16 15; do
    candidate="/opt/homebrew/opt/postgresql@${v}/bin/pg_dump"
    if [[ -x "$candidate" ]]; then
        PG_DUMP="$candidate"
        break
    fi
done
echo "Using: $PG_DUMP ($($PG_DUMP --version 2>/dev/null || echo 'unknown'))"

# ── Fly.io backup ──
if [[ -n "$FLY_APP" ]]; then
    echo "Backing up from Fly.io app: ${FLY_APP}"
    echo "  Starting proxy on localhost:15432..."

    # Start proxy in background
    flyctl proxy 15432:5432 -a "$FLY_APP" &
    PROXY_PID=$!
    sleep 3

    # Get credentials from Fly secrets
    echo "  Dumping database..."
    $PG_DUMP "postgres://postgres:$(flyctl ssh console -a "$FLY_APP" -C 'echo $OPERATOR_PASSWORD' 2>/dev/null)@localhost:15432/atlas" \
        --no-owner --no-privileges --clean --if-exists \
        | gzip > "$BACKUP_FILE"

    kill $PROXY_PID 2>/dev/null || true

# ── Explicit URL ──
elif [[ -n "$DB_URL" ]]; then
    echo "Backing up from: ${DB_URL%%@*}@..."
    $PG_DUMP "$DB_URL" --no-owner --no-privileges --clean --if-exists \
        | gzip > "$BACKUP_FILE"

# ── Auto-detect from .env ──
else
    ENV_FILE="annotation_platform/backend/.env"
    if [[ ! -f "$ENV_FILE" ]]; then
        echo "ERROR: No .env found at $ENV_FILE and no --url or --fly specified" >&2
        exit 1
    fi

    DB_URL=$(grep -E '^DATABASE_URL=' "$ENV_FILE" | cut -d= -f2-)
    if [[ -z "$DB_URL" ]]; then
        echo "ERROR: DATABASE_URL not found in $ENV_FILE" >&2
        exit 1
    fi

    echo "Backing up from .env DATABASE_URL..."
    $PG_DUMP "$DB_URL" --no-owner --no-privileges --clean --if-exists \
        | gzip > "$BACKUP_FILE"
fi

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo ""
echo "Backup saved: ${BACKUP_FILE} (${SIZE})"
echo ""
echo "To restore:"
echo "  gunzip -c ${BACKUP_FILE} | psql \$DATABASE_URL"
