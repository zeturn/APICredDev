from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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
from app.db.session import SessionLocal
from app.db import models as _models  # noqa: F401
from app.services.bootstrap import (
    ensure_admin_user,
    ensure_bootstrap_openai_provider_key,
    ensure_default_brands,
    ensure_default_models,
    ensure_default_providers,
    ensure_default_provider_keys,
    ensure_default_routes,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings(settings)
    if settings.startup_bootstrap_enabled:
        async with SessionLocal() as db:
            await ensure_admin_user(db)
            await ensure_default_brands(db)
            await ensure_default_providers(db)
            await ensure_default_provider_keys(db)
            await ensure_default_models(db)
            await ensure_default_routes(db)
            await ensure_bootstrap_openai_provider_key(db)
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
    app.include_router(auth.runtime_auth_router, prefix="/v1")
    app.include_router(tokens.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(llm.router, prefix="/v1")
    app.include_router(billing.router, prefix="/v1")
    app.include_router(admin.router, prefix="/v1")
    app.include_router(basalt.router, prefix="/v1")
    app.include_router(stripe_webhook.router, prefix="/v1")

    return app


app = create_app()

