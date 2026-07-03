#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"
PY="${ROOT_DIR}/../.venv/bin/python"
if [ ! -x "${PY}" ]; then
  PY="python3"
fi

SOAK_MINUTES="${APICRED_SOAK_MINUTES:-30}"
END_TS=$(( $(date +%s) + SOAK_MINUTES * 60 ))

echo "Starting soak test for ${SOAK_MINUTES} minutes..."
while [ "$(date +%s)" -lt "${END_TS}" ]; do
  APICRED_LOAD_REQUESTS="${APICRED_LOAD_REQUESTS:-100}" APICRED_LOAD_CONCURRENCY="${APICRED_LOAD_CONCURRENCY:-10}" \
    "${PY}" "scripts/apicred_load_test.py" > /tmp/apicred_soak_latest.json
  sleep 2
done

cat /tmp/apicred_soak_latest.json | tee "reports/13-standalone-load-soak-report.md"
