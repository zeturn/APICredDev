# 04 Provider Health / Failover Report

## Scope

增强 provider contract、route failover 测试与 provider credential 健康探测能力。

## Implemented

- Provider contract tests：
  - `backend/tests/providers/test_provider_contract_openai_compat.py`
  - `backend/tests/providers/test_provider_contract_anthropic.py`
  - `backend/tests/providers/test_provider_contract_gemini.py`
  - 覆盖 success shape、usage extraction、error normalization、stream finalize。
- Route failover tests：
  - `backend/tests/test_route_failover.py`
  - 覆盖 priority/weight、disabled/cooldown skip、quota exhausted skip、auth/rate_limit 处理、retryable/non-retryable 行为。
- Provider health probe：
  - 新增 provider credential 健康字段（`last_checked_at` 等）并通过 migration 落库。
  - CLI：
    - `python -m app.cli providers health-check --provider openai --credential-id ...`
    - `python -m app.cli providers health-check --all`
  - 使用模型列表/轻量探测请求，不发送敏感 prompt。
- Admin API：
  - `POST /v1/admin/provider-credentials/{id}/health-check`
  - `GET /v1/admin/provider-credentials/{id}/health`

## Result

- `provider_contract_tests_ready = true`
- `route_failover_tests_ready = true`
- `provider_health_probe_ready = true`
