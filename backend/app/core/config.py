from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    app_env: str = "dev"
    app_secret: str = "dev-secret"
    token_salt: str = "dev-token-salt"
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
    allow_test_cli_local_auth: bool = True
    test_cli_auth_secret: str = ""

    stripe_webhook_secret: str = "whsec_dev"
    stripe_price_credits: int = 1000

    production_mode: bool = False
    max_key_attempts: int = 3
    debug_endpoints_enabled: bool = False
    startup_create_tables_enabled: bool = False
    startup_schema_compat_enabled: bool = False
    startup_bootstrap_enabled: bool = False

    basalt_base_url: str = Field("http://localhost:8101", validation_alias=AliasChoices("BASALTPASS_BASE_URL", "BASALT_BASE_URL"))
    basalt_internal_base_url: str = Field(
        "http://localhost:8101",
        validation_alias=AliasChoices("BASALTPASS_INTERNAL_BASE_URL", "BASALT_INTERNAL_BASE_URL"),
    )
    basalt_service_token: str = Field("", validation_alias=AliasChoices("BASALTPASS_SERVICE_TOKEN", "BASALT_SERVICE_TOKEN"))
    basalt_oauth_client_id: str = Field("", validation_alias=AliasChoices("BASALTPASS_CLIENT_ID", "BASALT_OAUTH_CLIENT_ID"))
    basalt_oauth_client_secret: str = Field("", validation_alias=AliasChoices("BASALTPASS_CLIENT_SECRET", "BASALT_OAUTH_CLIENT_SECRET"))
    basalt_oauth_scopes: str = Field("openid profile email", validation_alias=AliasChoices("BASALTPASS_SCOPES", "BASALT_OAUTH_SCOPES"))
    basalt_oauth_audience: str = Field("", validation_alias=AliasChoices("BASALTPASS_AUDIENCE", "BASALT_OAUTH_AUDIENCE"))
    basalt_s2s_client_id: str = Field("", validation_alias=AliasChoices("BASALTPASS_S2S_CLIENT_ID", "BASALT_S2S_CLIENT_ID"))
    basalt_s2s_client_secret: str = Field("", validation_alias=AliasChoices("BASALTPASS_S2S_CLIENT_SECRET", "BASALT_S2S_CLIENT_SECRET"))
    basalt_credit_currency: str = "CREDIT"
    basalt_credit_scale: int = 1000000
    basalt_tenant_admin_role_codes: str = "tenant,owner,admin,tenant_admin,aadmin"
    basalt_rbac_enforce: bool = True
    basalt_rbac_strict_user_binding: bool = True
    basalt_default_tenant_id: str = ""
    basalt_timeout_seconds: float = Field(15.0, validation_alias=AliasChoices("BASALTPASS_TIMEOUT_SECONDS", "BASALT_TIMEOUT_SECONDS"))
    basalt_max_retries: int = Field(2, validation_alias=AliasChoices("BASALTPASS_MAX_RETRIES", "BASALT_MAX_RETRIES"))
    apicred_public_base_url: str = "http://localhost:8103"
    frontend_base_url: str = "http://localhost:5106"
    cors_origins: list[str] = ["http://localhost:5106", "http://127.0.0.1:5106"]


settings = Settings()


def validate_production_settings(current: Settings) -> None:
    if not current.production_mode:
        return

    insecure_values = {
        "app_secret": {"", "dev-secret"},
        "token_salt": {"", "dev-token-salt"},
    }
    bad = [name for name, blocked in insecure_values.items() if getattr(current, name) in blocked]
    if bad:
        raise RuntimeError(f"insecure production settings: {', '.join(sorted(bad))}")

    if current.debug_endpoints_enabled:
        raise RuntimeError("debug endpoints must be disabled in production mode")

    if current.startup_create_tables_enabled or current.startup_schema_compat_enabled or current.startup_bootstrap_enabled:
        raise RuntimeError("startup create-tables/schema-compat/bootstrap must be disabled in production mode")

