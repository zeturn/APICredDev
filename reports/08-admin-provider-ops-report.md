# 08 Admin Provider Ops Report

## Implemented

- 后端新增/补齐 API：
  - `GET /v1/admin/provider-health`
  - `GET /v1/admin/provider-credentials/{id}/health`
  - `POST /v1/admin/provider-credentials/{id}/health-check`
  - `POST /v1/admin/provider-credentials/{id}/disable`
  - `POST /v1/admin/provider-credentials/{id}/enable`
  - `POST /v1/admin/provider-credentials/{id}/rotate-secret`
  - `GET /v1/admin/model-routes/{id}/effective-status`
- 前端新增页面：
  - `frontend/src/pages/admin/AdminProviderHealth.tsx`
  - 展示 provider/endpoint/credential/health/cooldown/last success/failure/error/routes/quota summary
  - 支持 health check、enable/disable、rotate secret（输入提交后清空）
- Provider health 页面显示最近 benchmark runs。

## Verification

- 测试：`backend/tests/test_admin_provider_health_api.py` 通过。
- 前端 build：`npm run build` 通过。
- secret rotation API 不回显 secret 明文，后端 `_to_dict` 仍过滤 `secret_encrypted` 与 `api_key`。

## Result

- `admin_provider_ops_ready = true`
- `provider_health_api_ready = true`
- `provider_health_ui_ready = true`
- `secret_not_leaked = true`
