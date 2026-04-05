from pydantic import BaseModel


class ModelUpsert(BaseModel):
    id: str | None = None
    name: str
    category: str
    enabled: bool
    multiplier: float
    pricing: dict


class ProviderKeyUpsert(BaseModel):
    id: str | None = None
    provider: str
    key_name: str
    secret_ref: str
    enabled: bool
    health_state: str
    cooldown_until: str | None = None


class ModelProviderKeyUpsert(BaseModel):
    id: str | None = None
    model_id: str
    provider_key_id: str
    base_url: str | None = None
    enabled: bool
    priority: int
    weight: int = 1
    quota_unit: str
    quota_rules: dict

