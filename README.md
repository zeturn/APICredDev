# APICred（Production Ready Basalt Integration）

APICred 是统一 API 接入与计费平台，本版本已完成：

- BasaltPass 的 `auth / permission / wallet` 一体化接入
- 业务 API + 管理 API 总量提升到 **50+**
- 管理端 + 用户端页面提升到 **30+**（当前 32 页面）
- Python SDK（生产可用）接入层
- 自动化测试（含 Basalt 代理、路由总量、重试逻辑）

---

## 1. 架构与能力

### 后端

- FastAPI + SQLAlchemy + Redis
- APICred 自有认证、钱包、Token 与账本
- BasaltPass 代理路由层（带超时、重试、统一响应）
- 管理能力与用户业务能力拆分

### 前端

- React + TypeScript + Vite
- 双控制台：用户工作台 + 管理后台
- 页面总数 32（用户 16 + 管理 16）
- 全量页面互链（侧边栏 + 页面级上一页/下一页 + 全量导航表）

### SDK

- `sdk/python/apicred_sdk`
- 支持 APICred 原生 API + Basalt 集成 API + Basalt 管理 API

---

## 2. BasaltPass 集成说明

新增路由：

- 业务域：`/v1/basalt/*`
- 管理域：`/v1/admin/basalt/*`

代理与鉴权特性：

- 配置化上游地址：`BASALT_BASE_URL`
- 重试策略：`BASALT_MAX_RETRIES`
- 请求超时：`BASALT_TIMEOUT_SECONDS`
- OAuth2/OIDC：`/v1/auth/basalt/login` -> `/api/v1/oauth/authorize`（Authorization Code + PKCE）
- PKCE 规则：`code_challenge = sha256(code_verifier).hexdigest()`（hex）
- S2S（权限/钱包）：使用 `client_id` / `client_secret` 请求头调用 `/api/v1/s2s/*`
- 最短联调步骤：`docs/BASALTPASS_QUICKSTART.md`

---

## 3. 目录结构

```text
APICred/
  backend/
    app/
      api/v1/
      core/
      db/
      services/
    tests/
  frontend/
    src/
      layouts/
      navigation/
      pages/
  sdk/
    python/
      apicred_sdk/
  docs/
    USAGE.md
    DEVELOPMENT.md
    TESTING.md
    SDK.md
    PRODUCTION.md
```

---

## 4. 环境变量（生产建议）

后端读取 `app/core/config.py`（大小写不敏感）：

- `DATABASE_URL`
- `REDIS_URL`
- `APP_SECRET`
- `TOKEN_SALT`
- `ADMIN_TOKEN`
- `STRIPE_WEBHOOK_SECRET`
- `BASALT_BASE_URL`（默认 `http://localhost:8101`）
- `BASALT_SERVICE_TOKEN`（服务级调用令牌）
- `BASALT_OAUTH_CLIENT_ID`
- `BASALT_OAUTH_CLIENT_SECRET`
- `BASALT_OAUTH_SCOPES`（默认 `openid profile email`）
- `BASALT_OAUTH_AUDIENCE`（可选）
- `BASALT_S2S_CLIENT_ID`
- `BASALT_S2S_CLIENT_SECRET`
- `BASALT_TIMEOUT_SECONDS`（默认 `15`）
- `BASALT_MAX_RETRIES`（默认 `2`）

> 生产环境必须通过环境变量覆盖默认值，不要使用开发默认秘钥。

---

## 5. 本地开发（Windows/WSL 均可）

### 启动后端

```bash
cd backend
python -m pip install fastapi sqlalchemy alembic pydantic pydantic-settings python-jose passlib[argon2] httpx redis stripe pytest pytest-asyncio pytest-cov aiosqlite email-validator
uvicorn app.main:app --reload --port 8103
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 启动 BasaltPass（用于联调）

在 `../BasaltPass` 项目中按其文档启动服务，保证 `http://localhost:8101` 可访问。

---

## 6. 页面规模与路由

前端当前总页面数：**32**

- 用户端：`/workspace/*` 共 16 页
- 管理端：`/admin*` 共 16 页

每个页面都提供：

- 左侧主导航（同域全链接）
- 上一页/下一页跳转
- 全量页面表格导航（32 页互链）

---

## 7. API 概览

### 原生 APICred（节选）

- Auth: `/v1/auth/*`
- Billing: `/v1/billing/*`
- Tokens: `/v1/tokens*`
- Admin: `/v1/admin/*`

### Basalt 业务代理

- `/v1/basalt/auth/*`
- `/v1/basalt/security/*`
- `/v1/basalt/wallet/*`
- `/v1/basalt/permissions`
- `/v1/basalt/roles`
- `/v1/basalt/orders*`
- `/v1/basalt/subscriptions*`

### Basalt 管理代理

- `/v1/admin/basalt/dashboard/*`
- `/v1/admin/basalt/apps*`
- `/v1/admin/basalt/users*`
- `/v1/admin/basalt/roles*`
- `/v1/admin/basalt/permissions*`
- `/v1/admin/basalt/wallets*`
- `/v1/admin/basalt/tenants*`
- `/v1/admin/basalt/subscriptions*`
- `/v1/admin/basalt/notifications*`
- `/v1/admin/basalt/logs`

---

## 8. SDK 快速使用

```python
from apicred_sdk import ApiCredClient, ApiCredConfig

client = ApiCredClient(ApiCredConfig(base_url="http://localhost:8103/v1"))
client.login("admin@example.com", "admin123")
print(client.wallet())
print(client.basalt("GET", "/wallet/balance"))
```

管理调用：

```python
client = ApiCredClient(ApiCredConfig(base_url="http://localhost:8103/v1", admin_token="dev-admin-token"))
print(client.admin_basalt("GET", "/dashboard/stats"))
```

---

## 9. 测试

```bash
cd backend
pytest -q --cov=app --cov-report=term-missing
```

Basalt 集成模块覆盖率门禁（98%+）：

```bash
cd backend
pytest -q tests/test_basalt_proxy_api.py tests/test_basaltpass_client.py \
  --cov=app.api.v1.basalt \
  --cov=app.services.basaltpass_client \
  --cov-report=term-missing \
  --cov-fail-under=98
```

新增测试覆盖：

- Basalt 代理用户/管理接口行为
- 路由总量（管理 + 业务 >= 50）
- Basalt 客户端重试策略

详细说明见：`docs/TESTING.md`

---

## 10. 生产部署清单

- 使用独立 Postgres、Redis 与反向代理
- 全部秘钥通过环境变量注入
- 开启 HTTPS / WAF / 访问日志
- 对 Basalt 网关启用健康检查与告警
- 使用 CI 跑测试与覆盖率门禁

详见：`docs/PRODUCTION.md`