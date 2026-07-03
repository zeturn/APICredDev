import base64
import os

import pytest

from app.core.config import settings
from app.core.secrets import decrypt_secret, encrypt_secret, secret_version
from app.db.models.provider import Provider
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.services.secret_rotation_service import rotate_provider_credentials


def _b64_key() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")


@pytest.mark.asyncio
async def test_encrypt_decrypt_current_key(monkeypatch):
    monkeypatch.setattr(settings, "encryption_key", _b64_key())
    monkeypatch.setattr(settings, "apicred_encryption_key_id", "v3")
    monkeypatch.setattr(settings, "apicred_previous_encryption_keys", "")
    token = encrypt_secret("sk-prod-123")
    assert token.startswith("v3:")
    assert decrypt_secret(token) == "sk-prod-123"


@pytest.mark.asyncio
async def test_decrypt_previous_key(monkeypatch):
    previous_key = _b64_key()
    monkeypatch.setattr(settings, "encryption_key", previous_key)
    monkeypatch.setattr(settings, "apicred_encryption_key_id", "v2")
    monkeypatch.setattr(settings, "apicred_previous_encryption_keys", "")
    old_token = encrypt_secret("prev-key-value")

    current_key = _b64_key()
    monkeypatch.setattr(settings, "encryption_key", current_key)
    monkeypatch.setattr(settings, "apicred_encryption_key_id", "v3")
    monkeypatch.setattr(settings, "apicred_previous_encryption_keys", f"v2:{previous_key}")
    assert decrypt_secret(old_token) == "prev-key-value"


def test_legacy_v2_fallback(monkeypatch):
    monkeypatch.setattr(settings, "encryption_key", "")
    monkeypatch.setattr(settings, "apicred_encryption_key_id", "v3")
    monkeypatch.setattr(settings, "apicred_previous_encryption_keys", "")
    token = encrypt_secret("legacy-fallback")
    assert token.startswith("v2:")
    assert decrypt_secret(token) == "legacy-fallback"


async def _seed_credential(db_session, secret: str):
    provider = Provider(name="OpenAI", slug="openai", enabled=True)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    endpoint = ProviderEndpoint(
        provider_id=provider.id,
        slug="default",
        display_name="default",
        base_url="https://api.openai.com",
        enabled=True,
        health_state="healthy",
    )
    db_session.add(endpoint)
    await db_session.commit()
    await db_session.refresh(endpoint)
    credential = ProviderCredential(
        provider_endpoint_id=endpoint.id,
        display_name="main",
        secret_encrypted=secret,
        secret_last4="1234",
        enabled=True,
        health_state="healthy",
    )
    db_session.add(credential)
    await db_session.commit()
    await db_session.refresh(credential)
    return credential


@pytest.mark.asyncio
async def test_rotation_dry_run_and_actual_and_idempotent(db_session, monkeypatch):
    monkeypatch.setattr(settings, "encryption_key", "")
    monkeypatch.setattr(settings, "apicred_encryption_key_id", "v3")
    monkeypatch.setattr(settings, "apicred_previous_encryption_keys", "")
    old_token = encrypt_secret("super-secret-value")
    credential = await _seed_credential(db_session, old_token)

    current_key = _b64_key()
    monkeypatch.setattr(settings, "encryption_key", current_key)
    monkeypatch.setattr(settings, "apicred_encryption_key_id", "v3")
    monkeypatch.setattr(settings, "apicred_previous_encryption_keys", "")

    dry = await rotate_provider_credentials(db_session, dry_run=True)
    assert dry["changed"] == 1
    assert dry["items"][0]["status"] == "would_rotate"
    refreshed = await db_session.get(ProviderCredential, credential.id)
    assert secret_version(refreshed.secret_encrypted) == "v2"

    actual = await rotate_provider_credentials(db_session, dry_run=False)
    assert actual["changed"] == 1
    refreshed = await db_session.get(ProviderCredential, credential.id)
    assert secret_version(refreshed.secret_encrypted) == "v3"
    assert decrypt_secret(refreshed.secret_encrypted) == "super-secret-value"

    second = await rotate_provider_credentials(db_session, dry_run=False)
    assert second["changed"] == 0
    assert second["items"][0]["status"] == "noop"


def test_bad_key_fails_safely(monkeypatch):
    monkeypatch.setattr(settings, "encryption_key", "bad")
    monkeypatch.setattr(settings, "apicred_encryption_key_id", "v3")
    monkeypatch.setattr(settings, "apicred_previous_encryption_keys", "")
    with pytest.raises(ValueError):
        encrypt_secret("x")


@pytest.mark.asyncio
async def test_secret_not_leaked_in_rotation_report(db_session, monkeypatch):
    monkeypatch.setattr(settings, "encryption_key", "")
    old_token = encrypt_secret("very-sensitive-value")
    await _seed_credential(db_session, old_token)
    monkeypatch.setattr(settings, "encryption_key", _b64_key())
    monkeypatch.setattr(settings, "apicred_encryption_key_id", "v3")
    report = await rotate_provider_credentials(db_session, dry_run=True)
    dumped = str(report)
    assert "very-sensitive-value" not in dumped
    assert "credential_id" in dumped
