# APICred 开发文档

## 1. 项目结构

- `backend/app/api/v1`: 所有 API 入口
- `backend/app/services`: 业务服务层
- `backend/app/db/models`: 数据模型
- `backend/app/catalog`: 默认 provider/model/route YAML 目录
- `backend/alembic/versions`: 数据库 schema migration
- `frontend/src/navigation`: 前端路由编排
- `frontend/src/pages/admin`: 管理端页面
- `sdk/python`: Python SDK

## 2. Basalt 集成实现

### 2.1 客户端

文件：`backend/app/services/basaltpass_client.py`

能力：

- 上游 HTTP 请求封装
- 重试（429/502/503/504）
- 超时与异常容错
- JSON 结果统一解码

### 2.2 路由层

文件：`backend/app/api/v1/basalt.py`

能力：

- `USER_PROXY_SPECS`：用户业务代理路由
- `ADMIN_PROXY_SPECS`：管理代理路由
- 统一透传 query / body / path params
- 用户上下文透传到 Basalt

## 3. 增加新代理接口

1. 在 `USER_PROXY_SPECS` 或 `ADMIN_PROXY_SPECS` 添加 `ProxyRouteSpec`
2. 指定：
   - APICred 暴露路径
   - Basalt 上游路径
   - 方法（GET/POST/PUT/DELETE）
3. 补充测试并验证

## 4. 前端新增页面

1. 在 `frontend/src/navigation/consoleRoutes.ts` 增加路由项
2. 自动出现在：
   - 侧边栏导航
   - 全量页面跳转表
   - 上一页/下一页逻辑

## 5. 新增模型或搜索供应商

如果只是注册默认数据，优先改 YAML：

- `backend/app/catalog/default_providers.yaml`
- `backend/app/catalog/default_models.yaml`
- `backend/app/catalog/default_routes.yaml`

如果需要新协议适配器：

1. 在 `backend/app/services/providers/` 增加 adapter
2. 在 provider factory 注册 provider slug
3. 为 public/upstream models 和 routes 增加 catalog seed
4. 增加测试和文档

搜索供应商一般不需要新增 adapter。只要能由 `search_service` 支持，就可通过 `category=search` 的 public model、provider credential 和 model route 管理 API key、quota 和 fallback。

## 6. 审计数据

LLM 调用会写入：

- `usage_sessions`：计费、token、route 和状态
- `audit_llm_messages`：message 粒度审计

新增会影响审计内容的代码时，要验证：

- 用户 `/v1/audit/conversations` 分页
- 用户软删除
- 管理员 `/v1/admin/users/{user_id}/audit-conversations` 分页

## 7. 代码质量建议

- 所有新增接口均需有测试
- 外部服务访问必须具备超时和重试
- 所有管理操作必须走 `X-Admin-Authorization: Bearer <admin_access_token>`
- 业务错误统一走 APICred 错误格式

