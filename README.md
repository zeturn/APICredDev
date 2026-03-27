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
docker compose up -d --build
```

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

- `DATABASE_URL`
- `REDIS_URL`
- `APP_SECRET`
- `TOKEN_SALT`
- `ADMIN_TOKEN`
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

`provider_keys.secret_ref` 仍然填写你保存 API Key 的环境变量名，`provider_keys.key_name` 填对应服务商的 `base_url`。

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

## Deployment

生产建议：

- 使用独立 Postgres/Redis 托管实例
- 所有密钥通过环境变量注入
- 使用反向代理与 HTTPS
- 启用日志、监控与告警

---

如需 BasaltPass 联调，请先启动 BasaltPass 并配置 `BASALT_BASE_URL`。
