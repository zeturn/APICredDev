# APICred 用户使用指南

本文档面向 API 调用方与普通控制台用户，覆盖从登录到调用的完整路径。

## 1. 登录方式（当前默认）

APICred 当前默认只支持 BasaltPass SSO 登录。

- 前端入口：`http://localhost:5106/login`
- 点击“使用 BasaltPass 登录”
- 登录成功后进入 `/workspace/dashboard`

说明：

- 本地 `register/login` 在常规环境默认关闭。
- 测试环境下仅受控 CLI 场景允许例外。

## 2. 用户端日常操作

登录后你会在用户工作台使用以下页面：

- `/workspace/dashboard`：余额、消费与最近账本
- `/workspace/models`：可用模型列表与定价
- `/workspace/tokens`：创建和管理 API Token
- `/workspace/usage`：按模型和调用记录统计
- `/workspace/topup`：充值与账本视图
- `/workspace/profile`：个人信息

## 3. 创建 API Token（给 SDK/服务端使用）

推荐流程：

1. 在控制台打开 Token 页面
2. 创建一个带 `llm` scope 的 Token
3. 保存返回的明文 Token（只展示一次）

调用 API 时使用：

```http
Authorization: Bearer <YOUR_API_TOKEN>
```

## 4. OpenAI SDK 调用 APICred

APICred 提供 OpenAI 风格的 Chat Completions 接口：

- `POST /v1/chat/completions`

Python 示例：

```python
from openai import OpenAI

client = OpenAI(
	base_url="http://localhost:8103/v1",
	api_key="YOUR_APICRED_TOKEN",
)

resp = client.chat.completions.create(
	model="gpt-5.4",
	messages=[{"role": "user", "content": "你好，帮我总结今天工作"}],
	temperature=0.7,
)

print(resp.choices[0].message.content)
```

建议：

- 优先使用 `chat.completions` 路径。
- `model` 必须是 APICred 当前可用模型名。

## 5. 关键接口速查

用户会话接口（浏览器登录态）：

- `GET /v1/auth/me`
- `GET /v1/models`
- `GET /v1/billing/wallet`
- `GET /v1/billing/usage`

API Token 接口（服务间调用）：

- `POST /v1/chat/completions`

## 6. 常见问题

### 6.1 模型列表为空

通常是环境初始化后未导入默认模型。

处理方式：请管理员执行模型种子初始化（brands/providers/models）。

### 6.2 登录后反复跳回登录页

排查：

- 检查浏览器是否拦截 Cookie
- 检查 APICred 与前端域名/端口是否与配置一致
- 检查 BasaltPass 回调地址是否配置正确

### 6.3 调用返回 401 或 403

- 401：Token 无效/缺失
- 403：权限不足（scope 或 Basalt RBAC）

## 7. 安全与行为说明

- Stripe webhook 在 APICred 侧已禁用（统一走 BasaltPass 金融链路）。
- Provider 的 `base_url` 会执行安全校验，禁止危险 scheme（如 `file://`）。
- 用户权限校验默认强制 Basalt 身份绑定。

