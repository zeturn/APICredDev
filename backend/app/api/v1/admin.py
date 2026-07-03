from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.errors import AppError
from app.schemas.admin import (
    BrandUpsert,
    ModelRouteUpsert,
    ProviderCredentialUpsert,
    ProviderEndpointUpsert,
    ProviderUpsert,
    PublicModelUpsert,
    UpstreamModelUpsert,
)
from app.services.admin_access import assert_admin_access
from app.services.basaltpass_client import BasaltPassClient
from app.services.providers.presets import list_provider_presets
from app.services.dashboard_service import get_admin_usage_summary
from app.services.provider_health_service import health_check_by_id
from app.services.quota_ledger_service import list_quota_ledger, list_quota_usage
from app.services.admin_service import (
    get_admin_dashboard,
    list_brands,
    list_providers,
    upsert_brand,
    upsert_provider,
    list_users,
    list_usage_sessions,
    list_user_chat_sessions,
    list_api_supported_models,
    list_model_routes,
    list_provider_credentials,
    list_provider_endpoints,
    list_public_models,
    list_upstream_models,
    update_user_status,
    upsert_model_route,
    upsert_provider_credential,
    upsert_provider_endpoint,
    upsert_public_model,
    upsert_upstream_model,
    sync_wallets_from_basalt,
)
from app.services.audit_service import list_user_audit_conversations


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


@router.get("/provider-endpoints")
async def admin_provider_endpoints_list(db: AsyncSession = Depends(get_db)) -> list:
    return [_to_dict(item) for item in await list_provider_endpoints(db)]


@router.post("/provider-endpoints")
async def admin_provider_endpoints_upsert(payload: ProviderEndpointUpsert, db: AsyncSession = Depends(get_db)) -> dict:
    return _to_dict(await upsert_provider_endpoint(db, payload.model_dump()))


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


@router.get("/provider-presets")
async def admin_provider_presets() -> list[dict]:
    return list_provider_presets()


@router.get("/users")
async def admin_users(db: AsyncSession = Depends(get_db)) -> list:
    users = await list_users(db)
    return [_to_dict(u) for u in users]


@router.get("/users/{user_id}/chat-sessions")
async def admin_user_chat_sessions(user_id: str, db: AsyncSession = Depends(get_db)) -> list:
    sessions = await list_user_chat_sessions(db, user_id)
    return sessions


@router.get("/users/{user_id}/audit-conversations")
async def admin_user_audit_conversations(
    user_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await list_user_audit_conversations(
        db,
        user_id,
        page=page,
        page_size=page_size,
        include_user_deleted=True,
    )


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


@router.get("/quota/usage")
async def admin_quota_usage(
    user_id: str | None = Query(default=None),
    token_id: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await list_quota_usage(
        db,
        user_id=user_id,
        token_id=token_id,
        provider=provider,
        model=model,
        date_from=date_from,
        date_to=date_to,
        status=status,
        limit=limit,
    )


@router.get("/quota/ledger")
async def admin_quota_ledger(
    user_id: str | None = Query(default=None),
    token_id: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await list_quota_ledger(
        db,
        user_id=user_id,
        token_id=token_id,
        provider=provider,
        model=model,
        date_from=date_from,
        date_to=date_to,
        status=status,
        limit=limit,
    )


@router.post("/provider-credentials/{credential_id}/health-check")
async def admin_provider_credential_health_check(credential_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        return await health_check_by_id(db, credential_id)
    except ValueError:
        raise AppError("provider_credential_not_found", "provider credential not found", "admin", 404)


@router.get("/provider-credentials/{credential_id}/health")
async def admin_provider_credential_health(credential_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    credential = next((item for item in await list_provider_credentials(db) if item.id == credential_id), None)
    if not credential:
        raise AppError("provider_credential_not_found", "provider credential not found", "admin", 404)
    data = _to_dict(credential)
    data["last_checked_at"] = credential.last_checked_at.isoformat() if credential.last_checked_at else None
    data["last_success_at"] = credential.last_success_at.isoformat() if credential.last_success_at else None
    data["last_failure_at"] = credential.last_failure_at.isoformat() if credential.last_failure_at else None
    data["last_error_code"] = credential.last_error_code
    data["last_error_message"] = credential.last_error_message
    data["consecutive_failures"] = int(credential.consecutive_failures or 0)
    return data

