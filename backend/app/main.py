from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    auth,
    tokens,
    models,
    llm,
    data_sources,
    billing,
    admin,
    basalt,
    stripe_webhook,
)
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.db import models as _models  # noqa: F401
from app.services.bootstrap import ensure_admin_user


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="apicred", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5106", "http://127.0.0.1:5106"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with SessionLocal() as db:
            await ensure_admin_user(db)

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = uuid4()
        response = await call_next(request)
        response.headers["X-Request-Id"] = str(request.state.request_id)
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    app.include_router(auth.router, prefix="/v1")
    app.include_router(tokens.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(llm.router, prefix="/v1")
    app.include_router(data_sources.router, prefix="/v1")
    app.include_router(billing.router, prefix="/v1")
    app.include_router(admin.router, prefix="/v1")
    app.include_router(basalt.router, prefix="/v1")
    app.include_router(stripe_webhook.router, prefix="/v1")

    return app


app = create_app()

