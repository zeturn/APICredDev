import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.loader import load_default_models, load_default_providers, load_default_routes
from app.core.config import settings
from app.core.secrets import encrypt_secret
from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.model import Model
from app.db.models.provider import Provider
from app.db.models.model_provider_key import ModelProviderKey
from app.db.models.model_route import ModelRoute
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_key import ProviderKey
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.db.models.user import User
from app.db.models.wallet import Wallet


logger = logging.getLogger(__name__)


def _assert_bootstrap_admin_password() -> None:
    password = (settings.admin_password or "").strip()
    lowered = password.lower()
    weak_values = {"admin123", "password", "123456", "changeme", "admin"}
    if len(password) < 12 or lowered in weak_values:
        raise RuntimeError("startup bootstrap requires strong ADMIN_PASSWORD (>=12 chars, non-default)")


def _public_models_by_slug() -> dict[str, dict]:
    return {item["slug"]: item for item in load_default_models().get("public_models", [])}


def configured_openai_bootstrap_models() -> list[str]:
    return [item.strip() for item in (settings.bootstrap_openai_models or "").split(",") if item.strip()]


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
    for payload in load_default_providers().get("brands", []):
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
    catalog = load_default_providers()
    for payload in catalog.get("providers", []):
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

    providers = {provider.slug: provider for provider in (await db.execute(select(Provider))).scalars().all()}
    credential_created = 0
    for payload in catalog.get("provider_credentials", []):
        provider = providers.get(payload["provider"])
        if not provider:
            continue
        result = await db.execute(
            select(ProviderCredential)
            .where(ProviderCredential.provider_id == provider.id)
            .where(ProviderCredential.display_name == payload["display_name"])
        )
        credential = result.scalar_one_or_none()
        credential_payload = {
            "provider_id": provider.id,
            "display_name": payload["display_name"],
            "enabled": payload.get("enabled", True),
            "health_state": payload.get("health_state", "healthy"),
        }
        if credential:
            credential.enabled = credential_payload["enabled"]
            credential.health_state = credential_payload["health_state"]
            continue
        db.add(ProviderCredential(**credential_payload))
        credential_created += 1

    await db.commit()
    if credential_created:
        logger.info("Default provider credentials created: %s", credential_created)


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
    providers = {provider.slug: provider for provider in (await db.execute(select(Provider))).scalars().all()}
    catalog = load_default_models()
    public_models = _public_models_by_slug()

    public_created = 0
    for payload in catalog.get("public_models", []):
        result = await db.execute(select(PublicModel).where(PublicModel.slug == payload["slug"]))
        public_model = result.scalar_one_or_none()
        model_payload = {
            "slug": payload["slug"],
            "display_name": payload["display_name"],
            "description": payload.get("description"),
            "brand_id": brands[payload["brand_slug"]].id if payload.get("brand_slug") in brands else None,
            "category": payload.get("category", "llm"),
            "pricing": payload.get("pricing", {}),
            "multiplier": payload.get("multiplier", 1),
            "enabled": payload.get("enabled", True),
        }
        if public_model:
            for key, value in model_payload.items():
                setattr(public_model, key, value)
            continue
        db.add(PublicModel(**model_payload))
        public_created += 1

    upstream_created = 0
    for payload in catalog.get("upstream_models", []):
        provider = providers.get(payload["provider"])
        if not provider:
            continue
        result = await db.execute(
            select(UpstreamModel)
            .where(UpstreamModel.provider_id == provider.id)
            .where(UpstreamModel.upstream_name == payload["upstream_name"])
        )
        upstream_model = result.scalar_one_or_none()
        upstream_payload = {
            "provider_id": provider.id,
            "upstream_name": payload["upstream_name"],
            "display_name": payload["display_name"],
            "context_window": payload.get("context_window"),
            "capabilities": payload.get("capabilities", {}),
            "default_pricing": payload.get("default_pricing", {}),
            "enabled": payload.get("enabled", True),
        }
        if upstream_model:
            for key, value in upstream_payload.items():
                setattr(upstream_model, key, value)
            continue
        db.add(UpstreamModel(**upstream_payload))
        upstream_created += 1
    await db.commit()

    created = 0
    for payload in catalog.get("legacy_models", []):
        brand = brands.get(payload["brand_slug"])
        public_model = public_models.get(payload["name"], {})
        model_payload = {
            "name": payload["name"],
            "brand_id": brand.id if brand else None,
            "category": payload.get("category", public_model.get("category", "llm")),
            "enabled": payload.get("enabled", public_model.get("enabled", True)),
            "multiplier": payload.get("multiplier", 1),
            "pricing": payload.get("pricing", public_model.get("pricing", {})),
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
    if public_created:
        logger.info("Default public models created: %s", public_created)
    if upstream_created:
        logger.info("Default upstream models created: %s", upstream_created)
    if created:
        logger.info("Default models created: %s", created)


async def ensure_default_routes(db: AsyncSession) -> None:
    public_models = {model.slug: model for model in (await db.execute(select(PublicModel))).scalars().all()}
    upstream_models = {
        f"{provider.slug}:{model.upstream_name}": model
        for model, provider in (
            await db.execute(select(UpstreamModel, Provider).join(Provider, Provider.id == UpstreamModel.provider_id))
        ).all()
    }
    credentials = {
        credential.display_name: credential
        for credential in (await db.execute(select(ProviderCredential))).scalars().all()
    }

    created = 0
    for payload in load_default_routes().get("routes", []):
        public_model = public_models.get(payload["public_model"])
        upstream_model = upstream_models.get(payload["upstream_model"])
        if not public_model or not upstream_model:
            continue
        credential = credentials.get(payload.get("credential", ""))
        result = await db.execute(
            select(ModelRoute)
            .where(ModelRoute.public_model_id == public_model.id)
            .where(ModelRoute.upstream_model_id == upstream_model.id)
            .where(ModelRoute.provider_credential_id == (credential.id if credential else None))
        )
        route = result.scalar_one_or_none()
        route_payload = {
            "public_model_id": public_model.id,
            "upstream_model_id": upstream_model.id,
            "provider_credential_id": credential.id if credential else None,
            "base_url_override": payload.get("base_url_override"),
            "enabled": payload.get("enabled", True),
            "priority": payload.get("priority", 1),
            "weight": payload.get("weight", 1),
            "quota_unit": payload.get("quota_unit", "tokens"),
            "quota_rules": payload.get("quota_rules", {}),
        }
        if route:
            for key, value in route_payload.items():
                setattr(route, key, value)
            continue
        db.add(ModelRoute(**route_payload))
        created += 1
    await db.commit()
    if created:
        logger.info("Default model routes created: %s", created)


async def ensure_bootstrap_openai_provider_key(db: AsyncSession) -> ProviderKey | None:
    api_key = (settings.bootstrap_openai_api_key or "").strip()
    if not api_key:
        return None

    await ensure_default_brands(db)
    await ensure_default_providers(db)
    await ensure_default_models(db)

    provider = (await db.execute(select(Provider).where(Provider.slug == "openai"))).scalar_one_or_none()
    if not provider:
        provider = Provider(
            name="OpenAI",
            slug="openai",
            default_base_url=settings.bootstrap_openai_base_url,
            icon_slug="openai",
            icon_url="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg",
            enabled=True,
        )
        db.add(provider)
        await db.commit()
        await db.refresh(provider)

    key_name = (settings.bootstrap_openai_key_name or "OpenAI bootstrap key").strip()
    result = await db.execute(select(ProviderKey).where(ProviderKey.provider == "openai").where(ProviderKey.key_name == key_name))
    provider_key = result.scalar_one_or_none()
    secret_last4 = api_key[-4:]
    if not provider_key:
        provider_key = ProviderKey(
            provider_id=provider.id,
            provider="openai",
            key_name=key_name,
            secret_encrypted=encrypt_secret(api_key),
            secret_last4=secret_last4,
            enabled=True,
            health_state="healthy",
        )
        db.add(provider_key)
    else:
        provider_key.provider_id = provider.id
        provider_key.secret_encrypted = encrypt_secret(api_key)
        provider_key.secret_last4 = secret_last4
        provider_key.enabled = True
        provider_key.health_state = "healthy"
        provider_key.cooldown_until = None
    await db.commit()
    await db.refresh(provider_key)

    result = await db.execute(
        select(ProviderCredential)
        .where(ProviderCredential.provider_id == provider.id)
        .where(ProviderCredential.display_name == key_name)
    )
    credential = result.scalar_one_or_none()
    credential_payload = {
        "provider_id": provider.id,
        "display_name": key_name,
        "secret_encrypted": encrypt_secret(api_key),
        "secret_last4": secret_last4,
        "enabled": True,
        "health_state": "healthy",
        "cooldown_until": None,
    }
    if not credential:
        db.add(ProviderCredential(**credential_payload))
    else:
        for field, value in credential_payload.items():
            setattr(credential, field, value)
    await db.commit()

    await ensure_openai_models_and_links(db, provider_key)
    await ensure_default_routes(db)
    logger.info("OpenAI bootstrap provider key configured: key_name=%s last4=%s", key_name, secret_last4)
    return provider_key


async def ensure_openai_models_and_links(db: AsyncSession, provider_key: ProviderKey) -> None:
    brand = (await db.execute(select(Brand).where(Brand.slug == "openai"))).scalar_one_or_none()
    if not brand:
        brand = Brand(
            name="OpenAI",
            slug="openai",
            icon_slug="openai",
            icon_url="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg",
            enabled=True,
        )
        db.add(brand)
        await db.commit()
        await db.refresh(brand)

    for model_name in configured_openai_bootstrap_models():
        model = (await db.execute(select(Model).where(Model.name == model_name))).scalar_one_or_none()
        if not model:
            model = Model(
                name=model_name,
                brand_id=brand.id,
                category="llm",
                enabled=True,
                multiplier=1,
                pricing={"mode": "free", "source": "openai_free_daily_shared_traffic"},
            )
            db.add(model)
            await db.commit()
            await db.refresh(model)
        else:
            model.brand_id = model.brand_id or brand.id
            model.enabled = True

        link = (
            await db.execute(
                select(ModelProviderKey)
                .where(ModelProviderKey.model_id == model.id)
                .where(ModelProviderKey.provider_key_id == provider_key.id)
            )
        ).scalar_one_or_none()
        if not link:
            db.add(
                ModelProviderKey(
                    model_id=model.id,
                    provider_key_id=provider_key.id,
                    enabled=True,
                    priority=1,
                    weight=1,
                    quota_unit="tokens",
                    quota_rules={},
                )
            )
        else:
            link.enabled = True
            link.priority = 1
            link.weight = max(link.weight or 1, 1)
            link.quota_unit = link.quota_unit or "tokens"
    await db.commit()
