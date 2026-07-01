from pydantic import BaseModel


class ModelItem(BaseModel):
    id: str
    name: str
    display_name: str | None = None
    brand_id: str | None = None
    brand_name: str | None = None
    brand_icon_url: str | None = None
    icon_url: str | None = None
    effective_icon_url: str | None = None
    category: str
    enabled: bool
    multiplier: float
    pricing: dict

