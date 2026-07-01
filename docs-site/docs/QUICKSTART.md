---
id: quickstart
title: 5 分钟快速开始
slug: /quickstart
---

这份指南面向第一次使用 APICred 的用户，目标是在 5 分钟内完成从登录到 API 调用。

## 第 1 步：打开控制台并登录

1. 打开前端：

   http://localhost:5106/login

2. 点击“使用 BasaltPass 登录”。
3. 登录成功后进入用户工作台。

说明：当前默认仅支持 SSO 登录，本地注册/密码登录默认关闭。

## 第 2 步：确认模型可用

1. 进入“模型目录”页面：

   http://localhost:5106/workspace/models

2. 确认可见至少一个启用模型（如 gpt-5.4）。

如果模型为空，请联系管理员执行模型种子初始化。

## 第 3 步：创建 API Token

1. 进入 Token 页面：

   http://localhost:5106/workspace/tokens

2. 创建一个 Token，scope 至少包含 llm。
3. 保存返回的明文 Token（只展示一次）。

## 第 4 步：用 OpenAI SDK 调用 APICred

安装：

```bash
python -m pip install openai
```

示例：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8103/v1",
    api_key="YOUR_APICRED_TOKEN",
)

resp = client.chat.completions.create(
    model="gpt-5.4",
    messages=[{"role": "user", "content": "你好，请给我一句欢迎语"}],
)

print(resp.choices[0].message.content)
```

## 第 5 步：快速排错

- 401：Token 缺失或无效。
- 403：权限不足（scope 或 Basalt RBAC）。
- 404 model_not_found：模型名不存在或未启用。
- 502 upstream_failed：上游服务商 key 不可用或暂时失败。

## 可选：调用联网搜索

如果管理员已注册搜索模型，例如 `brave-web-search`，可以在同一个 Chat Completions 请求中声明搜索 tool：

```json
{
  "model": "apicred-fast",
  "messages": [
    {"role": "user", "content": "Search the web and answer: what is Brave Search API?"}
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
          "properties": {"query": {"type": "string"}},
          "required": ["query"]
        }
      }
    }
  ]
}
```

搜索请求会使用管理员配置的搜索模型 route 和 API key，支持备用 key 和按请求数限额。

## 下一步推荐

- 查看完整用户指南：USAGE
- 查看管理员模型目录：ADMIN_MODEL_CATALOG
- 查看 SDK 文档：SDK
- 查看 Basalt 联调：BASALTPASS_QUICKSTART
