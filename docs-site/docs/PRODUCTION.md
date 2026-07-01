# APICred 生产部署指南

## 1. 基础原则

- 所有秘钥通过环境变量注入
- 不在代码中写死数据库、Redis、第三方 token
- 对 Basalt 上游调用必须具备超时和重试
- 全量 API 接入日志与告警
- 数据库 schema 只能通过 Alembic migration 管理
- Provider/Search API key 通过管理后台录入并加密存库

## 2. 推荐部署拓扑

- APICred Backend（FastAPI）x N
- APICred Frontend（静态资源 + CDN）
- PostgreSQL（主从或托管）
- Redis（高可用）
- BasaltPass（独立部署域）
- API Gateway / WAF / HTTPS

## 3. 必要环境变量

- `DATABASE_URL`
- `REDIS_URL`
- `APP_SECRET`
- `TOKEN_SALT`
- `BASALT_BASE_URL`
- `BASALT_OAUTH_CLIENT_ID`
- `BASALT_OAUTH_CLIENT_SECRET`
- `BASALT_S2S_CLIENT_ID`
- `BASALT_S2S_CLIENT_SECRET`
- `BASALT_TIMEOUT_SECONDS`
- `BASALT_MAX_RETRIES`
- `PRODUCTION_MODE=true`

可选 bootstrap 变量：

- `APICRED_OPENAI_API_KEY`
- `BRAVE_SEARCH_API_KEY`

这些变量只建议用于初始化或本地环境。生产长期管理应使用管理后台的 provider credentials。

## 4. 发布前检查

1. 执行测试与覆盖率门禁
2. 执行 `alembic upgrade head`
3. 校验 Basalt 连接和关键代理接口
4. 校验管理员账号可以换取 Admin Token
5. 校验 LLM provider credentials、search provider credentials 均可用
6. 校验默认 public models、upstream models 和 model routes
7. 校验用户对话审计分页和软删除
8. 校验 SDK 示例可运行

## 5. 运行命令示例

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

```bash
cd frontend
npm run build
```

## 6. 搜索模型与 Key 管理

搜索能力与 LLM 使用同一套路由模型。生产环境中：

- 注册 `category=search` 的 public model，例如 `brave-web-search`
- 注册真实 upstream model，例如 `brave-search:web-search`
- 在 provider credentials 中录入 Brave Search API key
- 在 model routes 中配置 `quota_unit=requests`
- 对备用 key 配置不同 `priority`、`weight` 和 `quota_rules`

不要在代码中写死搜索 API key。`BRAVE_SEARCH_API_KEY` 只作为 bootstrap fallback。

## 7. 审计与数据保留

`audit_llm_messages` 保存 message 粒度审计数据：

- 用户原始请求
- APICred 托管工具上下文，例如搜索结果
- 模型回复

用户软删除只隐藏自己的视图，不会物理删除审计记录。生产环境需要明确数据保留期限、导出流程和合规删除流程。

