# APICred Operations Readiness

## Summary

apicred_ops_ready: true

## Admin Provider Ops

provider_health_ui_ready: true  
provider_health_api_ready: true

## Policy

access_policy_ready: true  
policy_enforced_on_llm: true

## Usage Dashboard

usage_dashboard_api_ready: true  
usage_dashboard_ui_ready: true

## Provider Benchmark

provider_benchmark_ready: true

## Observability

metrics_endpoint_ready: true  
structured_logs_ready: true

## Load / Soak

load_test_ready: true  
success_rate: 1.0  
p95_latency_ms: 46.0

## Tests

pytest: pass (`122 passed, 3 skipped`)  
alembic: pass (`upgrade head` through `0005`)  
docker_compose_config: pass (`docker compose config --quiet`)

## Known Limitations

- `tenant_id` 过滤参数在 usage analytics API 中已预留，当前主聚合路径以 user/provider/model 为主。
- load/soak 默认使用 mock/stub 路径（`APICRED_USE_REAL_PROVIDER=false`），真实 provider 压测需显式开启。
- OTel 仅提供可选配置开关，当前未启用 exporter 实际接入。

## Next Steps

- 将 `scripts/apicred-ops-smoke.sh` 接入 CI nightly。
- 在预发环境执行一次 `APICRED_USE_REAL_PROVIDER=true` 的小规模 benchmark（受控额度）。
- 为 usage dashboard 增加 tenant 维度聚合查询与前端筛选器。
