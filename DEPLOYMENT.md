# APICred 部署说明

本文档约定 APICred 通过 `GHCR + GitHub Actions + 服务器 docker compose pull && up -d` 自动部署，并使用 `BasaltPass` 作为统一认证服务。

## 1. 部署目标

- 后端 API: `8103`
- 前端: `5106`
- 建议镜像:
  - `ghcr.io/<owner>/apicred-backend:<tag>`
  - `ghcr.io/<owner>/apicred-frontend:<tag>`
- 健康检查:
  - 后端建议使用 `http://<host>:8103/health` 或现有 API 健康端点

## 2. BasaltPass 接入方式

APICred 后端直接对接 BasaltPass 的 OAuth2/OIDC 与 S2S 能力。

- OAuth 登录入口: `/v1/auth/basalt/login`
- 回调地址:
  - `https://api.example.com/v1/auth/basalt/callback`
  - 兼容旧路由: `https://api.example.com/v1/auth/basalt/oauth/<provider>/callback`
- OAuth 端点由 `BASALT_BASE_URL` 推导:
  - `/api/v1/oauth/authorize`
  - `/api/v1/oauth/token`
  - `/api/v1/oauth/userinfo`
- S2S 用于权限/钱包等服务级调用
- 前端 BasaltPass 登录按钮实际跳转到后端 OAuth 路由

注意: 代码里 PKCE 使用的是 BasaltPass 约定的 `sha256(verifier).hexdigest()`。

## 3. 需要在 BasaltPass 中创建的客户端

至少准备两套凭据:

1. OAuth 客户端
- `grant_types`: `authorization_code`, `refresh_token`
- `client_type`: `confidential`
- `redirect_uri`: `https://api.example.com/v1/auth/basalt/callback`
- `scopes`: `openid profile email`
- `require_pkce`: `true`

2. S2S 客户端
- `grant_types`: `client_credentials`
- 按 APICred 实际调用范围授予最小权限

## 4. APICred 生产环境变量

后端核心变量来自 `backend/app/core/config.py`:

```env
DATABASE_URL=postgresql+asyncpg://apicred:<password>@postgres:5432/apicred
REDIS_URL=redis://:<password>@redis:6379/0
APP_SECRET=<long-random-secret>
TOKEN_SALT=<long-random-secret>
ADMIN_TOKEN=<admin-token>

BASALT_BASE_URL=https://auth.example.com
BASALT_OAUTH_CLIENT_ID=<oauth-client-id>
BASALT_OAUTH_CLIENT_SECRET=<oauth-client-secret>
BASALT_OAUTH_SCOPES=openid profile email
BASALT_OAUTH_AUDIENCE=
BASALT_S2S_CLIENT_ID=<s2s-client-id>
BASALT_S2S_CLIENT_SECRET=<s2s-client-secret>
BASALT_TIMEOUT_SECONDS=15
BASALT_MAX_RETRIES=2

APICRED_PUBLIC_BASE_URL=https://api.example.com
FRONTEND_BASE_URL=https://app.example.com
```

前端至少要能访问:

```env
VITE_API_BASE_URL=https://api.example.com/v1
VITE_BASALT_OAUTH_PROVIDER=google
```

## 5. GHCR 自动部署建议

如果仓库尚未提交 deploy workflow，直接按工作区统一 SOP 落地即可:

1. GitHub Actions 构建后端和前端镜像并推送到 GHCR。
2. 服务器保存 `docker-compose.prod.yml` 和 `.env`。
3. Action 通过 SSH 登录服务器执行:

```bash
docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
docker compose pull
docker compose up -d --remove-orphans
```

建议 GitHub Actions Secrets:

- `DEPLOY_HOST`
- `DEPLOY_PORT`
- `DEPLOY_USER`
- `DEPLOY_PATH`
- `DEPLOY_SSH_PRIVATE_KEY`
- `DEPLOY_GHCR_USERNAME`
- `DEPLOY_GHCR_TOKEN`
- `BASALT_OAUTH_CLIENT_ID`
- `BASALT_OAUTH_CLIENT_SECRET`
- `BASALT_S2S_CLIENT_ID`
- `BASALT_S2S_CLIENT_SECRET`
- `APP_SECRET`
- `TOKEN_SALT`
- `ADMIN_TOKEN`

## 6. 服务器落地步骤

1. 先部署 BasaltPass，确保 `https://auth.example.com` 可访问。
2. 在 BasaltPass 中创建 APICred 的 OAuth/S2S 客户端。
3. 在服务器准备 APICred 的 `.env`。
4. 部署数据库、Redis、APICred backend、APICred frontend。
5. 配置反向代理:
  - `app.example.com` -> 前端
  - `api.example.com` -> 后端
6. 验证登录:
  - 访问前端登录页
  - 点击“使用 BasaltPass 登录”
  - 成功后应跳回 APICred 页面并写入 token

## 7. 验收清单

- `BASALT_BASE_URL` 指向线上 BasaltPass
- `APICRED_PUBLIC_BASE_URL` 与 BasaltPass 配置的回调地址一致
- OAuth 登录能成功跳转并回调
- S2S 调用权限/钱包接口成功
- 后端健康检查通过
