#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PY="${ROOT_DIR}/../.venv/bin/python"
if [ ! -x "${PY}" ]; then
  PY="python3"
fi
"${PY}" "scripts/apicred_load_test.py" | tee "reports/13-standalone-load-soak-report.md"
