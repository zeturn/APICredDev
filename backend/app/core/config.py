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
    basalt_tenant_admin_role_codes: str = "tenant,owner,admin,tenant_admin,aadmin"
    basalt_rbac_enforce: bool = True
    basalt_rbac_strict_user_binding: bool = True
    basalt_default_tenant_id: str = ""
    basalt_timeout_seconds: float = 15.0
    basalt_max_retries: int = 2
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

    if current.startup_bootstrap_enabled:
        raise RuntimeError("startup bootstrap must be disabled in production mode")

