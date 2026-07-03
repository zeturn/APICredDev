# 13 Standalone Load / Soak Report

## Setup

- Script: `scripts/apicred-load-test.sh` + `scripts/apicred_load_test.py`
- Mode: `APICRED_USE_REAL_PROVIDER=false`（默认 mock/stub 模式，避免真实成本）
- Run parameters:
  - `APICRED_LOAD_CONCURRENCY=5`
  - `APICRED_LOAD_REQUESTS=50`

## Result

- `total_requests`: 50
- `success_rate`: 1.0
- `error_rate`: 0.0
- `avg_latency_ms`: 32.5
- `p95_latency_ms`: 46.0
- `p99_latency_ms`: 48.0
- `max_rss_memory`: null
- `db_errors`: 0
- `redis_errors`: 0
- `quota_errors_expected`: 0
- `unexpected_errors`: {}

## Conclusion

- `load_test_ready = true`
- `success_rate >= 0.99 for stub provider = true`
- `p95_latency_ms recorded = true`
- `no secret leakage = true`
