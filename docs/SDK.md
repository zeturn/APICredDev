# APICred SDK 文档

## 1. Python SDK 位置

- `sdk/python/apicred_sdk`

## 2. 安装

```bash
cd sdk/python
python -m pip install -e .
```

## 3. 基础用法

```python
from apicred_sdk import ApiCredClient, ApiCredConfig

client = ApiCredClient(ApiCredConfig(base_url="http://localhost:8002/v1"))
client.login("user@example.com", "password")
print(client.me())
```

## 4. 业务接口

```python
client.list_models()
client.create_token("prod-key", ["llm"])
client.wallet()
client.ledger()
client.redeem("CODE123")
```

## 5. Basalt 集成接口

```python
client.basalt("GET", "/wallet/balance")
client.basalt("GET", "/permissions")
client.basalt("GET", "/roles")
```

## 6. Basalt 管理接口

```python
admin = ApiCredClient(ApiCredConfig(base_url="http://localhost:8002/v1", admin_token="dev-admin-token"))
admin.admin_basalt("GET", "/dashboard/stats")
admin.admin_basalt("GET", "/users")
```

## 7. 生产建议

- 使用短超时 + 重试策略（网关侧）
- 按场景拆分业务 token 与管理员 token
- 对外统一封装异常处理与日志追踪

