from contextlib import asynccontextmanager
import uuid6

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import (
    auth,
    tokens,
    models,
    llm,
    billing,
    audit,
    admin,
    basalt,
    tableGraphql,
)
from app.core.errors import AppError
from app.core.config import settings, validate_production_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.db import models as _models  # noqa: F401
from app.services.bootstrap import (
    ensure_admin_user,
    ensure_bootstrap_brave_search_credential,
    ensure_bootstrap_openai_credential,
    ensure_bootstrap_openrouter_credential,
    ensure_default_brands,
    ensure_default_models,
    ensure_default_providers,
    ensure_default_routes,
)
from app.services.metrics_service import on_request_end, on_request_start, render_prometheus_metrics


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings(settings)
    if settings.startup_create_tables_enabled:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if settings.startup_schema_compat_enabled:
                await _apply_startup_schema_compat(conn)
    if settings.startup_bootstrap_enabled:
        async with SessionLocal() as db:
            await ensure_admin_user(db)
            await ensure_default_brands(db)
            await ensure_default_providers(db)
            await ensure_default_models(db)
            await ensure_default_routes(db)
            await ensure_bootstrap_openai_credential(db)
            await ensure_bootstrap_openrouter_credential(db)
            await ensure_bootstrap_brave_search_credential(db)
    yield


async def _apply_startup_schema_compat(conn) -> None:
    await conn.execute(text("ALTER TABLE usage_sessions ADD COLUMN IF NOT EXISTS upstream_credential_id VARCHAR"))
    await conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'usage_sessions'
                      AND column_name = 'upstream_key_id'
                ) THEN
                    EXECUTE 'UPDATE usage_sessions SET upstream_credential_id = upstream_key_id WHERE upstream_credential_id IS NULL';
                END IF;
            END $$;
            """
        )
    )


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="apicred",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Admin-Authorization",
            "X-Basalt-Access-Token",
            "X-APICRED-Client",
            "X-APICRED-CLI-Auth",
        ],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = uuid6.uuid7()
        on_request_start()
        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = str(request.state.request_id)
            return response
        finally:
            on_request_end()

    @app.middleware("http")
    async def graphql_auth_guard(request: Request, call_next):
        """Reject ``/graphql`` requests that lack admin auth headers.

        This middleware runs *before* the FastAPI dependency layer, so it
        cannot be bypassed by ``app.dependency_overrides``.  The downstream
        ``require_admin_access`` dependency still validates the actual token.
        """
        if request.url.path.startswith("/graphql") or request.url.path.startswith("/v1/graphql"):
            has_admin = request.headers.get("x-admin-authorization")
            has_auth = request.headers.get("authorization")
            has_cookie = request.cookies.get(settings.auth_cookie_name)
            if not has_admin and not has_auth and not has_cookie:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required"},
                )
        return await call_next(request)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "apicred"}

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(render_prometheus_metrics(), media_type="text/plain; version=0.0.4")

    app.include_router(auth.router, prefix="/v1")
    app.include_router(auth.runtime_auth_router, prefix="/v1")
    app.include_router(tokens.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(llm.router, prefix="/v1")
    app.include_router(billing.router, prefix="/v1")
    app.include_router(audit.router, prefix="/v1")
    app.include_router(admin.router, prefix="/v1")
    app.include_router(basalt.router, prefix="/v1")
    app.include_router(tableGraphql.router, prefix="/graphql")
    app.include_router(tableGraphql.router, prefix="/v1/graphql")

    return app


app = create_app()
