---
id: admin-model-catalog
title: 管理模型、搜索模型与 API Key
slug: /admin-model-catalog
---

APICred 使用同一套路由模型管理 LLM、搜索、embedding、图像、音频等能力。管理员不需要为搜索能力维护单独系统；搜索供应商也走 provider、endpoint、credential、public model、upstream model 和 route。

## 核心对象

```text
public_models
  -> model_routes
       -> upstream_models
       -> provider_credentials
            -> provider_endpoints
                 -> providers
```

含义：

- `public_models`：用户看到、购买、调用或被 tool 引用的产品模型。
- `upstream_models`：真实上游模型名，例如 `gpt-4o-mini` 或 `web-search`。
- `providers`：供应商身份，例如 `openai`、`anthropic`、`brave-search`。
- `provider_endpoints`：上游入口和 base URL。
- `provider_credentials`：API key/credential，加密保存。
- `model_routes`：产品模型到真实上游模型和 credential 的路由，可配置备用、权重、优先级和 quota。

## 管理入口

控制台入口：

- `/admin/brands`
- `/admin/providers`
- `/admin/provider-endpoints`
- `/admin/provider-credentials`
- `/admin/public-models`
- `/admin/upstream-models`
- `/admin/model-routes`

每个页面都支持：

- 列表/卡片列表
- 点击查看详情
- JSON 新增或更新对象

带 `id` 的 JSON 会更新对象；不带 `id` 的 JSON 会创建新对象。

## 注册一个搜索模型

以 Brave Search 为例。

### 1. Provider

```json
{
  "name": "Brave Search",
  "slug": "brave-search",
  "icon_slug": "brave",
  "icon_url": "https://brave.com/static-assets/images/brave-logo-sans-text.svg",
  "enabled": true
}
```

### 2. Endpoint

```json
{
  "provider_id": "<brave-search-provider-id>",
  "slug": "web",
  "display_name": "Brave Web Search",
  "base_url": "https://api.search.brave.com/res/v1",
  "enabled": true,
  "health_state": "healthy"
}
```

### 3. Credential

```json
{
  "provider_endpoint_id": "<endpoint-id>",
  "display_name": "Brave Search main key",
  "api_key": "<brave-api-key>",
  "enabled": true,
  "health_state": "healthy"
}
```

明文 `api_key` 只用于提交；后端会加密保存，并只返回 `secret_last4` 和 `has_secret`。

### 4. Public Model

```json
{
  "slug": "brave-web-search",
  "display_name": "Brave Web Search",
  "description": "Search product model exposed as APICred tool capacity.",
  "brand_id": "<brand-id>",
  "category": "search",
  "enabled": true,
  "pricing": {
    "mode": "request",
    "unit": "request",
    "price": 0
  },
  "multiplier": 1
}
```

### 5. Upstream Model

```json
{
  "provider_id": "<brave-search-provider-id>",
  "upstream_name": "web-search",
  "display_name": "Brave Web Search",
  "context_window": null,
  "capabilities": {
    "search": true,
    "web": true
  },
  "default_pricing": {
    "mode": "request",
    "unit": "request"
  },
  "enabled": true
}
```

### 6. Model Route

```json
{
  "public_model_id": "<public-model-id>",
  "upstream_model_id": "<upstream-model-id>",
  "provider_credential_id": "<credential-id>",
  "priority": 1,
  "weight": 1,
  "enabled": true,
  "quota_unit": "requests",
  "quota_rules": {
    "day": 2000
  }
}
```

## 备用 Key 与用尽切换

给同一个 public search model 建多条 route 即可实现备用：

- `priority` 小的先用
- 同 priority 下按 `weight` 加权随机
- credential 被禁用、处于 cooldown 或 quota 用尽时会跳过
- `quota_rules` 支持 `minute`、`hour`、`day`、`month`

示例：

```json
{
  "priority": 1,
  "weight": 3,
  "quota_unit": "requests",
  "quota_rules": {
    "minute": 60,
    "day": 2000
  }
}
```

## 用户如何调用搜索

调用仍然使用 OpenAI 风格的 `/v1/chat/completions`。

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
        "description": "Search the web through an APICred search model",
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

支持的托管搜索 tool 名称：

- `brave_web_search`
- `brave_search`
- `web_search`
- `search_web`

如果不传 `search_model`，默认使用 `SEARCH_DEFAULT_MODEL_SLUG`，默认值是 `brave-web-search`。

## Bootstrap

本地开发可设置：

```env
BRAVE_SEARCH_API_KEY=...
```

启动时会自动创建或更新默认 Brave Search provider、endpoint、credential、public model、upstream model 和 route。

生产环境建议通过管理后台录入和轮换 key，环境变量只用于初始 bootstrap。
