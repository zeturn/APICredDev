# APICred

统一 API 接入与计费平台，集成 BasaltPass 鉴权/权限/钱包能力，提供用户端与管理端控制台、后端 API 与 Python SDK。

## Overview

- **定位**：API 网关与计费中台（FastAPI + Postgres + Redis）
- **核心能力**：认证、令牌、模型目录、上游路由、计费、BasaltPass 代理、管理后台
- **运行形态**：`backend` + `frontend` + `postgres` + `redis`

## Repository Structure

```text
APICred/
├─ backend/                 # FastAPI 后端
├─ frontend/                # React + Vite 前端
├─ sdk/python/              # Python SDK
├─ scripts/                 # 启动与维护脚本
├─ docker-compose.yml       # Docker 编排
├─ docs-site/               # Docusaurus 文档站（统一文档入口）
└─ README.md
```

## Quick Start

### Docker

```bash
cd APICred
cp .env.compose.example .env
docker compose up -d --build
```

> `docker-compose.yml` 不再内置数据库/Redis/应用密钥；未提供 `.env` 中的必填变量会直接启动失败。

- Backend: `http://localhost:8103`
- Frontend: `http://localhost:5106`
- Postgres: `localhost:5403`
- Redis: `localhost:6303`

### Local Development

```bash
cd backend
python -m pip install -e .
uvicorn app.main:app --reload --port 8103
```

```bash
cd frontend
npm install
npm run dev
```

## Domain Model

APICred 的模型路由域已经拆成五个一等对象：

```text
public_models
  └── model_routes
        ├── upstream_models
        │     └── providers
        └── provider_credentials
              └── provider_endpoints
                    └── providers
```

含义：

- `public_models`：用户可见、可购买、可在请求里传入的模型，例如 `apicred-fast`。
- `upstream_models`：上游真实模型名，例如 `openai:gpt-4o-mini` 或 `anthropic:claude-sonnet-4.6`。
- `providers`：上游供应商/协议适配器，例如 `openai`、`gemini`、`anthropic`、`openrouter`。
- `provider_endpoints`：上游访问入口，`base_url` 的唯一默认归属，例如 `https://api.openai.com`。
- `provider_credentials`：绑定到某个 endpoint 的 API key/credential，密钥加密后存库。
- `model_routes`：把一个 public model 路由到某个 upstream model + credential，并配置 `priority`、`weight`、quota 和可选 `base_url_override`。

Base URL 解析顺序：

```text
1. model_routes.base_url_override
2. provider_credentials -> provider_endpoints.base_url
3. provider preset fallback
```

`providers` 不保存 `default_base_url`。Provider 只表达供应商/适配器身份；默认请求入口属于 `provider_endpoints`。

`model_routes.provider_credential_id = null` 表示该 route 指向 public/no-auth endpoint 或 internal provider。普通第三方 API key 路由应绑定具体 `provider_credentials`。

Admin schema 对以下枚举做约束：

```python
Literal["healthy", "disabled", "cooldown"]
Literal["tokens", "requests"]
Literal["llm", "image", "embedding", "audio", "moderation", "realtime"]
```

## Catalog

默认 catalog 从 YAML 加载：

```text
backend/app/catalog/default_providers.yaml
backend/app/catalog/default_models.yaml
backend/app/catalog/default_routes.yaml
```

其中：

- `default_providers.yaml` 定义 brands、providers、provider_endpoints 和默认 provider_credentials 占位。
- `default_models.yaml` 定义 public models 和 upstream models。
- `default_routes.yaml` 定义默认 public model 到 upstream model + credential 的路由。

## Configuration

常用环境变量：

- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `DATABASE_URL`
- `REDIS_URL`
- `APP_SECRET`
- `TOKEN_SALT`
- `ADMIN_JWT_AUDIENCE`
- `ADMIN_JWT_EXP_MINUTES`
- `BASALT_BASE_URL`
- `BASALT_OAUTH_CLIENT_ID`
- `BASALT_OAUTH_CLIENT_SECRET`
- `BASALT_S2S_CLIENT_ID`
- `BASALT_S2S_CLIENT_SECRET`

