# 06 APICred Hardening Smoke Report

## Script

已新增：`scripts/apicred-hardening-smoke.sh`

执行顺序：

1. `cd backend`
2. `pytest`
3. `alembic upgrade head`
4. `python -m app.cli secrets rotate-provider-credentials --dry-run`
5. `python -m app.cli quota reconcile --dry-run`
6. `python -m app.cli audit purge-expired --dry-run`

## Verification Snapshot

- `pytest`：通过（`111 passed, 3 skipped`）。
- `docker compose config --quiet`：通过。
- `alembic upgrade head`：通过（本次在本地 sqlite smoke 库 `tmp_apicred.db` 验证 migration 链路）。
- 三个 CLI dry-run：通过并返回结构化 JSON。

## Result

- `apicred_hardening_smoke_ready = true`
- `production_config_guard_ready = true`
- `secret_rotation_ready = true`
- `quota_ledger_ready = true`
- `provider_health_ready = true`
- `audit_privacy_ready = true`
