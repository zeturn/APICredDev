# APICred SDK 与 API 调用指南

## 1. 推荐调用方式

当前建议优先使用 OpenAI SDK（通过 `base_url` 指向 APICred），因为 APICred 已兼容 Chat Completions 请求形态。

## 2. OpenAI Python SDK（推荐）

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
	messages=[{"role": "user", "content": "请给我一段 20 字摘要"}],
	temperature=0.7,
)

print(resp.choices[0].message.content)
```

流式调用示例：

```python
stream = client.chat.completions.create(
	model="gpt-5.4",
	messages=[{"role": "user", "content": "逐步解释什么是向量数据库"}],
	stream=True,
)

for event in stream:
	delta = event.choices[0].delta.content if event.choices and event.choices[0].delta else None
	if delta:
		print(delta, end="", flush=True)
```

## 3. Token 要求

OpenAI SDK 中的 `api_key` 实际应填 APICred 的 API Token。

要求：

- Token 状态为 active
- Token scope 至少包含 `llm`
- 对应用户具备 Basalt 侧可用权限

## 4. 兼容性说明

已兼容：

- `POST /v1/chat/completions`
- `stream=True` 的 SSE 流式返回

注意：

- 模型名必须来自 APICred 当前可用模型。
- 若上游 key 不可用或配额受限，可能返回 `502 upstream_failed`。

## 5. 调试建议

- 先在控制台确认模型存在且已启用。
- 用一个最小请求验证：短 prompt + 非流式。
- 失败时记录 `X-Request-Id` 便于服务端排查。

## 6. 旧版本地 SDK 说明

仓库中保留了 `sdk/python` 目录用于历史兼容，但在新项目中优先建议使用 OpenAI SDK + APICred `base_url` 模式。

