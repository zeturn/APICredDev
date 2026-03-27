from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.core.errors import AppError
from app.schemas.admin import ModelUpsert, ProviderKeyUpsert, ModelProviderKeyUpsert
from app.services.providers.presets import list_provider_presets
from app.services.dashboard_service import get_admin_usage_summary
from app.services.admin_service import (
    get_admin_dashboard,
    list_models,
    upsert_model,
    list_provider_keys,
    upsert_provider_key,
    list_model_provider_keys,
    upsert_model_provider_key,
    list_users,
    list_usage_sessions,
    update_user_status,
)


router = APIRouter(prefix="/admin", tags=["admin"])


def _to_dict(obj: object) -> dict:
    if isinstance(obj, dict):
        data = {}
        for k, v in obj.items():
            if hasattr(v, "isoformat"):
                data[k] = v.isoformat()
            else:
                data[k] = v
        return data
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


@router.get("/dashboard")
async def admin_dashboard(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    return await get_admin_dashboard(db)


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


@router.post("/users/{user_id}/status")
async def admin_user_status_update(
    user_id: str,
    request: Request,
    payload: dict,
    x_admin_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    try:
        user = await update_user_status(db, user_id, payload.get("status", "active"))
    except ValueError:
        raise AppError("user_not_found", "user not found", request.state.request_id, 404)
    return _to_dict(user)


@router.get("/usage-sessions")
async def admin_usage_sessions(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> list:
    _check_admin(x_admin_token, request.state.request_id)
    sessions = await list_usage_sessions(db)
    return [_to_dict(s) for s in sessions]


@router.get("/usage-summary")
async def admin_usage_summary(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    return await get_admin_usage_summary(db)

