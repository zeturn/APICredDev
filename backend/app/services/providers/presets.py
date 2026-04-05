PROVIDER_PRESETS = [
    {
        "provider": "openai",
        "label": "OpenAI",
        "base_url": "https://api.openai.com",
        "protocol": "openai_compat",
        "notes": "Official OpenAI Chat Completions compatible endpoint.",
    },
    {
        "provider": "openrouter",
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api",
        "protocol": "openai_compat",
        "notes": "OpenAI-compatible API aggregation layer.",
    },
    {
        "provider": "deepseek",
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "protocol": "openai_compat",
        "notes": "Use DeepSeek API key with OpenAI-compatible chat completions.",
    },
    {
        "provider": "groq",
        "label": "Groq",
        "base_url": "https://api.groq.com/openai",
        "protocol": "openai_compat",
        "notes": "Groq OpenAI-compatible endpoint.",
    },
    {
        "provider": "xai",
        "label": "xAI",
        "base_url": "https://api.x.ai",
        "protocol": "openai_compat",
        "notes": "xAI Grok API with OpenAI-compatible chat completions.",
    },
    {
        "provider": "siliconflow",
        "label": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn",
        "protocol": "openai_compat",
        "notes": "SiliconFlow OpenAI-compatible endpoint.",
    },
    {
        "provider": "moonshot",
        "label": "Moonshot",
        "base_url": "https://api.moonshot.cn",
        "protocol": "openai_compat",
        "notes": "Moonshot AI OpenAI-compatible endpoint.",
    },
    {
        "provider": "together",
        "label": "Together AI",
        "base_url": "https://api.together.xyz",
        "protocol": "openai_compat",
        "notes": "Together AI OpenAI-compatible endpoint.",
    },
    {
        "provider": "fireworks",
        "label": "Fireworks AI",
        "base_url": "https://api.fireworks.ai/inference",
        "protocol": "openai_compat",
        "notes": "Fireworks OpenAI-compatible endpoint.",
    },
    {
        "provider": "anthropic",
        "label": "Anthropic Claude",
        "base_url": "https://api.anthropic.com",
        "protocol": "anthropic",
        "notes": "Uses Anthropic Messages API and native streaming.",
    },
    {
        "provider": "gemini",
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com",
        "protocol": "gemini",
        "notes": "Uses Gemini generateContent and streamGenerateContent APIs.",
    },
]


def list_provider_presets() -> list[dict]:
    return [dict(item) for item in PROVIDER_PRESETS]


def get_provider_default_base_url(provider: str) -> str | None:
    normalized = (provider or "").strip().lower()
    for item in PROVIDER_PRESETS:
        if item["provider"] == normalized:
            return item.get("base_url")
    return None
