from datetime import datetime, timedelta, timezone

import pytest

from app.core.secrets import encrypt_secret
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.services import admin_service
from app.services.bootstrap import ensure_default_brands, ensure_default_models, ensure_default_providers, ensure_default_routes
from app.services.routing_service import get_route_candidates
from app.services.usage_service import calculate_cost


@pytest.mark.asyncio
async def test_default_catalog_bootstrap_creates_new_model_architecture(db_session):
    await ensure_default_brands(db_session)
    await ensure_default_providers(db_session)
    await ensure_default_models(db_session)
    await ensure_default_routes(db_session)

    public_models = await admin_service.list_public_models(db_session)
    upstream_models = await admin_service.list_upstream_models(db_session)
    provider_credentials = await admin_service.list_provider_credentials(db_session)
    model_routes = await admin_service.list_model_routes(db_session)

    assert public_models
    assert upstream_models
    assert provider_credentials
    assert model_routes


@pytest.mark.asyncio
async def test_admin_service_upserts_public_upstream_credential_and_route(db_session):
    provider = await admin_service.upsert_provider(
        db_session,
        {"slug": "svc-openai", "name": "Svc OpenAI", "default_base_url": "https://api.openai.com", "enabled": True},
    )
    public_model = await admin_service.upsert_public_model(
        db_session,
        {"slug": "svc-fast", "display_name": "Svc Fast", "category": "llm", "pricing": {"unit": "request", "price": 1}, "multiplier": 1, "enabled": True},
    )
    upstream_model = await admin_service.upsert_upstream_model(
        db_session,
        {"provider_id": provider.id, "upstream_name": "gpt-test", "display_name": "GPT Test", "capabilities": {}, "default_pricing": {}, "enabled": True},
    )
    endpoint = await admin_service.upsert_provider_endpoint(
        db_session,
        {"provider_id": provider.id, "slug": "default", "display_name": "Svc OpenAI Default", "base_url": "https://api.openai.com", "enabled": True, "health_state": "healthy"},
    )
    credential = await admin_service.upsert_provider_credential(
        db_session,
        {"provider_endpoint_id": endpoint.id, "display_name": "svc-key", "api_key": "sk-service", "enabled": True, "health_state": "healthy"},
    )
    route = await admin_service.upsert_model_route(
        db_session,
        {
            "public_model_id": public_model.id,
            "upstream_model_id": upstream_model.id,
            "provider_credential_id": credential.id,
            "base_url_override": "https://proxy.example.com",
            "enabled": True,
            "priority": 1,
            "weight": 2,
            "quota_unit": "requests",
            "quota_rules": {"minute": 100},
        },
    )

    assert route.base_url_override == "https://proxy.example.com"
    assert (await admin_service.list_api_supported_models(db_session))[0]["credential_name"] == "svc-key"


@pytest.mark.asyncio
async def test_routing_skips_disabled_and_cooldown_credentials(db_session):
    provider = Provider(slug="route-provider", name="Route Provider", default_base_url="https://example.com", enabled=True)
    public_model = PublicModel(slug="route-model", display_name="Route Model", category="llm", enabled=True, multiplier=1, pricing={})
    db_session.add_all([provider, public_model])
    await db_session.commit()
    await db_session.refresh(provider)
    await db_session.refresh(public_model)
    endpoint = ProviderEndpoint(provider_id=provider.id, slug="default", display_name="Route Default", base_url="https://example.com", enabled=True, health_state="healthy")
    db_session.add(endpoint)
    await db_session.commit()
    await db_session.refresh(endpoint)

    upstream_model = UpstreamModel(provider_id=provider.id, upstream_name="route-upstream", display_name="Route Upstream", capabilities={}, default_pricing={}, enabled=True)
    disabled = ProviderCredential(provider_endpoint_id=endpoint.id, display_name="disabled", secret_encrypted=encrypt_secret("A"), secret_last4="A", enabled=True, health_state="disabled")
    cooldown = ProviderCredential(
        provider_endpoint_id=endpoint.id,
        display_name="cooldown",
        secret_encrypted=encrypt_secret("B"),
        secret_last4="B",
        enabled=True,
        health_state="healthy",
        cooldown_until=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    ok = ProviderCredential(provider_endpoint_id=endpoint.id, display_name="ok", secret_encrypted=encrypt_secret("C"), secret_last4="C", enabled=True, health_state="healthy")
    db_session.add_all([upstream_model, disabled, cooldown, ok])
    await db_session.commit()
    await db_session.refresh(upstream_model)
    await db_session.refresh(disabled)
    await db_session.refresh(cooldown)
    await db_session.refresh(ok)

    db_session.add_all(
        [
            ModelRoute(public_model_id=public_model.id, upstream_model_id=upstream_model.id, provider_credential_id=disabled.id, enabled=True, priority=1, quota_unit="requests", quota_rules={}),
            ModelRoute(public_model_id=public_model.id, upstream_model_id=upstream_model.id, provider_credential_id=cooldown.id, enabled=True, priority=2, quota_unit="requests", quota_rules={}),
            ModelRoute(public_model_id=public_model.id, upstream_model_id=upstream_model.id, provider_credential_id=ok.id, enabled=True, priority=3, quota_unit="requests", quota_rules={}),
        ]
    )
    await db_session.commit()

    candidates = await get_route_candidates(db_session, public_model.id)
    assert len(candidates) == 1
    assert candidates[0].credential.id == ok.id


def test_calculate_cost_uses_public_model_pricing():
    model = PublicModel(slug="cost-model", display_name="Cost Model", category="llm", enabled=True, multiplier=2, pricing={"unit": "request", "price": 3})
    assert calculate_cost(model, total_tokens=100, request_count=2) == 12_000_000


def test_calculate_cost_returns_credit_points_from_usd_per_million():
    model = PublicModel(
        slug="point-cost-model",
        display_name="Point Cost Model",
        category="llm",
        enabled=True,
        multiplier=1,
        pricing={"mode": "token_segments", "input_per_million": 0.75, "output_per_million": 4.5},
    )

    assert calculate_cost(model, prompt_tokens=15, completion_tokens=8) == 48
