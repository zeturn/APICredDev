# APICred 开发文档

## 1. 项目结构

- `backend/app/api/v1`: 所有 API 入口
- `backend/app/services`: 业务服务层
- `backend/app/db/models`: 数据模型
- `frontend/src/navigation`: 前端路由编排
- `frontend/src/pages/ConsolePage.tsx`: 通用控制台页面
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

## 5. 代码质量建议

- 所有新增接口均需有测试
- 外部服务访问必须具备超时和重试
- 所有管理操作必须走 `X-Admin-Token`
- 业务错误统一走 APICred 错误格式

