from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.v1 import (
    auth,
    tokens,
    models,
    llm,
    billing,
    admin,
    basalt,
    stripe_webhook,
)
from app.core.errors import AppError
from app.core.config import settings, validate_production_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.db import models as _models  # noqa: F401
from app.services.bootstrap import ensure_admin_user, ensure_default_brands, ensure_default_models, ensure_default_providers, ensure_default_provider_keys


def _apply_compat_schema_updates(connection) -> None:
    inspector = inspect(connection)
    if not inspector.has_table("model_provider_keys"):
        mpk_columns = set()
    else:
        mpk_columns = {column["name"] for column in inspector.get_columns("model_provider_keys")}
    if "base_url" not in mpk_columns:
        connection.execute(text("ALTER TABLE model_provider_keys ADD COLUMN base_url VARCHAR"))
    if "weight" not in mpk_columns:
        connection.execute(text("ALTER TABLE model_provider_keys ADD COLUMN weight INTEGER DEFAULT 1"))
        connection.execute(text("UPDATE model_provider_keys SET weight = 1 WHERE weight IS NULL"))
    if inspector.has_table("models"):
        model_columns = {column["name"] for column in inspector.get_columns("models")}
        if "brand_id" not in model_columns:
            connection.execute(text("ALTER TABLE models ADD COLUMN brand_id VARCHAR"))
        if "icon_slug" not in model_columns:
            connection.execute(text("ALTER TABLE models ADD COLUMN icon_slug VARCHAR"))
        if "icon_url" not in model_columns:
            connection.execute(text("ALTER TABLE models ADD COLUMN icon_url VARCHAR"))
    if inspector.has_table("brands"):
        brand_columns = {column["name"] for column in inspector.get_columns("brands")}
        if "icon_slug" not in brand_columns:
            connection.execute(text("ALTER TABLE brands ADD COLUMN icon_slug VARCHAR"))
        if "icon_url" not in brand_columns:
            connection.execute(text("ALTER TABLE brands ADD COLUMN icon_url VARCHAR"))
    if inspector.has_table("provider_keys"):
        provider_key_columns = {column["name"] for column in inspector.get_columns("provider_keys")}
        if "provider_id" not in provider_key_columns:
            connection.execute(text("ALTER TABLE provider_keys ADD COLUMN provider_id VARCHAR"))
        if "secret_encrypted" not in provider_key_columns:
            connection.execute(text("ALTER TABLE provider_keys ADD COLUMN secret_encrypted VARCHAR"))
        if "secret_last4" not in provider_key_columns:
            connection.execute(text("ALTER TABLE provider_keys ADD COLUMN secret_last4 VARCHAR"))
        if "secret_ref" in provider_key_columns:
            connection.execute(
                text(
                    """
                    DELETE FROM model_provider_keys
                    WHERE provider_key_id IN (
                        SELECT id
                        FROM provider_keys
                        WHERE COALESCE(secret_encrypted, '') = ''
                          AND COALESCE(secret_ref, '') <> ''
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    DELETE FROM provider_keys
                    WHERE COALESCE(secret_encrypted, '') = ''
                      AND COALESCE(secret_ref, '') <> ''
                    """
                )
            )
            try:
                connection.execute(text("ALTER TABLE provider_keys DROP COLUMN secret_ref"))
            except Exception:
                pass
    if inspector.has_table("providers"):
        provider_columns = {column["name"] for column in inspector.get_columns("providers")}
        if "default_base_url" not in provider_columns:
            connection.execute(text("ALTER TABLE providers ADD COLUMN default_base_url VARCHAR"))

    if not inspector.has_table("usage_sessions"):
        return
    usage_columns = {column["name"] for column in inspector.get_columns("usage_sessions")}
    if "model_name" not in usage_columns:
        connection.execute(text("ALTER TABLE usage_sessions ADD COLUMN model_name VARCHAR"))
    if "request_messages" not in usage_columns:
        connection.execute(text("ALTER TABLE usage_sessions ADD COLUMN request_messages JSON"))
    if "request_text" not in usage_columns:
        connection.execute(text("ALTER TABLE usage_sessions ADD COLUMN request_text TEXT"))
    if "response_text" not in usage_columns:
        connection.execute(text("ALTER TABLE usage_sessions ADD COLUMN response_text TEXT"))
    if "prompt_tokens" not in usage_columns:
        connection.execute(text("ALTER TABLE usage_sessions ADD COLUMN prompt_tokens INTEGER DEFAULT 0"))
        connection.execute(text("UPDATE usage_sessions SET prompt_tokens = 0 WHERE prompt_tokens IS NULL"))
    if "completion_tokens" not in usage_columns:
        connection.execute(text("ALTER TABLE usage_sessions ADD COLUMN completion_tokens INTEGER DEFAULT 0"))
        connection.execute(text("UPDATE usage_sessions SET completion_tokens = 0 WHERE completion_tokens IS NULL"))
    if "total_tokens" not in usage_columns:
        connection.execute(text("ALTER TABLE usage_sessions ADD COLUMN total_tokens INTEGER DEFAULT 0"))
        connection.execute(text("UPDATE usage_sessions SET total_tokens = 0 WHERE total_tokens IS NULL"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings(settings)
    async with engine.begin() as conn:
        if settings.startup_create_tables_enabled:
            await conn.run_sync(Base.metadata.create_all)
        if settings.startup_schema_compat_enabled:
            await conn.run_sync(_apply_compat_schema_updates)
    if settings.startup_bootstrap_enabled:
        async with SessionLocal() as db:
            await ensure_admin_user(db)
            await ensure_default_brands(db)
            await ensure_default_providers(db)
            await ensure_default_provider_keys(db)
            await ensure_default_models(db)
    yield


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
        allow_origins=["http://localhost:5106", "http://127.0.0.1:5106", settings.frontend_base_url],
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
        request.state.request_id = uuid4()
        response = await call_next(request)
        response.headers["X-Request-Id"] = str(request.state.request_id)
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "apicred"}

    app.include_router(auth.router, prefix="/v1")
    app.include_router(tokens.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(llm.router, prefix="/v1")
    app.include_router(billing.router, prefix="/v1")
    app.include_router(admin.router, prefix="/v1")
    app.include_router(basalt.router, prefix="/v1")
    app.include_router(stripe_webhook.router, prefix="/v1")

    return app


app = create_app()

