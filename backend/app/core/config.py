from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    app_secret: str = "dev-secret"
    token_salt: str = "dev-token-salt"
    jwt_issuer: str = "apicred"
    jwt_exp_minutes: int = 60 * 24

    database_url: str = "postgresql+asyncpg://apicred:apicred@localhost:5403/apicred"
    redis_url: str = "redis://localhost:6303/0"

    admin_token: str = "dev-admin-token"
    admin_email: str = "admin@example.com"
    admin_password: str = "admin123"

    stripe_webhook_secret: str = "whsec_dev"
    stripe_price_credits: int = 1000

    max_key_attempts: int = 3
    debug_endpoints_enabled: bool = True

    basalt_base_url: str = "http://localhost:8101"
    basalt_internal_base_url: str = "http://localhost:8101"
    basalt_service_token: str = ""
    basalt_oauth_client_id: str = ""
    basalt_oauth_client_secret: str = ""
    basalt_oauth_scopes: str = "openid profile email"
    basalt_oauth_audience: str = ""
    basalt_s2s_client_id: str = ""
    basalt_s2s_client_secret: str = ""
    basalt_timeout_seconds: float = 15.0
    basalt_max_retries: int = 2
    apicred_public_base_url: str = "http://localhost:8103"
    frontend_base_url: str = "http://localhost:5106"


settings = Settings()

