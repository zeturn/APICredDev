# APICred Standalone Hardening Readiness

## Summary

apicred_standalone_hardening_ready: true

## Implemented

- Production config guard
- Explicit encryption key / rotation
- Durable quota ledger
- Provider health / failover
- Audit privacy / retention

## Tests

| Area | Status | Notes |
|---|---|---|
| Production config guard | PASS | `test_production_config_guard.py` |
| Secret encryption & rotation | PASS | `test_secret_encryption_rotation.py` |
| Durable quota ledger | PASS | `test_quota_ledger.py`, `test_quota_reconciliation.py` |
| Provider contract | PASS | `tests/providers/test_provider_contract_*` |
| Route failover | PASS | `test_route_failover.py` |
| Audit privacy/retention | PASS | `test_audit_redaction_retention.py` |
| Full backend pytest | PASS | `111 passed, 3 skipped` |
| Alembic upgrade head | PASS | migration chain succeeded |
| Docker compose config | PASS | `docker compose config --quiet` succeeded |

## Migration Files

- `backend/alembic/versions/0004_apicred_hardening_features.py`

## CLI Commands

- `python -m app.cli secrets rotate-provider-credentials --dry-run`
- `python -m app.cli secrets rotate-provider-credentials`
- `python -m app.cli quota reconcile --dry-run`
- `python -m app.cli quota reconcile`
- `python -m app.cli providers health-check --provider openai --credential-id ...`
- `python -m app.cli providers health-check --all`
- `python -m app.cli audit purge-expired --dry-run`
- `python -m app.cli audit purge-expired`

## APIs

- `GET /v1/admin/quota/usage`
- `GET /v1/admin/quota/ledger`
- `POST /v1/admin/provider-credentials/{id}/health-check`
- `GET /v1/admin/provider-credentials/{id}/health`

## Security Notes

- provider secrets never printed
- audit redaction enabled
- production unsafe config rejected

## Known Limitations

- 本地 smoke 的 `alembic upgrade head` 使用 sqlite 临时库验证迁移链路；生产仍建议按 Postgres 执行同命令。
- Redis 依赖测试在无本地 Redis 时会被 `skip`（不影响核心硬化用例通过）。

## Next Steps

- 在目标生产/预发 Postgres 上执行一次 `alembic upgrade head`。
- 在真实 provider 凭证上执行一次 `providers health-check --all` 并观察 health_state 演进。
- 将 `scripts/apicred-hardening-smoke.sh` 接入 CI 定时任务。
