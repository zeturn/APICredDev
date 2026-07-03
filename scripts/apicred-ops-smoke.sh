#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="${ROOT_DIR}/../.venv/bin/python"
VENV_ALEMBIC="${ROOT_DIR}/../.venv/bin/alembic"
SQLITE_DB_URL="sqlite+aiosqlite:///./tmp_apicred_ops_smoke.db"

cd "${ROOT_DIR}/backend"
APP_SECRET="dev-secret" \
TOKEN_SALT="dev-token-salt" \
ALLOW_LOCAL_PASSWORD_AUTH="false" \
STARTUP_CREATE_TABLES_ENABLED="false" \
STARTUP_SCHEMA_COMPAT_ENABLED="false" \
STARTUP_BOOTSTRAP_ENABLED="false" \
PYTHONPATH="${ROOT_DIR}/backend" "${VENV_PY}" -m pytest "${ROOT_DIR}/backend/tests"
rm -f tmp_apicred_ops_smoke.db
DATABASE_URL="${SQLITE_DB_URL}" PYTHONPATH="${ROOT_DIR}/backend" "${VENV_ALEMBIC}" -c alembic.ini upgrade head
DATABASE_URL="${SQLITE_DB_URL}" PYTHONPATH="${ROOT_DIR}/backend" "${VENV_PY}" -m app.cli secrets rotate-provider-credentials --dry-run
DATABASE_URL="${SQLITE_DB_URL}" PYTHONPATH="${ROOT_DIR}/backend" "${VENV_PY}" -m app.cli quota reconcile --dry-run
DATABASE_URL="${SQLITE_DB_URL}" PYTHONPATH="${ROOT_DIR}/backend" "${VENV_PY}" -m app.cli audit purge-expired --dry-run
DATABASE_URL="${SQLITE_DB_URL}" PYTHONPATH="${ROOT_DIR}/backend" "${VENV_PY}" -m app.cli providers health-check --all --dry-run
DATABASE_URL="${SQLITE_DB_URL}" PYTHONPATH="${ROOT_DIR}/backend" "${VENV_PY}" -m app.cli providers benchmark --public-model apicred-fast --runs 1 --dry-run
cd "${ROOT_DIR}"
docker compose config --quiet

if [ -f "scripts/apicred-load-test.sh" ]; then
  APICRED_LOAD_CONCURRENCY=5 APICRED_LOAD_REQUESTS=50 scripts/apicred-load-test.sh || true
fi
