# 11 Provider Benchmark / Routing Insight Report

## Implemented

- 新增表（migration `0005`）：
  - `provider_benchmark_runs`
  - `provider_benchmark_results`
- 新增 benchmark 服务：`backend/app/services/provider_benchmark_service.py`
- 新增 CLI：
  - `python -m app.cli providers benchmark --public-model apicred-fast --runs 5`
  - `python -m app.cli providers benchmark --provider openai --runs 5`
  - 支持 `--dry-run`、`--mock-mode`
  - 默认 prompt：`Reply with exactly: ok`
- 新增 API：
  - `GET /v1/admin/provider-benchmarks`
  - `POST /v1/admin/provider-benchmarks`
  - `GET /v1/admin/provider-benchmarks/{id}`
- 前端 Provider Health 页面显示最近 benchmark runs。

## Metrics Output

结果包含：

- provider
- credential_id
- upstream_model
- success_rate
- avg_latency_ms
- p95_latency_ms
- error_rate
- tokens
- estimated_cost
- health_state_before
- health_state_after

## Verification

- 测试：`backend/tests/test_provider_benchmark.py` 通过。
- CLI dry-run 通过并持久化 run/result 结构（targets=0 场景也可落库 run）。

## Result

- `provider_benchmark_ready = true`
- `benchmark_results_persisted = true`
- `routing_insight_available = true`
