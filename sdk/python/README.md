# APICred Python SDK

`apicred-sdk` 提供生产可用的 Python 接入封装，支持：

- 认证：注册/登录/me
- 用户业务：token、模型、钱包、账本、充值
- BasaltPass 集成：`/v1/basalt/*`
- Basalt 管理集成：`/v1/admin/basalt/*`

## 安装

```bash
cd sdk/python
python -m pip install -e .
```

## 快速开始

```python
from apicred_sdk import ApiCredClient, ApiCredConfig

client = ApiCredClient(
    ApiCredConfig(
        base_url="http://localhost:8002/v1",
        timeout_seconds=20,
    )
)

client.login("user@example.com", "password")
print(client.me())
print(client.wallet())

# 访问 Basalt 集成业务接口
print(client.basalt("GET", "/wallet/balance"))
```

## 管理接口

```python
from apicred_sdk import ApiCredClient, ApiCredConfig

client = ApiCredClient(ApiCredConfig(base_url="http://localhost:8002/v1", admin_token="dev-admin-token"))
stats = client.admin_basalt("GET", "/dashboard/stats")
print(stats)
```

