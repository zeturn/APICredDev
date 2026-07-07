import pytest
from sqlalchemy import select

from app.core.config import Settings, settings
from app.core.secrets import decrypt_secret
from app.db.models.model_route import ModelRoute
from app.db.models.provider_credential import ProviderCredential
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.services.bootstrap import ensure_bootstrap_openai_credential, ensure_bootstrap_openrouter_credential


@pytest.mark.asyncio
async def test_openai_bootstrap_imports_credential_and_routes_models(db_session, monkeypatch):
    monkeypatch.setattr(settings, "bootstrap_openai_api_key", "sk-test-openai-123456")
    monkeypatch.setattr(settings, "bootstrap_openai_key_name", "OpenAI test credential")
    monkeypatch.setattr(settings, "bootstrap_openai_models", "gpt-5.4,gpt-4o-mini")

    credential = await ensure_bootstrap_openai_credential(db_session)

    assert credential is not None
    assert credential.display_name == "OpenAI test credential"
    assert credential.secret_last4 == "3456"
    assert decrypt_secret(credential.secret_encrypted) == "sk-test-openai-123456"

    public_models = (await db_session.execute(select(PublicModel).where(PublicModel.slug.in_(["gpt-5.4", "gpt-4o-mini"])))).scalars().all()
    assert {model.slug for model in public_models} == {"gpt-5.4", "gpt-4o-mini"}

    upstream_models = (await db_session.execute(select(UpstreamModel).where(UpstreamModel.upstream_name.in_(["gpt-5.4", "gpt-4o-mini"])))).scalars().all()
    assert {model.upstream_name for model in upstream_models} == {"gpt-5.4", "gpt-4o-mini"}

    routes = (await db_session.execute(select(ModelRoute).where(ModelRoute.provider_credential_id == credential.id))).scalars().all()
    assert len(routes) == 2
    assert all(route.enabled for route in routes)
    assert all(route.quota_unit == "tokens" for route in routes)


@pytest.mark.asyncio
async def test_openai_bootstrap_is_idempotent_and_updates_secret(db_session, monkeypatch):
    monkeypatch.setattr(settings, "bootstrap_openai_api_key", "sk-test-openai-old")
    monkeypatch.setattr(settings, "bootstrap_openai_key_name", "OpenAI test credential")
    monkeypatch.setattr(settings, "bootstrap_openai_models", "gpt-5.4")

    first = await ensure_bootstrap_openai_credential(db_session)

    monkeypatch.setattr(settings, "bootstrap_openai_api_key", "sk-test-openai-new")
    second = await ensure_bootstrap_openai_credential(db_session)

    credentials = (await db_session.execute(select(ProviderCredential).where(ProviderCredential.display_name == "OpenAI test credential"))).scalars().all()
    routes = (await db_session.execute(select(ModelRoute).where(ModelRoute.provider_credential_id == first.id))).scalars().all()

    assert first.id == second.id
    assert len(credentials) == 1
    assert len(routes) == 1
    assert decrypt_secret(second.secret_encrypted) == "sk-test-openai-new"


def test_openai_bootstrap_api_key_env_alias(monkeypatch):
    monkeypatch.setenv("APICRED_OPENAI_API_KEY", "sk-test-env-alias")

    loaded = Settings()

    assert loaded.bootstrap_openai_api_key == "sk-test-env-alias"


@pytest.mark.asyncio
async def test_openrouter_bootstrap_imports_credential_and_routes_models(db_session, monkeypatch):
    monkeypatch.setattr(settings, "bootstrap_openrouter_api_key", "sk-or-test-openrouter-123456")
    monkeypatch.setattr(settings, "bootstrap_openrouter_key_name", "OpenRouter test credential")
    monkeypatch.setattr(settings, "bootstrap_openrouter_models", "tencent/hy3:free")

    credential = await ensure_bootstrap_openrouter_credential(db_session)

    assert credential is not None
    assert credential.display_name == "OpenRouter test credential"
    assert credential.secret_last4 == "3456"
    assert decrypt_secret(credential.secret_encrypted) == "sk-or-test-openrouter-123456"

    public_model = (
        await db_session.execute(select(PublicModel).where(PublicModel.slug == "tencent/hy3:free"))
    ).scalar_one_or_none()
    assert public_model is not None
    assert public_model.enabled is True

    upstream_model = (
        await db_session.execute(select(UpstreamModel).where(UpstreamModel.upstream_name == "tencent/hy3:free"))
    ).scalar_one_or_none()
    assert upstream_model is not None
    assert upstream_model.enabled is True

    routes = (await db_session.execute(select(ModelRoute).where(ModelRoute.provider_credential_id == credential.id))).scalars().all()
    assert len(routes) == 1
    assert routes[0].enabled is True
    assert routes[0].quota_unit == "tokens"


def test_openrouter_bootstrap_api_key_env_alias(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-openrouter-env")

    loaded = Settings()

    assert loaded.bootstrap_openrouter_api_key == "sk-test-openrouter-env"
