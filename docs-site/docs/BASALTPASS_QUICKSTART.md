# APICred x BasaltPass 最短联调指南

本文用于本地快速验证 APICred 已正确接入 BasaltPass 的三条链路：

- OAuth2/OIDC 登录（Authorization Code + PKCE）
- S2S 权限查询（permissions / roles）
- S2S 钱包查询（wallet balance / history）

## 1. 准备环境变量

编辑 `backend/.env`，至少确认以下字段：

```env
BASALTPASS_BASE_URL=http://localhost:8080
BASALTPASS_CLIENT_ID=...
BASALTPASS_CLIENT_SECRET=...
BASALTPASS_SCOPES=openid profile email
BASALTPASS_AUDIENCE=

BASALTPASS_S2S_CLIENT_ID=...
BASALTPASS_S2S_CLIENT_SECRET=...

APICRED_PUBLIC_BASE_URL=http://localhost:8002
FRONTEND_BASE_URL=http://localhost:5179
DEBUG_ENDPOINTS_ENABLED=true
```

注意：

- `BASALTPASS_S2S_CLIENT_ID/SECRET` 需要在 BasaltPass 侧具备 `s2s.rbac.read`、`s2s.wallet.read` 等 scope。
- 如果 OAuth Client 与 S2S Client 不是同一个，分别填写对应凭证。

## 2. 启动服务

在 APICred 项目中：

```bash
cd backend
PYTHONPATH=. uvicorn app.main:app --reload --port 8002
```

确保 BasaltPass 已运行在 `BASALTPASS_BASE_URL` 对应地址。

## 3. 走 OAuth 登录

浏览器打开：

```text
http://localhost:8002/v1/auth/basalt/login?next=/workspace/dashboard
```

完成 BasaltPass 登录授权后，APICred 会重定向到前端地址：

```text
http://localhost:5179/login?token=<APICRED_JWT>&next=...&source=basaltpass
```

从 URL 中拷贝 `token` 参数，作为后续 API 的 `Bearer`。

## 4. 调用权限与钱包接口

替换 `<TOKEN>` 后执行：

```bash
curl -sS "http://localhost:8002/v1/basalt/permissions" \
  -H "Authorization: Bearer <TOKEN>"
```

```bash
curl -sS "http://localhost:8002/v1/basalt/roles" \
  -H "Authorization: Bearer <TOKEN>"
```

```bash
curl -sS "http://localhost:8002/v1/basalt/wallet/balance?currency=CNY&limit=20" \
  -H "Authorization: Bearer <TOKEN>"
```

```bash
curl -sS "http://localhost:8002/v1/basalt/wallet/history?currency=CNY&limit=20" \
  -H "Authorization: Bearer <TOKEN>"
```

可选调试接口（仅在 `DEBUG_ENDPOINTS_ENABLED=true` 时可用）：

```bash
curl -sS "http://localhost:8002/v1/basalt/debug/context" \
  -H "Authorization: Bearer <TOKEN>"
```

## 5. 常见报错

- `basalt_identity_missing`：当前 APICred 用户未绑定 Basalt 身份（OAuth 回调没拿到 `sub` 或未成功写入用户）。
- `s2s_config_missing`：未配置 `BASALTPASS_S2S_CLIENT_ID/SECRET`。
- `s2s_request_failed`：S2S 凭证无效、scope 不足或 BasaltPass 上游返回错误。

## 6. 快速自检命令

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_auth_basalt_oauth.py tests/test_basaltpass_client.py tests/test_basalt_proxy_api.py
```
