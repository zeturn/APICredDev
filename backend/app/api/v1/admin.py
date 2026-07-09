from fastapi import APIRouter, Depends, Query, Request
from app.api.v1.admin_auth import require_admin_access as _shared_require
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
from app.services.providers.presets import list_provider_presets
from app.services.dashboard_service import get_admin_usage_summary
from app.services.quota_ledger_service import list_quota_ledger, list_quota_usage
from app.services.access_policy_admin_service import delete_policy, get_policy, list_policies, set_policy_enabled, upsert_policy
from app.services.provider_ops_service import check_credential_health, list_provider_health, model_route_effective_status, rotate_credential_secret, set_credential_enabled
from app.services.provider_benchmark_service import get_benchmark_run, list_benchmark_runs, run_provider_benchmark
from app.services.usage_analytics_service import quota_summary, usage_group_by, usage_summary, usage_timeseries
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


require_admin_access = _shared_require


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
        return await check_credential_health(db, credential_id)
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


@router.get("/provider-health")
async def admin_provider_health(db: AsyncSession = Depends(get_db)) -> dict:
    return await list_provider_health(db)


@router.post("/provider-credentials/{credential_id}/disable")
async def admin_provider_credential_disable(credential_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        return _to_dict(await set_credential_enabled(db, credential_id, False))
    except ValueError:
        raise AppError("provider_credential_not_found", "provider credential not found", "admin", 404)


@router.post("/provider-credentials/{credential_id}/enable")
async def admin_provider_credential_enable(credential_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        return _to_dict(await set_credential_enabled(db, credential_id, True))
    except ValueError:
        raise AppError("provider_credential_not_found", "provider credential not found", "admin", 404)


@router.post("/provider-credentials/{credential_id}/rotate-secret")
async def admin_provider_credential_rotate_secret(credential_id: str, payload: dict, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        credential = await rotate_credential_secret(db, credential_id, str(payload.get("secret") or ""))
    except ValueError as exc:
        code = str(exc)
        if code == "secret_required":
            raise AppError("secret_required", "secret is required", "admin", 400)
        raise AppError("provider_credential_not_found", "provider credential not found", "admin", 404)
    data = _to_dict(credential)
    data["rotated"] = True
    return data


@router.get("/model-routes/{route_id}/effective-status")
async def admin_model_route_effective_status(route_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        return await model_route_effective_status(db, route_id)
    except ValueError:
        raise AppError("model_route_not_found", "model route not found", "admin", 404)


@router.get("/policies")
async def admin_policies_list(db: AsyncSession = Depends(get_db)) -> list[dict]:
    return [_to_dict(item) for item in await list_policies(db)]


@router.post("/policies")
async def admin_policies_create(payload: dict, db: AsyncSession = Depends(get_db)) -> dict:
    return _to_dict(await upsert_policy(db, payload))


@router.get("/policies/{policy_id}")
async def admin_policies_get(policy_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    policy = await get_policy(db, policy_id)
    if not policy:
        raise AppError("policy_not_found", "policy not found", "admin", 404)
    return _to_dict(policy)


@router.put("/policies/{policy_id}")
async def admin_policies_update(policy_id: str, payload: dict, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        return _to_dict(await upsert_policy(db, payload, policy_id=policy_id))
    except ValueError:
        raise AppError("policy_not_found", "policy not found", "admin", 404)


@router.delete("/policies/{policy_id}")
async def admin_policies_delete(policy_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    ok = await delete_policy(db, policy_id)
    if not ok:
        raise AppError("policy_not_found", "policy not found", "admin", 404)
    return {"ok": True}


@router.post("/policies/{policy_id}/enable")
async def admin_policies_enable(policy_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        return _to_dict(await set_policy_enabled(db, policy_id, True))
    except ValueError:
        raise AppError("policy_not_found", "policy not found", "admin", 404)


@router.post("/policies/{policy_id}/disable")
async def admin_policies_disable(policy_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        return _to_dict(await set_policy_enabled(db, policy_id, False))
    except ValueError:
        raise AppError("policy_not_found", "policy not found", "admin", 404)


@router.get("/usage/summary")
async def admin_usage_summary_v2(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    bucket: str = Query(default="hour"),
    tenant_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await usage_summary(db, from_ts=from_, to_ts=to, tenant_id=tenant_id, user_id=user_id, provider=provider, model=model)


@router.get("/usage/timeseries")
async def admin_usage_timeseries(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    bucket: str = Query(default="hour"),
    tenant_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await usage_timeseries(db, from_ts=from_, to_ts=to, bucket=bucket, user_id=user_id, provider=provider, model=model)


@router.get("/usage/top-users")
async def admin_usage_top_users(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await usage_group_by(db, "user", from_ts=from_, to_ts=to)


@router.get("/usage/by-provider")
async def admin_usage_by_provider(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    model: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await usage_group_by(db, "provider", from_ts=from_, to_ts=to, user_id=user_id, model=model)


@router.get("/usage/by-model")
async def admin_usage_by_model(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await usage_group_by(db, "model", from_ts=from_, to_ts=to, user_id=user_id, provider=provider)


@router.get("/usage/errors")
async def admin_usage_errors(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await usage_group_by(db, "error", from_ts=from_, to_ts=to, user_id=user_id, provider=provider, model=model)


@router.get("/quota/summary")
async def admin_quota_summary(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await quota_summary(db, from_ts=from_, to_ts=to, user_id=user_id, provider=provider, model=model)


@router.get("/provider-benchmarks")
async def admin_provider_benchmarks(db: AsyncSession = Depends(get_db)) -> list[dict]:
    return await list_benchmark_runs(db)


@router.post("/provider-benchmarks")
async def admin_provider_benchmarks_create(payload: dict, db: AsyncSession = Depends(get_db)) -> dict:
    return await run_provider_benchmark(
        db,
        public_model=str(payload.get("public_model") or "").strip() or None,
        provider=str(payload.get("provider") or "").strip() or None,
        runs=max(int(payload.get("runs") or 1), 1),
        dry_run=bool(payload.get("dry_run", True)),
        mock_mode=bool(payload.get("mock_mode", True)),
    )


@router.get("/provider-benchmarks/{run_id}")
async def admin_provider_benchmarks_get(run_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        return await get_benchmark_run(db, run_id)
    except ValueError:
        raise AppError("benchmark_run_not_found", "benchmark run not found", "admin", 404)

