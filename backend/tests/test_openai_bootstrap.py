import pytest
from sqlalchemy import select

from app.core.config import Settings, settings
from app.core.secrets import decrypt_secret
from app.db.models.model import Model
from app.db.models.model_provider_key import ModelProviderKey
from app.db.models.provider_key import ProviderKey
from app.services.bootstrap import ensure_bootstrap_openai_provider_key


@pytest.mark.asyncio
async def test_openai_bootstrap_imports_key_and_links_models(db_session, monkeypatch):
    monkeypatch.setattr(settings, "bootstrap_openai_api_key", "sk-test-openai-123456")
    monkeypatch.setattr(settings, "bootstrap_openai_key_name", "OpenAI test key")
    monkeypatch.setattr(settings, "bootstrap_openai_models", "gpt-5.4,gpt-4o-mini")

    provider_key = await ensure_bootstrap_openai_provider_key(db_session)

    assert provider_key is not None
    assert provider_key.provider == "openai"
    assert provider_key.key_name == "OpenAI test key"
    assert provider_key.secret_last4 == "3456"
    assert decrypt_secret(provider_key.secret_encrypted) == "sk-test-openai-123456"

    models = (await db_session.execute(select(Model).where(Model.name.in_(["gpt-5.4", "gpt-4o-mini"])))).scalars().all()
    assert {model.name for model in models} == {"gpt-5.4", "gpt-4o-mini"}

    links = (await db_session.execute(select(ModelProviderKey).where(ModelProviderKey.provider_key_id == provider_key.id))).scalars().all()
    assert len(links) == 2
    assert all(link.enabled for link in links)
    assert all(link.quota_unit == "tokens" for link in links)


@pytest.mark.asyncio
async def test_openai_bootstrap_is_idempotent_and_updates_secret(db_session, monkeypatch):
    monkeypatch.setattr(settings, "bootstrap_openai_api_key", "sk-test-openai-old")
    monkeypatch.setattr(settings, "bootstrap_openai_key_name", "OpenAI test key")
    monkeypatch.setattr(settings, "bootstrap_openai_models", "gpt-5.4")

    first = await ensure_bootstrap_openai_provider_key(db_session)

    monkeypatch.setattr(settings, "bootstrap_openai_api_key", "sk-test-openai-new")
    second = await ensure_bootstrap_openai_provider_key(db_session)

    provider_keys = (await db_session.execute(select(ProviderKey).where(ProviderKey.provider == "openai"))).scalars().all()
    links = (await db_session.execute(select(ModelProviderKey).where(ModelProviderKey.provider_key_id == first.id))).scalars().all()

    assert first.id == second.id
    assert len(provider_keys) == 1
    assert len(links) == 1
    assert decrypt_secret(second.secret_encrypted) == "sk-test-openai-new"


def test_openai_bootstrap_api_key_env_alias(monkeypatch):
    monkeypatch.setenv("APICRED_OPENAI_API_KEY", "sk-test-env-alias")

    loaded = Settings()

    assert loaded.bootstrap_openai_api_key == "sk-test-env-alias"
