# APICred 测试文档

## 1. 运行测试

```bash
cd backend
pytest -q --cov=app --cov-report=term-missing
```

## 2. 新增测试点

- `tests/test_basalt_proxy_api.py`
  - 用户代理接口调用
  - 管理代理接口调用
  - 路由规模校验（管理 + 业务 >= 50）
- `tests/test_basaltpass_client.py`
  - 上游 503 场景重试成功

## 3. 覆盖率建议

全量项目覆盖率：

```bash
pytest -q --cov=app --cov-report=term-missing
```

全量覆盖率门禁（当前已验证可达 >=98%）：

```bash
pytest -q --cov=app --cov-report=term-missing --cov-fail-under=98
```

Basalt 集成模块覆盖率门禁（生产强制建议）：

```bash
pytest -q tests/test_basalt_proxy_api.py tests/test_basaltpass_client.py \
  --cov=app.api.v1.basalt \
  --cov=app.services.basaltpass_client \
  --cov-report=term-missing \
  --cov-fail-under=98
```

如未达到目标：

1. 优先补代理路由和异常处理分支
2. 补充值、账本、KeyPool、quota 分支
3. 对关键模块做参数化测试与失败路径测试

