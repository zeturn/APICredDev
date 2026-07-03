# 10 Usage / Cost Dashboard Report

## Implemented

- `usage_sessions` 增强字段（migration `0005`）：
  - `latency_ms`
  - `upstream_latency_ms`
  - `error_code`
  - `error_message`
- 新增 usage analytics 服务：`backend/app/services/usage_analytics_service.py`
- 新增 API：
  - `GET /v1/admin/usage/summary`
  - `GET /v1/admin/usage/timeseries`
  - `GET /v1/admin/usage/top-users`
  - `GET /v1/admin/usage/by-provider`
  - `GET /v1/admin/usage/by-model`
  - `GET /v1/admin/usage/errors`
  - `GET /v1/admin/quota/summary`
- 支持参数：`from`、`to`、`bucket`、`tenant_id`、`user_id`、`provider`、`model`（tenant_id 预留，user/provider/model 已可过滤）。
- 前端新增页面：
  - `frontend/src/pages/admin/AdminUsageDashboard.tsx`
  - 显示 summary cards、provider/model 视图、top users、errors、quota summary。

## Verification

- 测试：`backend/tests/test_admin_usage_analytics.py` 通过。
- 前端 build 通过。

## Result

- `usage_dashboard_api_ready = true`
- `usage_dashboard_ui_ready = true`
- `latency_metrics_recorded = true`
