#!/bin/bash
# Wrapper script for scheduled photo_ref maintenance.
#
# Default behavior:
# 1) Run refresh_photo_refs in dry-run mode to detect stale photo refs.
# 2) Run the real refresh only if updates are needed.
#
# Usage examples:
#   ./refresh_photo_refs.sh
#   ./refresh_photo_refs.sh --limit 50 --verbose
#   COMPOSE_FILE=docker-compose.yml ./refresh_photo_refs.sh

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
SERVICE_NAME="${SERVICE_NAME:-web}"
LOG_DIR="${LOG_DIR:-}"
LOCK_FILE="${LOCK_FILE:-/tmp/directory_factory_refresh_photo_refs.lock}"
REFRESH_ARGS=()

print_usage() {
    cat <<'EOF'
Usage: ./refresh_photo_refs.sh [OPTIONS]

Options:
  --limit N           Process only first N listings
  --verbose           Show detailed listing-level output
  --compose-file FILE Docker compose file (default: docker-compose.prod.yml)
  --service NAME      Compose service name (default: web)
  --log-dir DIR       Log directory (default: ./logs)
  --help, -h          Show this help

Environment overrides:
  COMPOSE_FILE, SERVICE_NAME, LOG_DIR, LOCK_FILE
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --limit)
            if [[ $# -lt 2 ]]; then
                echo "Missing value for --limit"
                exit 1
            fi
            REFRESH_ARGS+=("--limit" "$2")
            shift 2
            ;;
        --verbose)
            REFRESH_ARGS+=("--verbose")
            shift
            ;;
        --compose-file)
            if [[ $# -lt 2 ]]; then
                echo "Missing value for --compose-file"
                exit 1
            fi
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --service)
            if [[ $# -lt 2 ]]; then
                echo "Missing value for --service"
                exit 1
            fi
            SERVICE_NAME="$2"
            shift 2
            ;;
        --log-dir)
            if [[ $# -lt 2 ]]; then
                echo "Missing value for --log-dir"
                exit 1
            fi
            LOG_DIR="$2"
            shift 2
            ;;
        --help|-h)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
elif command -v docker >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
else
    echo "Neither docker-compose nor docker is available on PATH"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -z "$LOG_DIR" ]]; then
    LOG_DIR="$SCRIPT_DIR/logs"
fi

mkdir -p "$LOG_DIR"
TIMESTAMP="$(date +%F_%H-%M-%S)"
LOG_FILE="$LOG_DIR/refresh_photo_refs_${TIMESTAMP}.log"

# Log both stdout and stderr to a rotating, timestamped file.
exec > >(tee -a "$LOG_FILE") 2>&1

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "[$(date -Is)] Another refresh_photo_refs job is already running. Exiting."
    exit 0
fi

MANAGE_CMD=("${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" python manage.py refresh_photo_refs)

echo "[$(date -Is)] Starting photo_ref stale-check"
echo "[$(date -Is)] Compose file: $COMPOSE_FILE"
echo "[$(date -Is)] Service: $SERVICE_NAME"

tmp_output="$(mktemp)"
trap 'rm -f "$tmp_output"' EXIT

# Dry run first to detect if there is anything to update.
"${MANAGE_CMD[@]}" --dry-run --no-color "${REFRESH_ARGS[@]}" | tee "$tmp_output"

updated_count="$(grep -Eo 'Updated:[[:space:]]*[0-9]+' "$tmp_output" | tail -n 1 | grep -Eo '[0-9]+' || true)"
updated_count="${updated_count:-0}"

if [[ "$updated_count" =~ ^[0-9]+$ ]] && (( updated_count > 0 )); then
    echo "[$(date -Is)] Detected $updated_count outdated photo refs. Running refresh."
    "${MANAGE_CMD[@]}" --no-color "${REFRESH_ARGS[@]}"
    echo "[$(date -Is)] Refresh run completed."
else
    echo "[$(date -Is)] No outdated photo refs detected. Nothing to update."
fi

echo "[$(date -Is)] Log file: $LOG_FILE"
