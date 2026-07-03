# 09 Access Policy Layer Report

## Implemented

- 新增表：`access_policies`（migration `0005_ops_console_policy_observability`）。
- 新增策略服务：`backend/app/services/policy_service.py`
  - scope 支持：`global | tenant | user | token`
  - 规则：
    - deny wins（model/provider block 优先）
    - limits 采用“更具体 scope 优先”
    - global 作为 fallback
  - 支持限制：
    - requests/minute
    - requests/day
    - tokens/day
    - cost/day
    - cost/month
- `/v1/chat/completions` 在 authorize 前接入 `enforce_pre_authorize_policy`，并在候选 provider 选择时接入 provider allow/block。
- 新增 admin policy API：
  - `GET /v1/admin/policies`
  - `POST /v1/admin/policies`
  - `GET /v1/admin/policies/{id}`
  - `PUT /v1/admin/policies/{id}`
  - `DELETE /v1/admin/policies/{id}`
  - `POST /v1/admin/policies/{id}/enable`
  - `POST /v1/admin/policies/{id}/disable`

## Verification

- `backend/tests/test_access_policy_service.py` 通过：
  - global model block
  - user allowlist
  - token provider block
  - daily cost cap
  - daily token cap
  - deny wins
  - disabled policy ignored
- `backend/tests/test_access_policy_api.py` 通过。
- `backend/tests/test_access_policy_llm_enforcement.py` 通过（policy violation 返回清晰错误）。

## Result

- `access_policy_ready = true`
- `policy_enforced_on_llm = true`
- `policy_tests_pass = true`