### Provider Presets

管理员可通过 `GET /v1/admin/provider-presets` 获取常见上游的推荐 `provider`、`protocol` 和 endpoint `base_url` 组合，便于创建 `provider_endpoints` 与 `provider_credentials`。

常见示例：

- `openai` -> `https://api.openai.com`
- `openrouter` -> `https://openrouter.ai/api`
- `deepseek` -> `https://api.deepseek.com`
- `groq` -> `https://api.groq.com/openai`
- `xai` -> `https://api.x.ai`
- `siliconflow` -> `https://api.siliconflow.cn`
- `anthropic` -> `https://api.anthropic.com`
- `gemini` -> `https://generativelanguage.googleapis.com`

`provider_credentials` 会把管理员录入的 API key 加密后存库；endpoint 的 `base_url` 在 `provider_endpoints` 中维护，单条路由可通过 `model_routes.base_url_override` 覆盖。

加密实现使用标准 AEAD（`Fernet`），并保留历史密文格式的解密兼容。

### OpenAI Provider Bootstrap

APICred 可以在启动 bootstrap 时从环境变量导入一个 OpenAI provider credential。密钥会先加密再存入数据库，不应写入仓库文件。

必需变量：

- `STARTUP_BOOTSTRAP_ENABLED=true`
- `APICRED_OPENAI_API_KEY=<your OpenAI key>`

可选变量：

- `BOOTSTRAP_OPENAI_KEY_NAME`：provider credential 名称，默认 `OpenAI free daily shared traffic`
- `BOOTSTRAP_OPENAI_BASE_URL`：OpenAI endpoint base URL，默认 `https://api.openai.com`
- `BOOTSTRAP_OPENAI_MODELS`：逗号分隔的模型列表，默认包含 OpenAI free daily shared-traffic 模型集合

启动时会创建或更新 OpenAI provider、default endpoint、provider credential、缺失的 OpenAI public/upstream models，并通过 `model_routes` 绑定路由。

## Persistence Mounts

`docker-compose.yml` 当前已挂载：

- `./data/postgres -> /var/lib/postgresql/data`（PostgreSQL 数据）
- `./data/redis -> /data`（Redis 数据）
- `./frontend -> /app`（前端开发映射）

## Documentation

项目文档统一入口：`docs-site/`（Docusaurus）。

- 本地预览：

```bash
cd docs-site
npm install
npm run start
```

## Testing

```bash
cd backend
pytest -q
```

## Authentication Session

- 用户登录后，后端会下发 `HttpOnly` 会话 Cookie（默认名 `apicred_access_token`）。
- 前端不再在 `localStorage` 持久化 `access_token`。
- 管理端 JWT 通过已登录会话换取，并仅保存在前端内存中。

## Deployment

生产建议：

- 使用独立 Postgres/Redis 托管实例
- Provider API key 通过管理后台录入并加密存储到数据库
- 使用反向代理与 HTTPS
- 启用日志、监控与告警
- 设置 `PRODUCTION_MODE=true`
- 使用 Alembic 管理数据库 schema
- 关闭 `STARTUP_BOOTSTRAP_ENABLED`
- 保持 `DEBUG_ENDPOINTS_ENABLED=false`

## Security and Quality

- CodeQL is configured to scan GitHub Actions, Go, Python, and JavaScript/TypeScript when those languages are present.
- Keep secrets out of the repository. Use `.env` files locally and GitHub Actions secrets in CI.
- Report vulnerabilities privately through the process in `SECURITY.md`.

## Contributing

Please read `CONTRIBUTING.md` before opening issues or pull requests. Contributions should include a clear description, relevant tests or manual verification, and updates to documentation when behavior changes.

## Code of Conduct

This project follows the community expectations in `CODE_OF_CONDUCT.md`.

## License

This project is licensed under the ISC License. See `LICENSE` for details.

---

如需 BasaltPass 联调，请先启动 BasaltPass 并配置 `BASALT_BASE_URL`。
