from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.errors import AppError
from app.schemas.admin import (
    BrandUpsert,
    ModelRouteUpsert,
    ModelUpsert,
    ProviderCredentialUpsert,
    ProviderUpsert,
    ProviderKeyUpsert,
    ModelProviderKeyUpsert,
    PublicModelUpsert,
    UpstreamModelUpsert,
)
from app.services.admin_access import assert_admin_access
from app.services.basaltpass_client import BasaltPassClient
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
    list_user_chat_sessions,
    list_api_supported_models,
    list_model_routes,
    list_provider_credentials,
    list_public_models,
    list_upstream_models,
    update_user_status,
    upsert_model_route,
    upsert_provider_credential,
    upsert_public_model,
    upsert_upstream_model,
    sync_wallets_from_basalt,
)


def get_basalt_client() -> BasaltPassClient:
    return BasaltPassClient()


async def require_admin_access(
    request: Request,
    authorization: str | None = Header(default=None),
    x_admin_authorization: str | None = Header(default=None, alias="X-Admin-Authorization"),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    db: AsyncSession = Depends(get_db),
    client: BasaltPassClient = Depends(get_basalt_client),
) -> None:
    await assert_admin_access(
        request=request,
        authorization=authorization,
        x_admin_authorization=x_admin_authorization,
        x_admin_token=x_admin_token,
        db=db,
        client=client,
    )


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_access)])


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
        if "secret_encrypted" in obj:
            data["has_secret"] = bool(obj.get("secret_encrypted"))
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
    if hasattr(obj, "secret_encrypted"):
        data["has_secret"] = bool(getattr(obj, "secret_encrypted", None))
    return data


@router.get("/models")
async def admin_models_list(db: AsyncSession = Depends(get_db)) -> list:
    models = await list_models(db)
    return [_to_dict(m) for m in models]


@router.get("/brands")
async def admin_brands_list(db: AsyncSession = Depends(get_db)) -> list:
    brands = await list_brands(db)
    return [_to_dict(b) for b in brands]


@router.get("/providers")
async def admin_providers_list(db: AsyncSession = Depends(get_db)) -> list:
    providers = await list_providers(db)
    return [_to_dict(p) for p in providers]


@router.get("/dashboard")
async def admin_dashboard(db: AsyncSession = Depends(get_db)) -> dict:
    return await get_admin_dashboard(db)


@router.post("/models")
async def admin_models_upsert(payload: ModelUpsert, db: AsyncSession = Depends(get_db)) -> dict:
    model = await upsert_model(db, payload.model_dump())
    return _to_dict(model)


@router.get("/public-models")
async def admin_public_models_list(db: AsyncSession = Depends(get_db)) -> list:
    return [_to_dict(item) for item in await list_public_models(db)]


@router.post("/public-models")
async def admin_public_models_upsert(payload: PublicModelUpsert, db: AsyncSession = Depends(get_db)) -> dict:
    return _to_dict(await upsert_public_model(db, payload.model_dump()))


@router.get("/upstream-models")
async def admin_upstream_models_list(db: AsyncSession = Depends(get_db)) -> list:
    return [_to_dict(item) for item in await list_upstream_models(db)]


@router.post("/upstream-models")
async def admin_upstream_models_upsert(payload: UpstreamModelUpsert, db: AsyncSession = Depends(get_db)) -> dict:
    return _to_dict(await upsert_upstream_model(db, payload.model_dump()))


@router.get("/provider-credentials")
async def admin_provider_credentials_list(db: AsyncSession = Depends(get_db)) -> list:
    return [_to_dict(item) for item in await list_provider_credentials(db)]


@router.post("/provider-credentials")
async def admin_provider_credentials_upsert(payload: ProviderCredentialUpsert, db: AsyncSession = Depends(get_db)) -> dict:
    return _to_dict(await upsert_provider_credential(db, payload.model_dump()))


@router.get("/model-routes")
async def admin_model_routes_list(db: AsyncSession = Depends(get_db)) -> list:
    return [_to_dict(item) for item in await list_model_routes(db)]


