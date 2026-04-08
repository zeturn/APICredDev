import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.model import Model
from app.db.models.provider import Provider
from app.db.models.provider_key import ProviderKey
from app.db.models.user import User
from app.db.models.wallet import Wallet


logger = logging.getLogger(__name__)


def _assert_bootstrap_admin_password() -> None:
    password = (settings.admin_password or "").strip()
    lowered = password.lower()
    weak_values = {"admin123", "password", "123456", "changeme", "admin"}
    if len(password) < 12 or lowered in weak_values:
        raise RuntimeError("startup bootstrap requires strong ADMIN_PASSWORD (>=12 chars, non-default)")


DEFAULT_BRANDS = [
    {"name": "OpenAI", "slug": "openai", "icon_slug": "openai", "icon_url": "https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg", "enabled": True},
    {"name": "Google", "slug": "google", "icon_slug": "google", "icon_url": "https://unpkg.com/@lobehub/icons-static-svg@latest/icons/google.svg", "enabled": True},
    {"name": "Anthropic", "slug": "anthropic", "icon_slug": "anthropic", "icon_url": "https://unpkg.com/@lobehub/icons-static-svg@latest/icons/anthropic.svg", "enabled": True},
    {"name": "Unknown", "slug": "unknown", "icon_slug": None, "icon_url": None, "enabled": True},
]


DEFAULT_PROVIDERS = [
    {"name": "OpenAI", "slug": "openai", "default_base_url": "https://api.openai.com", "icon_slug": "openai", "icon_url": "https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg", "enabled": True},
    {"name": "Google Gemini", "slug": "gemini", "default_base_url": "https://generativelanguage.googleapis.com", "icon_slug": "gemini", "icon_url": "https://unpkg.com/@lobehub/icons-static-svg@latest/icons/gemini.svg", "enabled": True},
    {"name": "Anthropic", "slug": "anthropic", "default_base_url": "https://api.anthropic.com", "icon_slug": "anthropic", "icon_url": "https://unpkg.com/@lobehub/icons-static-svg@latest/icons/anthropic.svg", "enabled": True},
    {"name": "OpenRouter", "slug": "openrouter", "default_base_url": "https://openrouter.ai/api", "icon_slug": "openrouter", "icon_url": "https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openrouter.svg", "enabled": True},
]


DEFAULT_PROVIDER_KEYS = [
]


DEFAULT_MODELS = [
    {"name": "gpt-5.4", "brand_slug": "openai", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 2.5, "cached_input_per_million": 0.25, "output_per_million": 15}},
    {"name": "gpt-5.4-pro", "brand_slug": "openai", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 10, "cached_input_per_million": 1, "output_per_million": 50}},
    {"name": "gpt-5.4-mini", "brand_slug": "openai", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.75, "cached_input_per_million": 0.08, "output_per_million": 4.5}},
    {"name": "gpt-5.4-nano", "brand_slug": "openai", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.2, "cached_input_per_million": 0.03, "output_per_million": 1.25}},
    {"name": "gpt-realtime-1.5", "brand_slug": "openai", "category": "realtime", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 4, "cached_input_per_million": 0.4, "output_per_million": 16}},
    {"name": "gpt-realtime-mini", "brand_slug": "openai", "category": "realtime", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.6, "cached_input_per_million": 0.06, "output_per_million": 2.4}},
    {"name": "gpt-image-1.5", "brand_slug": "openai", "category": "image", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 5, "cached_input_per_million": 0.5, "output_per_million": 25, "image_prices": {"low": 0.02, "medium": 0.07, "high": 0.28}}},
    {"name": "gpt-image-1-mini", "brand_slug": "openai", "category": "image", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 1.15, "cached_input_per_million": 0.12, "output_per_million": 5.75, "image_prices": {"low": 0.01, "medium": 0.03, "high": 0.12}}},
    {"name": "gpt-4o-transcribe", "brand_slug": "openai", "category": "audio", "enabled": True, "multiplier": 1, "pricing": {"mode": "request", "unit": "minute", "price": 0.006}},
    {"name": "gpt-4o-mini-transcribe", "brand_slug": "openai", "category": "audio", "enabled": True, "multiplier": 1, "pricing": {"mode": "request", "unit": "minute", "price": 0.003}},
    {"name": "text-embedding-3-small", "brand_slug": "openai", "category": "embedding", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.02, "output_per_million": 0}},
    {"name": "text-embedding-3-large", "brand_slug": "openai", "category": "embedding", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.13, "output_per_million": 0}},
    {"name": "omni-moderation-latest", "brand_slug": "openai", "category": "moderation", "enabled": True, "multiplier": 1, "pricing": {"mode": "free"}},
    {"name": "gemini-3.1-pro-preview", "brand_slug": "google", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 2, "output_per_million": 12, "tiers": [{"max_input_tokens": 200000, "input_per_million": 2, "output_per_million": 12}, {"min_input_tokens": 200001, "input_per_million": 4, "output_per_million": 18}]}},
    {"name": "gemini-3-flash-preview", "brand_slug": "google", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.5, "output_per_million": 3}},
    {"name": "gemini-3.1-flash-lite-preview", "brand_slug": "google", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.25, "output_per_million": 1.5}},
    {"name": "gemini-3.1-flash-live-preview", "brand_slug": "google", "category": "realtime", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.75, "output_per_million": 4.5, "audio_input_per_million": 3, "audio_output_per_million": 12}},
    {"name": "gemini-2.5-flash-image", "brand_slug": "google", "category": "image", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.3, "output_per_million": 30}},
    {"name": "gemini-3.1-flash-image-preview", "brand_slug": "google", "category": "image", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.5, "output_per_million": 3, "image_output_per_million": 60}},
    {"name": "gemini-3-pro-image-preview", "brand_slug": "google", "category": "image", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "priority_input_per_million": 3.6, "priority_output_per_million": 21.6, "priority_image_output_per_million": 216}},
    {"name": "gemini-embedding-001", "brand_slug": "google", "category": "embedding", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.15, "output_per_million": 0}},
    {"name": "gemini-embedding-2-preview", "brand_slug": "google", "category": "embedding", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.2, "output_per_million": 0, "image_input_per_million": 0.45, "audio_input_per_million": 6.5, "video_input_per_million": 12}},
    {"name": "gemini-robotics-er-1.5-preview", "brand_slug": "google", "category": "robotics", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.3, "output_per_million": 2.5}},
    {"name": "gemini-2.5-computer-use-preview", "brand_slug": "google", "category": "agent", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 1.25, "output_per_million": 10, "tiers": [{"max_input_tokens": 200000, "input_per_million": 1.25, "output_per_million": 10}, {"min_input_tokens": 200001, "input_per_million": 2.5, "output_per_million": 15}]}},
    {"name": "claude-opus-4.6", "brand_slug": "anthropic", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 5, "cached_input_per_million": 0.5, "output_per_million": 25, "cache_write_5m_per_million": 6.25, "cache_write_1h_per_million": 10}},
    {"name": "claude-sonnet-4.6", "brand_slug": "anthropic", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 3, "cached_input_per_million": 0.3, "output_per_million": 15, "cache_write_5m_per_million": 3.75, "cache_write_1h_per_million": 6}},
    {"name": "claude-haiku-4.5", "brand_slug": "anthropic", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 1, "cached_input_per_million": 0.1, "output_per_million": 5, "cache_write_5m_per_million": 1.25, "cache_write_1h_per_million": 2}},
    {"name": "claude-haiku-3.5", "brand_slug": "anthropic", "category": "llm", "enabled": True, "multiplier": 1, "pricing": {"mode": "token_segments", "input_per_million": 0.8, "cached_input_per_million": 0.08, "output_per_million": 4}},
]


