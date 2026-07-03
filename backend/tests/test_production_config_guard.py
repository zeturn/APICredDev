from types import SimpleNamespace

import pytest

from app.core.config import validate_production_settings


def _settings(**overrides):
    base = {
        "production_mode": True,
        "app_secret": "prod-secret",
        "token_salt": "prod-token-salt",
        "encryption_key": "Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MDEyMzQ1Njc4OTA",
        "debug_endpoints_enabled": False,
        "startup_create_tables_enabled": False,
        "startup_schema_compat_enabled": False,
        "startup_bootstrap_enabled": False,
        "allow_test_cli_local_auth": False,
        "allow_local_password_auth": False,
        "production_allow_local_password_auth": False,
        "cors_origins": ["https://console.apicred.example"],
        "database_url": "postgresql+asyncpg://user:pw@db/apicred",
        "redis_url": "redis://:pw@redis:6379/0",
        "admin_password": "strong-admin-password",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.parametrize(
    "field,value",
    [
        ("app_secret", "dev-secret"),
        ("token_salt", "dev-token-salt"),
        ("database_url", ""),
        ("redis_url", ""),
        ("admin_password", ""),
        ("encryption_key", ""),
    ],
)
def test_production_guard_rejects_insecure_or_empty_required_values(field, value):
    current = _settings(**{field: value})
    with pytest.raises(RuntimeError):
        validate_production_settings(current)


@pytest.mark.parametrize(
    "field,value",
    [
        ("debug_endpoints_enabled", True),
        ("startup_create_tables_enabled", True),
        ("startup_schema_compat_enabled", True),
        ("startup_bootstrap_enabled", True),
        ("allow_test_cli_local_auth", True),
    ],
)
def test_production_guard_rejects_unsafe_toggles(field, value):
    current = _settings(**{field: value})
    with pytest.raises(RuntimeError):
        validate_production_settings(current)


def test_production_guard_rejects_local_auth_without_explicit_allow():
    current = _settings(allow_local_password_auth=True, production_allow_local_password_auth=False)
    with pytest.raises(RuntimeError):
        validate_production_settings(current)


def test_production_guard_allows_local_auth_only_with_explicit_override():
    current = _settings(allow_local_password_auth=True, production_allow_local_password_auth=True)
    validate_production_settings(current)


def test_production_guard_rejects_wildcard_cors():
    with pytest.raises(RuntimeError):
        validate_production_settings(_settings(cors_origins=["*"]))
    with pytest.raises(RuntimeError):
        validate_production_settings(_settings(cors_origins=["https://*.example.com"]))


def test_dev_mode_still_works_with_relaxed_values():
    current = _settings(
        production_mode=False,
        app_secret="dev-secret",
        token_salt="dev-token-salt",
        database_url="",
        redis_url="",
        admin_password="",
        encryption_key="",
        debug_endpoints_enabled=True,
        startup_create_tables_enabled=True,
        startup_schema_compat_enabled=True,
        startup_bootstrap_enabled=True,
        allow_test_cli_local_auth=True,
        cors_origins=["*"],
    )
    validate_production_settings(current)
