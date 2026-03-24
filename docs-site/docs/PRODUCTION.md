# APICred 生产部署指南

## 1. 基础原则

- 所有秘钥通过环境变量注入
- 不在代码中写死数据库、Redis、第三方 token
- 对 Basalt 上游调用必须具备超时和重试
- 全量 API 接入日志与告警

## 2. 推荐部署拓扑

- APICred Backend（FastAPI）x N
- APICred Frontend（静态资源 + CDN）
- PostgreSQL（主从或托管）
- Redis（高可用）
- BasaltPass（独立部署域）
- API Gateway / WAF / HTTPS

## 3. 必要环境变量

- `DATABASE_URL`
- `REDIS_URL`
- `APP_SECRET`
- `TOKEN_SALT`
- `ADMIN_TOKEN`
- `STRIPE_WEBHOOK_SECRET`
- `BASALT_BASE_URL`
- `BASALT_SERVICE_TOKEN`
- `BASALT_TIMEOUT_SECONDS`
- `BASALT_MAX_RETRIES`

## 4. 发布前检查

1. 执行测试与覆盖率门禁
2. 校验管理 token 策略和访问控制
3. 校验 Basalt 连接和关键代理接口
4. 校验前端 32 页面导航与权限跳转
5. 校验 SDK 示例可运行

## 5. 运行命令示例

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

```bash
cd frontend
npm run build
```

