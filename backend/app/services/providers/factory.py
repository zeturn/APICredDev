from app.services.providers.anthropic import AnthropicAdapter
from app.services.providers.base import ProviderAdapter
from app.services.providers.gemini import GeminiAdapter
from app.services.providers.openai_compat import OpenAICompatAdapter
from app.services.providers.stubs import StubAdapter


OPENAI_COMPAT_PROVIDERS = {
    "openai",
    "openai_compat",
    "openrouter",
    "deepseek",
    "groq",
    "xai",
    "siliconflow",
    "moonshot",
    "together",
    "fireworks",
    "dashscope_compat",
}


def get_provider_adapter(provider_name: str) -> ProviderAdapter:
    normalized = (provider_name or "").strip().lower()
    if normalized in OPENAI_COMPAT_PROVIDERS:
        return OpenAICompatAdapter()
    if normalized in {"anthropic", "claude"}:
        return AnthropicAdapter()
    if normalized in {"gemini", "google", "google_ai", "googleai"}:
        return GeminiAdapter()
    if normalized == "stub":
        return StubAdapter()
    return OpenAICompatAdapter()
