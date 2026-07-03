# 12 Observability Report

## Implemented

- 结构化日志增强（LLM 请求与完成日志）：
  - `request_id`
  - `user_id`
  - `token_id`
  - `public_model`
  - `provider`
  - `upstream_model`
  - `credential_id`
  - `route_id`
  - `usage_session_id`
  - `status`
  - `error_code`
  - `latency_ms`
  - `upstream_latency_ms`
  - `final_cost_credits`
- 未记录完整 prompt/response/secret 明文。

- 新增 `/metrics`：
  - `GET /metrics`（Prometheus text）
  - 指标包含：
    - `apicred_requests_total`
    - `apicred_llm_requests_total`
    - `apicred_llm_errors_total`
    - `apicred_provider_errors_total{provider=...}`
    - `apicred_tokens_total`
    - `apicred_cost_credits_total`
    - `apicred_upstream_latency_ms_bucket`
    - `apicred_active_requests`

- OTel 可选配置预留：
  - `OTEL_ENABLED`
  - `OTEL_EXPORTER_OTLP_ENDPOINT`

## Verification

- 测试：`backend/tests/test_observability.py` 通过。
- `/metrics` 输出包含关键指标，并校验不包含 `sk-` token 字样。

## Result

- `structured_logs_ready = true`
- `metrics_endpoint_ready = true`
- `secret_not_logged = true`
