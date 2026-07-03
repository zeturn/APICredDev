# 01 Production Config Guard Report

## Scope

已扩展 `validate_production_settings`，覆盖生产模式下的关键安全配置校验，并新增测试 `backend/tests/test_production_config_guard.py`。

## Implemented

- 新增/纳入校验项：
  - `ENCRYPTION_KEY`（兼容 `APICRED_ENCRYPTION_KEY`）
  - `PRODUCTION_MODE`
  - `DEBUG_ENDPOINTS_ENABLED`
  - `STARTUP_CREATE_TABLES_ENABLED`
  - `STARTUP_SCHEMA_COMPAT_ENABLED`
  - `STARTUP_BOOTSTRAP_ENABLED`
  - `ALLOW_LOCAL_PASSWORD_AUTH`
  - `ALLOW_TEST_CLI_LOCAL_AUTH`
  - `CORS_ORIGINS`
  - `DATABASE_URL`
  - `REDIS_URL`
  - `APP_SECRET`
  - `TOKEN_SALT`
  - `ADMIN_PASSWORD`
- `PRODUCTION_MODE=true` 时拒绝：
  - `APP_SECRET=dev-secret`
  - `TOKEN_SALT=dev-token-salt`
  - debug/bootstrap/create_tables/schema_compat/test_cli_local_auth 开关开启
  - wildcard CORS
  - 空 `ADMIN_PASSWORD` / `DATABASE_URL` / `REDIS_URL` / `ENCRYPTION_KEY`
  - `ALLOW_LOCAL_PASSWORD_AUTH=true` 且未显式允许（`production_allow_local_password_auth=true`）

## Verification

- 测试：`backend/tests/test_production_config_guard.py`
- 在全量 `pytest` 中通过（见 smoke 汇总报告）。

## Result

- `production_config_guard_ready = true`
- `all unsafe production configs rejected = true`
- `dev config still works = true`