async def ensure_admin_user(db: AsyncSession) -> None:
    _assert_bootstrap_admin_password()
    result = await db.execute(select(User).where(User.email == settings.admin_email))
    user = result.scalar_one_or_none()
    if user:
        return

    admin_id = str(uuid.uuid4())
    admin = User(id=admin_id, email=settings.admin_email, password_hash=hash_password(settings.admin_password))
    wallet = Wallet(user_id=admin_id, balance_credits=0)
    db.add(admin)
    db.add(wallet)
    await db.commit()
    logger.info("Default admin user created: %s", settings.admin_email)


async def ensure_default_brands(db: AsyncSession) -> None:
    created = 0
    for payload in DEFAULT_BRANDS:
        result = await db.execute(select(Brand).where(Brand.slug == payload["slug"]))
        brand = result.scalar_one_or_none()
        if brand:
            brand.name = payload["name"]
            brand.icon_slug = payload["icon_slug"]
            brand.icon_url = payload["icon_url"]
            brand.enabled = payload["enabled"]
            continue
        db.add(Brand(**payload))
        created += 1
    await db.commit()

    unknown_brand = (await db.execute(select(Brand).where(Brand.slug == "unknown"))).scalar_one()
    models = (await db.execute(select(Model).where(Model.brand_id.is_(None)))).scalars().all()
    if models:
        for model in models:
            model.brand_id = unknown_brand.id
        await db.commit()

    if created:
        logger.info("Default brands created: %s", created)


async def ensure_default_providers(db: AsyncSession) -> None:
    created = 0
    for payload in DEFAULT_PROVIDERS:
        result = await db.execute(select(Provider).where(Provider.slug == payload["slug"]))
        provider = result.scalar_one_or_none()
        if provider:
            provider.name = payload["name"]
            provider.default_base_url = payload["default_base_url"]
            provider.icon_slug = payload["icon_slug"]
            provider.icon_url = payload["icon_url"]
            provider.enabled = payload["enabled"]
            continue
        db.add(Provider(**payload))
        created += 1
    await db.commit()
    if created:
        logger.info("Default providers created: %s", created)


async def ensure_default_provider_keys(db: AsyncSession) -> None:
    providers = {
        provider.slug: provider
        for provider in (await db.execute(select(Provider))).scalars().all()
    }
    existing_keys = (await db.execute(select(ProviderKey))).scalars().all()
    for provider_key in existing_keys:
        if provider_key.provider_id:
            continue
        provider = providers.get(provider_key.provider)
        if provider:
            provider_key.provider_id = provider.id

    await db.commit()


async def ensure_default_models(db: AsyncSession) -> None:
    brands = {brand.slug: brand for brand in (await db.execute(select(Brand))).scalars().all()}
    created = 0
    for payload in DEFAULT_MODELS:
        brand = brands.get(payload["brand_slug"])
        model_payload = {
            "name": payload["name"],
            "brand_id": brand.id if brand else None,
            "category": payload["category"],
            "enabled": payload["enabled"],
            "multiplier": payload["multiplier"],
            "pricing": payload["pricing"],
        }
        result = await db.execute(select(Model).where(Model.name == payload["name"]))
        model = result.scalar_one_or_none()
        if model:
            model.brand_id = model_payload["brand_id"]
            model.category = model_payload["category"]
            model.enabled = model_payload["enabled"]
            model.multiplier = model_payload["multiplier"]
            model.pricing = model_payload["pricing"]
            continue
        db.add(Model(**model_payload))
        created += 1
    await db.commit()
    if created:
        logger.info("Default models created: %s", created)
