from pydantic import BaseModel


class TokenCreateRequest(BaseModel):
    name: str
    scopes: list[str]


class TokenCreateResponse(BaseModel):
    id: str
    name: str
    token: str
    scopes: list[str]


class TokenListItem(BaseModel):
    id: str
    name: str
    scopes: list[str]
    status: str
    created_at: str
    last_used_at: str | None

