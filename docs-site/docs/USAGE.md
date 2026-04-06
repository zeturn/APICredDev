# APICred 使用文档

## 1. 登录与认证

1. 调用 `POST /v1/auth/register` 注册账号
2. 调用 `POST /v1/auth/login` 获取 `access_token`
3. 后续业务请求使用：

```http
Authorization: Bearer <access_token>
```

## 2. 用户业务主流程

> 当前已接入统一 RBAC 依赖函数：`permission("read") / permission("write")`。
>
> 已迁移模块：`/v1/auth/me`、`/v1/models`、`/v1/tokens/*`、`/v1/billing/*`、`/v1/basalt/*(用户代理路由按 GET/写操作自动映射 read/write)`。

### 2.1 Token 管理

- `POST /v1/tokens`
- `GET /v1/tokens`
- `DELETE /v1/tokens/{token_id}`

### 2.2 钱包与账本

- `GET /v1/billing/wallet`
- `GET /v1/billing/ledger`
- `POST /v1/billing/redeem`

### 2.3 模型列表

- `GET /v1/models`（需要用户 Bearer，且具备 `read` 权限）

### 2.4 Basalt 用户能力（auth / permission / wallet）

主要入口均在 `GET|POST|PUT /v1/basalt/*`，核心分组：

- `auth`: `/v1/basalt/auth/*`
- `permission`: `/v1/basalt/permissions`、`/v1/basalt/roles`
- `wallet`: `/v1/basalt/wallet/*`

## 3. 管理后台主流程

管理请求支持两种方式：

```http
X-Admin-Token: <admin_token>
```

或使用租户管理员账号登录后得到的用户 Bearer Token（tenant `owner/admin/tenant/tenant_admin/aadmin` 角色会被识别为管理权限）：

```http
Authorization: Bearer <access_token>
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

## 5. LLM 调用鉴权（双轨）

`POST /v1/chat/completions` 当前使用双轨校验：

1. API Token scope：必须包含 `llm`
2. Basalt RBAC：`token_permission("write")`

说明：

- 这保证了与历史 API Token scope 行为兼容；
- 同时可以逐步过渡到 Basalt app 权限系统；
- 若未绑定 Basalt 账号且 `basalt_rbac_strict_user_binding=false`，仍保持兼容放行。

