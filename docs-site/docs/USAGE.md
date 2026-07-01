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
- `/workspace/usage`：按模型和调用记录统计；分页查看自己的对话记录并软删除
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

## 5. 联网搜索 Tools

APICred 支持托管搜索 tool。调用方式仍然是同一个 Chat Completions 接口；请求中声明搜索 tool 后，APICred 会先通过已注册的搜索模型产品执行搜索，再把搜索结果注入给 LLM。

示例：

```json
{
  "model": "apicred-fast",
  "messages": [
    {
      "role": "user",
      "content": "Search the web and answer: what is Brave Search API?"
    }
  ],
  "tools": [
    {
      "type": "function",
      "search_model": "brave-web-search",
      "function": {
        "name": "brave_web_search",
        "description": "Search the web through APICred",
        "parameters": {
          "type": "object",
          "properties": {
            "query": { "type": "string" }
          },
          "required": ["query"]
        }
      }
    }
  ]
}
```

说明：

- `search_model` 是 APICred 的搜索 public model，例如 `brave-web-search`。
- 如果不传 `search_model`，后端使用默认搜索模型。
- 搜索调用本身也走管理员配置的 route、credential、quota 和 fallback。
- 支持的 tool 名称：`brave_web_search`、`brave_search`、`web_search`、`search_web`。

## 6. 对话记录与软删除

每次 LLM 调用会被保存为审计消息：

- `request`：用户输入
- `tool`：APICred 托管工具上下文，例如搜索结果
- `response`：模型回复

用户可在 `/workspace/usage` 分页查看自己的对话记录。点击删除后，这条对话会从用户视图中隐藏，但管理员仍可在审计视图中查看，用于合规和排障。

## 7. 关键接口速查

用户会话接口（浏览器登录态）：

- `GET /v1/auth/me`
- `GET /v1/models`
- `GET /v1/billing/wallet`
- `GET /v1/billing/usage`
- `GET /v1/audit/conversations?page=1&page_size=10`
- `DELETE /v1/audit/conversations/{usage_session_id}`

API Token 接口（服务间调用）：

- `POST /v1/chat/completions`

## 8. 常见问题

### 8.1 模型列表为空

通常是环境初始化后未导入默认模型。

处理方式：请管理员执行模型种子初始化（brands/providers/models）。

### 8.2 登录后反复跳回登录页

排查：

- 检查浏览器是否拦截 Cookie
- 检查 APICred 与前端域名/端口是否与配置一致
- 检查 BasaltPass 回调地址是否配置正确

### 8.3 调用返回 401 或 403

- 401：Token 无效/缺失
- 403：权限不足（scope 或 Basalt RBAC）

### 8.4 搜索 tool 没有生效

排查：

- `tools[].function.name` 是否为受支持的搜索 tool 名称。
- `search_model` 是否存在且 `category=search`。
- 搜索模型是否有启用的 route 和 credential。
- 对应 credential 是否被禁用、冷却或 quota 用尽。

## 9. 安全与行为说明

- Stripe webhook 在 APICred 侧已禁用（统一走 BasaltPass 金融链路）。
- Provider 的 `base_url` 会执行安全校验，禁止危险 scheme（如 `file://`）。
- 用户权限校验默认强制 Basalt 身份绑定。
- 搜索和 LLM API key 均由管理员录入 provider credentials，并加密保存。

