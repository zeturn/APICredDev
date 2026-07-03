#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}/backend"

pytest
alembic upgrade head
python -m app.cli secrets rotate-provider-credentials --dry-run
python -m app.cli quota reconcile --dry-run
python -m app.cli audit purge-expired --dry-run
