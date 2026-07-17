from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    app_env: str = "dev"
    app_secret: str = "dev-secret"
    token_salt: str = "dev-token-salt"
    encryption_key: str = Field("", validation_alias=AliasChoices("ENCRYPTION_KEY", "APICRED_ENCRYPTION_KEY"))
    apicred_encryption_key_id: str = Field("v3", validation_alias=AliasChoices("APICRED_ENCRYPTION_KEY_ID", "ENCRYPTION_KEY_ID"))
    apicred_previous_encryption_keys: str = Field("", validation_alias=AliasChoices("APICRED_PREVIOUS_ENCRYPTION_KEYS", "PREVIOUS_ENCRYPTION_KEYS"))
    jwt_issuer: str = "apicred"
    jwt_exp_minutes: int = 60 * 24
    auth_cookie_name: str = "apicred_access_token"
    auth_cookie_samesite: str = "lax"

    database_url: str = "postgresql+asyncpg://apicred:apicred@localhost:5403/apicred"
    redis_url: str = "redis://localhost:6303/0"

    admin_jwt_audience: str = "apicred-admin"
    admin_jwt_exp_minutes: int = 15
    admin_email: str = "admin@example.com"
    admin_password: str = ""

    allow_local_password_auth: bool = False
    production_allow_local_password_auth: bool = False
    allow_test_cli_local_auth: bool = True
    test_cli_auth_secret: str = ""

    production_mode: bool = False
    max_key_attempts: int = 3
    debug_endpoints_enabled: bool = False
    startup_create_tables_enabled: bool = False
    startup_schema_compat_enabled: bool = False
    startup_bootstrap_enabled: bool = False
    bootstrap_openai_api_key: str = Field("", validation_alias=AliasChoices("APICRED_OPENAI_API_KEY", "BOOTSTRAP_OPENAI_API_KEY"))
    bootstrap_openai_key_name: str = "OpenAI free daily shared traffic"
    bootstrap_openai_base_url: str = "https://api.openai.com"
    bootstrap_openai_models: str = (
        "gpt-5.4,gpt-5.2,gpt-5.1,gpt-5.1-codex,gpt-5,gpt-5-codex,gpt-5-chat-latest,"
        "gpt-4.1,gpt-4o,o1,o3,"
        "gpt-5.4-mini,gpt-5.4-nano,gpt-5.1-codex-mini,gpt-5-mini,gpt-5-nano,"
        "gpt-4.1-mini,gpt-4.1-nano,gpt-4o-mini,o1-mini,o3-mini,o4-mini,codex-mini-latest"
    )
    bootstrap_openrouter_api_key: str = Field(
        "",
        validation_alias=AliasChoices(
            "APICRED_OPENROUTER_API_KEY",
            "BOOTSTRAP_OPENROUTER_API_KEY",
            "OPENROUTER_API_KEY",
        ),
    )
    bootstrap_openrouter_key_name: str = "OpenRouter main key"
    bootstrap_openrouter_base_url: str = "https://openrouter.ai/api"
    bootstrap_openrouter_models: str = "tencent/hy3:free"

    basalt_base_url: str = "http://localhost:8101"
    basalt_internal_base_url: str = "http://localhost:8101"
    basalt_service_token: str = ""
    basalt_oauth_client_id: str = Field("", validation_alias=AliasChoices("BASALT_OAUTH_CLIENT_ID", "APICRED_BASALTPASS_CLIENT_ID"))
    basalt_oauth_client_secret: str = Field("", validation_alias=AliasChoices("BASALT_OAUTH_CLIENT_SECRET", "APICRED_BASALTPASS_CLIENT_SECRET"))
    basalt_oauth_scopes: str = "openid profile email"
    basalt_oauth_audience: str = ""
    basalt_s2s_client_id: str = ""
    basalt_s2s_client_secret: str = ""
    basalt_credit_currency: str = "CREDIT"
    basalt_credit_scale: int = 1000000
    basalt_tenant_admin_role_codes: str = "tenant,owner,admin,tenant_admin,aadmin,apicred_admin"
    basalt_admin_permission_codes: str = "admin_console,apicred.admin"
    basalt_rbac_enforce: bool = True
    basalt_rbac_strict_user_binding: bool = True
    basalt_default_tenant_id: str = ""
    basalt_timeout_seconds: float = 15.0
    basalt_max_retries: int = 2
    # Synavis Core（OCaml 计费引擎）地址，第一阶段联调用
    synavis_base_url: str = "http://localhost:10622"
    brave_search_api_key: str = ""
    brave_search_base_url: str = "https://api.search.brave.com/res/v1"
    brave_search_default_country: str = "US"
    brave_search_default_lang: str = "en"
    brave_search_default_count: int = 5
    search_default_model_slug: str = "brave-web-search"
    apicred_public_base_url: str = "http://localhost:8103"
    frontend_base_url: str = "http://localhost:5106"
    cors_origins: list[str] = ["http://localhost:5106", "http://127.0.0.1:5106"]
    audit_store_message_content: bool = True
    audit_redaction_enabled: bool = True
    audit_retention_days: int = 90
    audit_hash_content: bool = False
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = ""


settings = Settings()


def _is_empty(value: str | None) -> bool:
    return not str(value or "").strip()


def _has_wildcard_cors(origins: list[str]) -> bool:
    for origin in origins or []:
        normalized = str(origin or "").strip().lower()
        if normalized == "*" or "://" in normalized and "*" in normalized:
            return True
    return False


def validate_production_settings(current: Settings) -> None:
    if not current.production_mode:
        return

    errors: list[str] = []
    insecure_values = {"app_secret": {"", "dev-secret"}, "token_salt": {"", "dev-token-salt"}}
    for name, blocked in insecure_values.items():
        if getattr(current, name) in blocked:
            errors.append(f"{name} is insecure")
    if _is_empty(current.database_url):
        errors.append("database_url is required")
    if _is_empty(current.redis_url):
        errors.append("redis_url is required")
    if _is_empty(current.admin_password):
        errors.append("admin_password is required")
    if _is_empty(current.encryption_key):
        errors.append("encryption_key is required")
    if current.debug_endpoints_enabled:
        errors.append("debug_endpoints_enabled must be false")
    if current.startup_create_tables_enabled:
        errors.append("startup_create_tables_enabled must be false (use alembic migrations)")
    if current.startup_schema_compat_enabled:
        errors.append("startup_schema_compat_enabled must be false")
    if current.startup_bootstrap_enabled:
        errors.append("startup_bootstrap_enabled must be false")
    if current.allow_test_cli_local_auth:
        errors.append("allow_test_cli_local_auth must be false")
    if current.allow_local_password_auth and not current.production_allow_local_password_auth:
        errors.append("allow_local_password_auth requires production_allow_local_password_auth=true")
    if _has_wildcard_cors(current.cors_origins):
        errors.append("cors_origins must not include wildcard")
    if errors:
        raise RuntimeError(f"insecure production settings: {', '.join(sorted(errors))}")
