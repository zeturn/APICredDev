from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.core.errors import AppError
from app.schemas.admin import BrandUpsert, ModelUpsert, ProviderUpsert, ProviderKeyUpsert, ModelProviderKeyUpsert
from app.services.providers.presets import list_provider_presets
from app.services.dashboard_service import get_admin_usage_summary
from app.services.admin_service import (
    get_admin_dashboard,
    list_brands,
    list_models,
    list_providers,
    upsert_brand,
    upsert_model,
    upsert_provider,
    list_provider_keys,
    get_provider_key,
    upsert_provider_key,
    validate_provider_key,
    list_model_provider_keys,
    list_model_provider_keys_by_provider_key,
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
            if k in {"secret_encrypted", "api_key"}:
                continue
            if hasattr(v, "isoformat"):
                data[k] = v.isoformat()
            else:
                data[k] = v
        if "secret_encrypted" in obj or "secret_ref" in obj:
            data["has_secret"] = bool(obj.get("secret_encrypted") or obj.get("secret_ref"))
        return data
    data = {}
    for k, v in obj.__dict__.items():
        if k.startswith("_"):
            continue
        if k in {"secret_encrypted", "api_key"}:
            continue
        if hasattr(v, "isoformat"):
            data[k] = v.isoformat()
        else:
            data[k] = v
    if hasattr(obj, "secret_encrypted") or hasattr(obj, "secret_ref"):
        data["has_secret"] = bool(getattr(obj, "secret_encrypted", None) or getattr(obj, "secret_ref", None))
    return data


def _check_admin(token: str | None, request_id) -> None:
    if not token or token != settings.admin_token:
        raise AppError("admin_unauthorized", "invalid admin token", request_id, 403)


@router.get("/models")
async def admin_models_list(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> list:
    _check_admin(x_admin_token, request.state.request_id)
    models = await list_models(db)
    return [_to_dict(m) for m in models]


@router.get("/brands")
async def admin_brands_list(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> list:
    _check_admin(x_admin_token, request.state.request_id)
    brands = await list_brands(db)
    return [_to_dict(b) for b in brands]


@router.get("/providers")
async def admin_providers_list(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> list:
    _check_admin(x_admin_token, request.state.request_id)
    providers = await list_providers(db)
    return [_to_dict(p) for p in providers]


@router.get("/dashboard")
async def admin_dashboard(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    return await get_admin_dashboard(db)


@router.post("/models")
async def admin_models_upsert(request: Request, payload: ModelUpsert, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    model = await upsert_model(db, payload.model_dump())
    return _to_dict(model)


@router.post("/brands")
async def admin_brands_upsert(request: Request, payload: BrandUpsert, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    brand = await upsert_brand(db, payload.model_dump())
    return _to_dict(brand)


@router.post("/providers")
async def admin_providers_upsert(request: Request, payload: ProviderUpsert, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    provider = await upsert_provider(db, payload.model_dump())
    return _to_dict(provider)


@router.get("/provider-keys")
async def admin_provider_keys_list(request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> list:
    _check_admin(x_admin_token, request.state.request_id)
    keys = await list_provider_keys(db)
    return [_to_dict(k) for k in keys]


@router.get("/provider-keys/{provider_key_id}")
async def admin_provider_key_detail(provider_key_id: str, request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    provider_key = await get_provider_key(db, provider_key_id)
    if not provider_key:
        raise AppError("provider_key_not_found", "provider key not found", request.state.request_id, 404)
    links = await list_model_provider_keys_by_provider_key(db, provider_key_id)
    return {
        "provider_key": _to_dict(provider_key),
        "model_links": [_to_dict(item) for item in links],
    }


@router.get("/provider-presets")
async def admin_provider_presets(request: Request, x_admin_token: str | None = Header(default=None)) -> list[dict]:
    _check_admin(x_admin_token, request.state.request_id)
    return list_provider_presets()


@router.post("/provider-keys")
async def admin_provider_keys_upsert(request: Request, payload: ProviderKeyUpsert, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    key = await upsert_provider_key(db, payload.model_dump())
    return _to_dict(key)


@router.post("/provider-keys/{provider_key_id}/validate")
async def admin_provider_key_validate(provider_key_id: str, request: Request, x_admin_token: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> dict:
    _check_admin(x_admin_token, request.state.request_id)
    try:
        return await validate_provider_key(db, provider_key_id)
    except ValueError:
        raise AppError("provider_key_not_found", "provider key not found", request.state.request_id, 404)


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

