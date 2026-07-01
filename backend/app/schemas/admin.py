from pydantic import BaseModel


class BrandUpsert(BaseModel):
    id: str | None = None
    name: str
    slug: str
    icon_slug: str | None = None
    icon_url: str | None = None
    enabled: bool = True


class ProviderUpsert(BaseModel):
    id: str | None = None
    name: str
    slug: str
    default_base_url: str | None = None
    icon_slug: str | None = None
    icon_url: str | None = None
    enabled: bool = True


class ProviderEndpointUpsert(BaseModel):
    id: str | None = None
    provider_id: str
    slug: str
    display_name: str
    base_url: str
    enabled: bool = True
    health_state: str = "healthy"
    cooldown_until: str | None = None


class PublicModelUpsert(BaseModel):
    id: str | None = None
    slug: str
    display_name: str
    description: str | None = None
    brand_id: str | None = None
    category: str = "llm"
    enabled: bool = True
    pricing: dict
    multiplier: float = 1


class UpstreamModelUpsert(BaseModel):
    id: str | None = None
    provider_id: str
    upstream_name: str
    display_name: str
    context_window: int | None = None
    capabilities: dict
    default_pricing: dict
    enabled: bool = True


class ProviderCredentialUpsert(BaseModel):
    id: str | None = None
    provider_endpoint_id: str
    display_name: str
    api_key: str | None = None
    enabled: bool = True
    health_state: str = "healthy"
    cooldown_until: str | None = None


class ModelRouteUpsert(BaseModel):
    id: str | None = None
    public_model_id: str
    upstream_model_id: str
    provider_credential_id: str | None = None
    base_url_override: str | None = None
    enabled: bool = True
    priority: int = 1
    weight: int = 1
    quota_unit: str = "tokens"
    quota_rules: dict

