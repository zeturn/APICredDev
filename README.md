# APICred

统一 API 接入与计费平台，集成 BasaltPass 鉴权/权限/钱包能力，提供用户端与管理端控制台、后端 API 与 Python SDK。

## Overview

- **定位**：API 网关与计费中台（FastAPI + Postgres + Redis）
- **核心能力**：认证、令牌、计费、BasaltPass 代理、管理后台
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

管理员可通过 `GET /v1/admin/provider-presets` 获取常见上游的推荐 `provider` 和 `base_url` 组合，便于创建 `provider_keys`。

常见示例：

- `openai` -> `https://api.openai.com`
- `openrouter` -> `https://openrouter.ai/api`
- `deepseek` -> `https://api.deepseek.com`
- `groq` -> `https://api.groq.com/openai`
- `xai` -> `https://api.x.ai`
- `siliconflow` -> `https://api.siliconflow.cn`
- `anthropic` -> `https://api.anthropic.com`
- `gemini` -> `https://generativelanguage.googleapis.com`

`provider_keys` 现在会把管理员录入的 API Key 加密后存库，`key_name` 填默认 `base_url`，详情页里的模型绑定可以再覆盖单模型 `base_url`。

加密实现使用标准 AEAD（`Fernet`），并保留历史密文格式的解密兼容。

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
- Provider API Key 通过管理后台录入并加密存储到数据库
- 使用反向代理与 HTTPS
- 启用日志、监控与告警
- 设置 `PRODUCTION_MODE=true`
- 关闭 `STARTUP_CREATE_TABLES_ENABLED`
- 关闭 `STARTUP_SCHEMA_COMPAT_ENABLED` 和 `STARTUP_BOOTSTRAP_ENABLED`
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
