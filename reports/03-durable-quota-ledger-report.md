# 03 Durable Quota Ledger Report

## Scope

引入 durable quota ledger，补齐 reserve/settle/reject/fail 轨迹与 reconciliation 能力。

## Implemented

- 新表：`quota_ledger_entries`
  - 已通过 Alembic `0004_apicred_hardening_features` 创建。
- 行为集成：
  - `authorize_usage` 创建 `reserved` ledger entry。
  - 路由选中并 Redis reserve 成功后记录 `reserved_delta/provider/upstream/credential`。
  - 正常结算时标记 `settled`。
  - 上游失败标记 `failed`。
  - 无容量/拒绝标记 `rejected`。
- 幂等：
  - `settle_quota_ledger` 对终态（`settled/rejected/released/failed`）重复调用无副作用。
- reconciliation CLI：
  - `python -m app.cli quota reconcile --dry-run`
  - `python -m app.cli quota reconcile`
- Admin API：
  - `GET /v1/admin/quota/usage`
  - `GET /v1/admin/quota/ledger`
  - 支持 `user_id/token_id/provider/model/date_from/date_to/status` 过滤。

## Tests

- 新增：
  - `backend/tests/test_quota_ledger.py`
  - `backend/tests/test_quota_reconciliation.py`
- 覆盖 reserve/settle、failure、idempotent settle、rejected、reconcile 异常场景。

## Result

- `durable_quota_ledger_ready = true`
- `quota_reconciliation_ready = true`
- `settlement_idempotent = true`
