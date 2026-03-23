from fastapi import APIRouter, Request

from app.core.errors import AppError

from app.core.time import utc_now


router = APIRouter(prefix="", tags=["data_sources"])


@router.get("/time")
async def get_time() -> dict:
    now = utc_now()
    return {"utc": now.isoformat(), "epoch": int(now.timestamp())}


@router.get("/weather")
async def get_weather(request: Request) -> dict:
    raise AppError("not_implemented", "not implemented", request.state.request_id, 501)


@router.get("/fx")
async def get_fx(request: Request) -> dict:
    raise AppError("not_implemented", "not implemented", request.state.request_id, 501)

