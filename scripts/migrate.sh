#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_DIR="$ROOT/packages/db"
VENV="$DB_DIR/.venv"

# Create venv and install db package if not already done
if [[ ! -f "$VENV/bin/alembic" ]]; then
    echo "==> Installing packages/db into $VENV"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet -e "$DB_DIR" python-dotenv
fi

# Load .env and rewrite docker hostname → localhost for local execution
if [[ -f "$ROOT/.env" ]]; then
    set -o allexport
    source "$ROOT/.env"
    set +o allexport
fi
# Replace Docker service hostname+port with localhost:5433 (dev overlay maps 5433→5432)
export DATABASE_URL="${DATABASE_URL//@db:5432/@localhost:5433}"

cd "$DB_DIR"
"$VENV/bin/alembic" upgrade head
