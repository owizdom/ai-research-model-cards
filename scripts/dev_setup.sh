#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/packages/db/.venv"

echo "==> Copying .env.example → .env"
[[ -f "$ROOT/.env" ]] || cp "$ROOT/.env.example" "$ROOT/.env"

echo "==> Starting DB + Redis"
docker compose -f "$ROOT/infra/compose/docker-compose.yml" \
               -f "$ROOT/infra/compose/docker-compose.dev.yml" \
               up -d db redis

echo "==> Waiting for DB to be ready..."
until docker compose -f "$ROOT/infra/compose/docker-compose.yml" \
      exec -T db pg_isready -U policy 2>/dev/null; do
    sleep 1
done

echo "==> Running migrations"
bash "$ROOT/scripts/migrate.sh"

echo "==> Seeding DB"
"$VENV/bin/pip" install --quiet pyyaml python-dotenv

# Use localhost URL for host-side seed script
if [[ -f "$ROOT/.env" ]]; then
    set -o allexport; source "$ROOT/.env"; set +o allexport
fi
DATABASE_URL="${DATABASE_URL//@db:5432/@localhost:5433}" \
    "$VENV/bin/python" "$ROOT/scripts/seed_db.py"

echo ""
echo "Done. Start all services:"
echo "  docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.dev.yml up"
