# APICred Ops Inventory (Round 2)

## 1. 第一轮新增 migration

- `backend/alembic/versions/0004_apicred_hardening_features.py`
  - 新增 `quota_ledger_entries`
  - 扩展 `provider_credentials` 健康字段（last checked/success/failure/error、consecutive_failures）
  - 扩展 `audit_llm_messages`（content_hash/content_preview/redaction_applied/retention_expires_at）

## 2. 第一轮新增 CLI

- `python -m app.cli secrets rotate-provider-credentials [--dry-run]`
- `python -m app.cli quota reconcile [--dry-run]`
- `python -m app.cli providers health-check --credential-id ... | --all [--provider ...]`
- `python -m app.cli audit purge-expired [--dry-run]`

## 3. 第一轮新增 API

- `GET /v1/admin/quota/usage`
- `GET /v1/admin/quota/ledger`
- `POST /v1/admin/provider-credentials/{id}/health-check`
- `GET /v1/admin/provider-credentials/{id}/health`

## 4. 当前 admin UI 可见性

- **provider health**：后端已有基础 API，但 admin 前端尚无专门 Provider Health 控制台页面。
- **quota**：后端已有 `quota/usage` 与 `quota/ledger` API，但 admin 前端当前未接入展示。
- **audit**：已有用户/管理员审计会话接口，但 admin 侧缺少统一审计运营视图（偏用户维度查看）。

## 5. usage/cost 聚合能力（user/token/provider/model）

- 当前已支持部分聚合（最近会话、按 model/provider 汇总）。
- 仍缺：
  - token 维度聚合
  - 时间序列聚合（minute/hour/day bucket）
  - 错误率与延迟聚合
  - 更完整多维过滤组合

## 6. tenant-level policy 支持情况

- 当前**不支持**独立的 tenant/user/token/global policy 对象与统一策略解析层。
- `/v1/chat/completions` 尚未在 authorize 前做策略决策（allow/deny/cap resolution）。

## 7. metrics / structured logs / tracing

- **Structured logs**：存在基础日志与 request_id，但尚未形成统一可运营字段集（status/error/latency/cost 全链路）。
- **Metrics**：无 `/metrics` 指标端点。
- **Tracing**：未见 OTel 可选接入配置与实现。

## 8. load test

- 当前无独立的 APICred load/soak 脚本与报告产物（仅有 hardening smoke 脚本）。

## 9. 当前最大运营风险

1. **可观测性不足**：缺指标端点与标准化运营日志，定位高错误率/高延迟/高成本来源困难。  
2. **策略层缺失**：缺 tenant/user/token policy，难做细粒度成本与访问控制。  
3. **运营控制台不足**：provider health/quota/audit 的 UI 运营闭环未形成。  
4. **容量验证不足**：缺负载与浸泡测试基线，独立运行风险不透明。  