@router.post("/model-routes")
async def admin_model_routes_upsert(payload: ModelRouteUpsert, db: AsyncSession = Depends(get_db)) -> dict:
    return _to_dict(await upsert_model_route(db, payload.model_dump()))


@router.post("/brands")
async def admin_brands_upsert(payload: BrandUpsert, db: AsyncSession = Depends(get_db)) -> dict:
    brand = await upsert_brand(db, payload.model_dump())
    return _to_dict(brand)


@router.post("/providers")
async def admin_providers_upsert(payload: ProviderUpsert, db: AsyncSession = Depends(get_db)) -> dict:
    provider = await upsert_provider(db, payload.model_dump())
    return _to_dict(provider)


@router.get("/provider-keys")
async def admin_provider_keys_list(db: AsyncSession = Depends(get_db)) -> list:
    keys = await list_provider_keys(db)
    return [_to_dict(k) for k in keys]


@router.get("/provider-keys/{provider_key_id}")
async def admin_provider_key_detail(provider_key_id: str, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    provider_key = await get_provider_key(db, provider_key_id)
    if not provider_key:
        raise AppError("provider_key_not_found", "provider key not found", request.state.request_id, 404)
    links = await list_model_provider_keys_by_provider_key(db, provider_key_id)
    return {
        "provider_key": _to_dict(provider_key),
        "model_links": [_to_dict(item) for item in links],
    }


@router.get("/provider-presets")
async def admin_provider_presets() -> list[dict]:
    return list_provider_presets()


@router.post("/provider-keys")
async def admin_provider_keys_upsert(payload: ProviderKeyUpsert, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        key = await upsert_provider_key(db, payload.model_dump())
    except ValueError as exc:
        raise AppError("invalid_provider_base_url", str(exc), request.state.request_id, 400)
    return _to_dict(key)


@router.post("/provider-keys/{provider_key_id}/validate")
async def admin_provider_key_validate(provider_key_id: str, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        return await validate_provider_key(db, provider_key_id)
    except ValueError:
        raise AppError("provider_key_not_found", "provider key not found", request.state.request_id, 404)


@router.get("/model-provider-keys")
async def admin_model_provider_keys_list(db: AsyncSession = Depends(get_db)) -> list:
    items = await list_model_provider_keys(db)
    return [_to_dict(i) for i in items]


@router.post("/model-provider-keys")
async def admin_model_provider_keys_upsert(payload: ModelProviderKeyUpsert, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        item = await upsert_model_provider_key(db, payload.model_dump())
    except ValueError as exc:
        raise AppError("invalid_provider_base_url", str(exc), request.state.request_id, 400)
    return _to_dict(item)


@router.get("/users")
async def admin_users(db: AsyncSession = Depends(get_db)) -> list:
    users = await list_users(db)
    return [_to_dict(u) for u in users]


@router.get("/users/{user_id}/chat-sessions")
async def admin_user_chat_sessions(user_id: str, db: AsyncSession = Depends(get_db)) -> list:
    sessions = await list_user_chat_sessions(db, user_id)
    return sessions


@router.post("/users/{user_id}/status")
async def admin_user_status_update(
    user_id: str,
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        user = await update_user_status(db, user_id, payload.get("status", "active"))
    except ValueError:
        raise AppError("user_not_found", "user not found", request.state.request_id, 404)
    return _to_dict(user)


@router.get("/usage-sessions")
async def admin_usage_sessions(db: AsyncSession = Depends(get_db)) -> list:
    sessions = await list_usage_sessions(db)
    return [_to_dict(s) for s in sessions]


@router.get("/usage-summary")
async def admin_usage_summary(db: AsyncSession = Depends(get_db)) -> dict:
    return await get_admin_usage_summary(db)


@router.get("/api-supported-models")
async def admin_api_supported_models(db: AsyncSession = Depends(get_db)) -> list:
    return await list_api_supported_models(db)


@router.post("/wallets/sync")
async def admin_wallets_sync(payload: dict, db: AsyncSession = Depends(get_db)) -> dict:
    user_id = str(payload.get("user_id") or "").strip() or None
    dry_run = bool(payload.get("dry_run", False))
    return await sync_wallets_from_basalt(db, user_id=user_id, dry_run=dry_run)

