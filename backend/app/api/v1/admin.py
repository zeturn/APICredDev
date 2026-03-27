from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.core.errors import AppError
from app.schemas.admin import ModelUpsert, ProviderKeyUpsert, ModelProviderKeyUpsert
from app.services.providers.presets import list_provider_presets
from app.services.admin_service import (
    list_models,
    upsert_model,
    list_provider_keys,
    upsert_provider_key,
    list_model_provider_keys,
    upsert_model_provider_key,
    list_users,
    list_usage_sessions,
)


router = APIRouter(prefix="/admin", tags=["admin"])


def _to_dict(obj: object) -> dict:
    data = {}
    for k, v in obj.__dict__.items():
        if k.startswith("_"):
            continue
        if hasattr(v, "isoformat"):
            data[k] = v.isoformat()
        else:
            data[k] = v
    return data


def _check_admin(token: str | None, request_id) -> None:
    if not token or token != settings.admin_token:
        raise AppError("admin_unauthorized", "invalid admin token", request_id, 403)


@router.get("/models")
async def admin_models_list(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> list:
    _check_admin(x_admin_token, request.state.request_id)
    models = await list_models(db)
    return [_to_dict(m) for m in models]


@router.post("/models")
async def admin_models_upsert(request: Request, payload: ModelUpsert, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    model = await upsert_model(db, payload.model_dump())
    return _to_dict(model)


@router.get("/provider-keys")
async def admin_provider_keys_list(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> list:
    _check_admin(x_admin_token, request.state.request_id)
    keys = await list_provider_keys(db)
    return [_to_dict(k) for k in keys]


@router.get("/provider-presets")
async def admin_provider_presets(request: Request, x_admin_token: str | None = Header(default=None)) -> list[dict]:
    _check_admin(x_admin_token, request.state.request_id)
    return list_provider_presets()


@router.post("/provider-keys")
async def admin_provider_keys_upsert(request: Request, payload: ProviderKeyUpsert, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    key = await upsert_provider_key(db, payload.model_dump())
    return _to_dict(key)


@router.get("/model-provider-keys")
async def admin_model_provider_keys_list(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> list:
    _check_admin(x_admin_token, request.state.request_id)
    items = await list_model_provider_keys(db)
    return [_to_dict(i) for i in items]


@router.post("/model-provider-keys")
async def admin_model_provider_keys_upsert(request: Request, payload: ModelProviderKeyUpsert, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    item = await upsert_model_provider_key(db, payload.model_dump())
    return _to_dict(item)


@router.get("/users")
async def admin_users(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> list:
    _check_admin(x_admin_token, request.state.request_id)
    users = await list_users(db)
    return [_to_dict(u) for u in users]


@router.get("/usage-sessions")
async def admin_usage_sessions(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> list:
    _check_admin(x_admin_token, request.state.request_id)
    sessions = await list_usage_sessions(db)
    return [_to_dict(s) for s in sessions]

