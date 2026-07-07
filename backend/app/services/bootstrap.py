import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.loader import load_default_models, load_default_providers, load_default_routes
from app.core.config import settings
from app.core.secrets import encrypt_secret
from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.provider import Provider
from app.db.models.model_route import ModelRoute
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
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


def configured_openrouter_bootstrap_models() -> list[str]:
    return [item.strip() for item in (settings.bootstrap_openrouter_models or "").split(",") if item.strip()]


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
            provider.default_base_url = payload.get("default_base_url")
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
    endpoint_created = 0
    for payload in catalog.get("provider_endpoints", []):
        provider = providers.get(payload["provider"])
        if not provider:
            continue
        result = await db.execute(
            select(ProviderEndpoint)
            .where(ProviderEndpoint.provider_id == provider.id)
            .where(ProviderEndpoint.slug == payload["slug"])
        )
        endpoint = result.scalar_one_or_none()
        endpoint_payload = {
            "provider_id": provider.id,
            "slug": payload["slug"],
            "display_name": payload["display_name"],
            "base_url": payload["base_url"],
            "enabled": payload.get("enabled", True),
            "health_state": payload.get("health_state", "healthy"),
            "cooldown_until": payload.get("cooldown_until"),
        }
        if endpoint:
            for key, value in endpoint_payload.items():
                setattr(endpoint, key, value)
            continue
        db.add(ProviderEndpoint(**endpoint_payload))
        endpoint_created += 1
    await db.commit()
    if endpoint_created:
        logger.info("Default provider endpoints created: %s", endpoint_created)

    endpoints = {
        f"{provider.slug}:{endpoint.slug}": endpoint
        for endpoint, provider in (
            await db.execute(select(ProviderEndpoint, Provider).join(Provider, Provider.id == ProviderEndpoint.provider_id))
        ).all()
    }
    credential_created = 0
    for payload in catalog.get("provider_credentials", []):
        endpoint = endpoints.get(f"{payload['provider']}:{payload.get('endpoint', 'default')}")
        if not endpoint:
            continue
        result = await db.execute(
            select(ProviderCredential)
            .where(ProviderCredential.provider_endpoint_id == endpoint.id)
            .where(ProviderCredential.display_name == payload["display_name"])
        )
        credential = result.scalar_one_or_none()
        credential_payload = {
            "provider_endpoint_id": endpoint.id,
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

    await db.commit()
    if public_created:
        logger.info("Default public models created: %s", public_created)
    if upstream_created:
        logger.info("Default upstream models created: %s", upstream_created)


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


async def ensure_bootstrap_openai_credential(db: AsyncSession) -> ProviderCredential | None:
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

    endpoint = (
        await db.execute(
            select(ProviderEndpoint)
            .where(ProviderEndpoint.provider_id == provider.id)
            .where(ProviderEndpoint.slug == "default")
        )
    ).scalar_one_or_none()
    if not endpoint:
        endpoint = ProviderEndpoint(
            provider_id=provider.id,
            slug="default",
            display_name="OpenAI Default",
            base_url=settings.bootstrap_openai_base_url,
            enabled=True,
            health_state="healthy",
        )
        db.add(endpoint)
        await db.commit()
        await db.refresh(endpoint)
    else:
        endpoint.base_url = settings.bootstrap_openai_base_url
        endpoint.enabled = True

    key_name = (settings.bootstrap_openai_key_name or "OpenAI bootstrap key").strip()
    secret_last4 = api_key[-4:]
    result = await db.execute(
        select(ProviderCredential)
        .where(ProviderCredential.provider_endpoint_id == endpoint.id)
        .where(ProviderCredential.display_name == key_name)
    )
    credential = result.scalar_one_or_none()
    credential_payload = {
        "provider_endpoint_id": endpoint.id,
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
    if credential:
        await db.refresh(credential)
    else:
        result = await db.execute(
            select(ProviderCredential)
            .where(ProviderCredential.provider_endpoint_id == endpoint.id)
            .where(ProviderCredential.display_name == key_name)
        )
        credential = result.scalar_one()

    await ensure_openai_models_and_routes(db, provider, credential)
    await ensure_default_routes(db)
    logger.info("OpenAI bootstrap credential configured: display_name=%s last4=%s", key_name, secret_last4)
    return credential


async def ensure_bootstrap_openrouter_credential(db: AsyncSession) -> ProviderCredential | None:
    api_key = (settings.bootstrap_openrouter_api_key or "").strip()
    if not api_key:
        return None

    await ensure_default_brands(db)
    await ensure_default_providers(db)
    await ensure_default_models(db)

    provider = (await db.execute(select(Provider).where(Provider.slug == "openrouter"))).scalar_one_or_none()
    if not provider:
        provider = Provider(
            name="OpenRouter",
            slug="openrouter",
            default_base_url=settings.bootstrap_openrouter_base_url,
            icon_slug="openrouter",
            icon_url="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openrouter.svg",
            enabled=True,
        )
        db.add(provider)
        await db.commit()
        await db.refresh(provider)

    endpoint = (
        await db.execute(
            select(ProviderEndpoint)
            .where(ProviderEndpoint.provider_id == provider.id)
            .where(ProviderEndpoint.slug == "default")
        )
    ).scalar_one_or_none()
    if not endpoint:
        endpoint = ProviderEndpoint(
            provider_id=provider.id,
            slug="default",
            display_name="OpenRouter Default",
            base_url=settings.bootstrap_openrouter_base_url,
            enabled=True,
            health_state="healthy",
        )
        db.add(endpoint)
        await db.commit()
        await db.refresh(endpoint)
    else:
        endpoint.base_url = settings.bootstrap_openrouter_base_url
        endpoint.enabled = True

    key_name = (settings.bootstrap_openrouter_key_name or "OpenRouter bootstrap key").strip()
    secret_last4 = api_key[-4:]
    result = await db.execute(
        select(ProviderCredential)
        .where(ProviderCredential.provider_endpoint_id == endpoint.id)
        .where(ProviderCredential.display_name == key_name)
    )
    credential = result.scalar_one_or_none()
    credential_payload = {
        "provider_endpoint_id": endpoint.id,
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
    if credential:
        await db.refresh(credential)
    else:
        result = await db.execute(
            select(ProviderCredential)
            .where(ProviderCredential.provider_endpoint_id == endpoint.id)
            .where(ProviderCredential.display_name == key_name)
        )
        credential = result.scalar_one()

    await ensure_openrouter_models_and_routes(db, provider, credential)
    await ensure_default_routes(db)
    logger.info("OpenRouter bootstrap credential configured: display_name=%s last4=%s", key_name, secret_last4)
    return credential


async def ensure_bootstrap_brave_search_credential(db: AsyncSession) -> ProviderCredential | None:
    api_key = (settings.brave_search_api_key or "").strip()
    if not api_key:
        return None

    await ensure_default_brands(db)
    await ensure_default_providers(db)
    await ensure_default_models(db)
    await ensure_default_routes(db)

    provider = (await db.execute(select(Provider).where(Provider.slug == "brave-search"))).scalar_one_or_none()
    if not provider:
        return None
    endpoint = (
        await db.execute(
            select(ProviderEndpoint)
            .where(ProviderEndpoint.provider_id == provider.id)
            .where(ProviderEndpoint.slug == "web")
        )
    ).scalar_one_or_none()
    if not endpoint:
        endpoint = ProviderEndpoint(
            provider_id=provider.id,
            slug="web",
            display_name="Brave Web Search",
            base_url=settings.brave_search_base_url,
            enabled=True,
            health_state="healthy",
        )
        db.add(endpoint)
        await db.commit()
        await db.refresh(endpoint)
    else:
        endpoint.base_url = settings.brave_search_base_url
        endpoint.enabled = True

    key_name = "Brave Search main key"
    result = await db.execute(
        select(ProviderCredential)
        .where(ProviderCredential.provider_endpoint_id == endpoint.id)
        .where(ProviderCredential.display_name == key_name)
    )
    credential = result.scalar_one_or_none()
    payload = {
        "provider_endpoint_id": endpoint.id,
        "display_name": key_name,
        "secret_encrypted": encrypt_secret(api_key),
        "secret_last4": api_key[-4:],
        "enabled": True,
        "health_state": "healthy",
        "cooldown_until": None,
    }
    if not credential:
        credential = ProviderCredential(**payload)
        db.add(credential)
    else:
        for key, value in payload.items():
            setattr(credential, key, value)
    await db.commit()
    await db.refresh(credential)
    logger.info("Brave Search bootstrap credential configured: display_name=%s last4=%s", key_name, api_key[-4:])
    return credential


async def ensure_openai_models_and_routes(db: AsyncSession, provider: Provider, credential: ProviderCredential) -> None:
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
        public_model = (await db.execute(select(PublicModel).where(PublicModel.slug == model_name))).scalar_one_or_none()
        if not public_model:
            public_model = PublicModel(
                slug=model_name,
                display_name=model_name,
                brand_id=brand.id,
                category="llm",
                enabled=True,
                multiplier=1,
                pricing={"mode": "free", "source": "openai_free_daily_shared_traffic"},
            )
            db.add(public_model)
            await db.commit()
            await db.refresh(public_model)
        else:
            public_model.brand_id = public_model.brand_id or brand.id
            public_model.enabled = True

        upstream_model = (
            await db.execute(
                select(UpstreamModel)
                .where(UpstreamModel.provider_id == provider.id)
                .where(UpstreamModel.upstream_name == model_name)
            )
        ).scalar_one_or_none()
        if not upstream_model:
            upstream_model = UpstreamModel(
                provider_id=provider.id,
                upstream_name=model_name,
                display_name=model_name,
                capabilities={"chat": True, "streaming": True},
                default_pricing={},
                enabled=True,
            )
            db.add(upstream_model)
            await db.commit()
            await db.refresh(upstream_model)
        else:
            upstream_model.enabled = True

        link = (
            await db.execute(
                select(ModelRoute)
                .where(ModelRoute.public_model_id == public_model.id)
                .where(ModelRoute.upstream_model_id == upstream_model.id)
                .where(ModelRoute.provider_credential_id == credential.id)
            )
        ).scalar_one_or_none()
        if not link:
            db.add(
                ModelRoute(
                    public_model_id=public_model.id,
                    upstream_model_id=upstream_model.id,
                    provider_credential_id=credential.id,
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


async def ensure_openrouter_models_and_routes(db: AsyncSession, provider: Provider, credential: ProviderCredential) -> None:
    for model_name in configured_openrouter_bootstrap_models():
        public_model = (await db.execute(select(PublicModel).where(PublicModel.slug == model_name))).scalar_one_or_none()
        if not public_model:
            public_model = PublicModel(
                slug=model_name,
                display_name=model_name,
                category="llm",
                enabled=True,
                multiplier=1,
                pricing={"mode": "free", "source": "openrouter_bootstrap"},
            )
            db.add(public_model)
            await db.commit()
            await db.refresh(public_model)
        else:
            public_model.enabled = True

        upstream_model = (
            await db.execute(
                select(UpstreamModel)
                .where(UpstreamModel.provider_id == provider.id)
                .where(UpstreamModel.upstream_name == model_name)
            )
        ).scalar_one_or_none()
        if not upstream_model:
            upstream_model = UpstreamModel(
                provider_id=provider.id,
                upstream_name=model_name,
                display_name=model_name,
                capabilities={"chat": True, "streaming": True, "reasoning": True},
                default_pricing={},
                enabled=True,
            )
            db.add(upstream_model)
            await db.commit()
            await db.refresh(upstream_model)
        else:
            upstream_model.enabled = True

        link = (
            await db.execute(
                select(ModelRoute)
                .where(ModelRoute.public_model_id == public_model.id)
                .where(ModelRoute.upstream_model_id == upstream_model.id)
                .where(ModelRoute.provider_credential_id == credential.id)
            )
        ).scalar_one_or_none()
        if not link:
            db.add(
                ModelRoute(
                    public_model_id=public_model.id,
                    upstream_model_id=upstream_model.id,
                    provider_credential_id=credential.id,
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
