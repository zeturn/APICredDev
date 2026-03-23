# APICred 使用文档

## 1. 登录与认证

1. 调用 `POST /v1/auth/register` 注册账号
2. 调用 `POST /v1/auth/login` 获取 `access_token`
3. 后续业务请求使用：

```http
Authorization: Bearer <access_token>
```

## 2. 用户业务主流程

### 2.1 Token 管理

- `POST /v1/tokens`
- `GET /v1/tokens`
- `DELETE /v1/tokens/{token_id}`

### 2.2 钱包与账本

- `GET /v1/billing/wallet`
- `GET /v1/billing/ledger`
- `POST /v1/billing/redeem`

### 2.3 Basalt 用户能力（auth / permission / wallet）

主要入口均在 `GET|POST|PUT /v1/basalt/*`，核心分组：

- `auth`: `/v1/basalt/auth/*`
- `permission`: `/v1/basalt/permissions`、`/v1/basalt/roles`
- `wallet`: `/v1/basalt/wallet/*`

## 3. 管理后台主流程

管理请求使用：

```http
X-Admin-Token: <admin_token>
```

### 3.1 原生管理接口

- `/v1/admin/models`
- `/v1/admin/provider-keys`
- `/v1/admin/model-provider-keys`
- `/v1/admin/users`
- `/v1/admin/usage-sessions`

### 3.2 Basalt 管理集成

统一入口：`/v1/admin/basalt/*`

常用：

- `/v1/admin/basalt/dashboard/stats`
- `/v1/admin/basalt/apps`
- `/v1/admin/basalt/users`
- `/v1/admin/basalt/roles`
- `/v1/admin/basalt/permissions`
- `/v1/admin/basalt/wallets`
- `/v1/admin/basalt/tenants`
- `/v1/admin/basalt/subscriptions`

## 4. 前端控制台

页面总数 32：

- 用户端 16 页：`/workspace/*`
- 管理端 16 页：`/admin*`

每页均支持：

- 主导航链接
- 上一页/下一页
- 全量页面链接表

