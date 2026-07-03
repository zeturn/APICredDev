# APICred Hardening Inventory

## 1) 当前启动方式

- 本地后端：`cd backend && python -m pip install -e . && uvicorn app.main:app --reload --port 8103`
- Docker 一体启动：`docker compose up -d --build`，包含 `postgres` / `redis` / `backend` / `frontend`。
- FastAPI 生命周期在 `app.main` 中执行：
  - `validate_production_settings(settings)` 生产配置校验。
  - 可选 `Base.metadata.create_all`（`STARTUP_CREATE_TABLES_ENABLED=true`）。
  - 可选 bootstrap（管理员、默认 catalog、OpenAI/Brave 凭证）。

## 2) env 配置

- 已发现核心变量：`DATABASE_URL`、`REDIS_URL`、`APP_SECRET`、`TOKEN_SALT`、`ADMIN_PASSWORD`、`PRODUCTION_MODE`、`DEBUG_ENDPOINTS_ENABLED`、`STARTUP_*`、BasaltPass OAuth/S2S 变量等。
- 当前风险：
  - 生产校验仅覆盖少量项（主要 `APP_SECRET`/`TOKEN_SALT` + 两个开关）。
  - Compose 默认将 `DEBUG_ENDPOINTS_ENABLED=true`、`STARTUP_CREATE_TABLES_ENABLED=true`、`STARTUP_BOOTSTRAP_ENABLED=true`，若用于生产会带来风险。
  - 未形成“显式加密主密钥”配置体系（目前凭证加密依赖 `APP_SECRET:TOKEN_SALT` 推导）。

## 3) DB schema / migrations

- 现有 Alembic 迁移：
  - `0001_initial_schema`
  - `0002_drop_provider_url`
  - `0003_audit_llm_messages`
- 已有核心表：`public_models`、`model_routes`、`upstream_models`、`providers`、`provider_endpoints`、`provider_credentials`、`usage_sessions`、`audit_llm_messages`、`wallets`、`ledger_entries`、`api_tokens` 等。
- 当前风险：
  - 仍支持启动时 `create_all + schema compat`，与 Alembic-first 生产治理冲突。
  - 缺少 durable quota ledger 专用表，难做重启恢复与对账。
  - `provider_credentials` 缺少健康探测元数据字段（last success/failure/error 等）。
  - `audit_llm_messages` 缺少哈希存储与 retention 字段。

## 4) provider / route / credential 模型

- 路由核心流程：
  - `model_routes` 按 `priority` 分组，组内按 `weight` 加权打散。
  - route 过滤了 disabled/cooldown endpoint 或 credential。
  - provider 适配器通过 `factory` 分发到 OpenAI-compat / Anthropic / Gemini。
- 当前风险：
  - 凭证健康状态主要在请求失败时被动更新，缺少主动 health check。
  - 故障类别标准化在不同 provider 仍需 contract test 固化。
  - failover 逻辑缺少系统化测试覆盖（优先级、冷却、禁用、不可重试中断等）。

## 5) LLM proxy 流程

- `POST /v1/chat/completions` 关键步骤：
  - 认证与 scope 校验。
  - 预估 tokens/cost，先 `authorize_usage` 预扣。
  - 可选托管搜索工具注入。
  - 选路 -> Redis quota reserve -> 调用 provider -> 记录 response audit -> `settle_usage`。
  - 上游异常会按 `normalize_error` 决定是否重试/切换 route。
- 当前风险：
  - quota 主要依赖 Redis 临时桶，缺少 durable 记账轨迹。
  - 上游失败后的结算语义较粗，后续对账能力不足。

## 6) quota / billing 流程

- 现状：
  - Redis Lua 做分钟/小时/天/月桶预占。
  - 钱包扣费通过 `usage_sessions + ledger_entries` 处理预扣与结算差额。
- 当前风险：
  - Redis 桶不可替代长期账本，不利于跨重启恢复与审计。
  - 缺少 quota 层面的 reconciliation 命令。
  - 缺少专门 admin 查询接口用于按 provider/model/status 追踪 quota 账本。

## 7) audit 流程

- 现状：
  - request/tool/response message 写入 `audit_llm_messages`。
  - 支持用户软删除（`user_deleted_at`），管理员可查看包含软删记录。
- 当前风险：
  - 默认直接存 message content，缺少敏感信息规则脱敏。
  - 无 hash-only 存储模式。
  - 无 retention TTL 字段与 purge CLI。

## 8) BasaltPass 集成

- 已集成能力：
  - OAuth/S2S 客户端参数。
  - 管理端访问校验（admin access）。
  - 远程钱包余额同步与扣减（条件满足时启用）。
- 当前风险：
  - 与本地钱包并存，异常场景一致性依赖应用层流程。
  - 需要更完善对账与失败补偿策略（尤其在上游调用失败、重试、超时场景）。

## 9) 已有测试

- 当前测试集中于：
  - API 基础流程、鉴权、安全硬化、BasaltPass 客户端、配额 Lua、加密兼容等。
- 缺口：
  - 生产配置防护覆盖不足。
  - provider contract tests 缺失（openai compat/anthropic/gemini）。
  - route failover 系统测试不足。
  - durable quota ledger / reconcile 缺失。
  - audit redaction/hash/retention 缺失。
  - secret rotation 命令缺失。

## 10) 当前生产化风险

1. **配置风险**：生产校验项不足，可能误用开发开关与弱默认 secret。  
2. **凭证风险**：未使用独立 encryption key 与 key-id 版本化轮换。  
3. **配额风险**：Redis-only quota 预占不具备 durable ledger 属性。  
4. **路由风险**：缺少 provider contract / failover 完整测试矩阵。  
5. **审计风险**：敏感内容明文落库，缺乏统一 redaction + retention。  
6. **运维风险**：缺少统一 hardening smoke 脚本与 readiness 汇总报告。  

## 结论

APICred 具备完整基础骨架，但距离 production-ready 的凭证治理、quota durability、provider 健康探测与审计隐私仍有明显增强空间。后续阶段需以 Alembic 迁移 + 可测试 CLI + admin 可观测接口为核心完成加固。
