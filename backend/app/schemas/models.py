from pydantic import BaseModel


class ModelItem(BaseModel):
    id: str
    name: str
    category: str
    enabled: bool
    multiplier: float
    pricing: dict

