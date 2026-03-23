from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass
class BasaltProxyResponse:
    status_code: int
    payload: Any


class BasaltPassClient:
    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.base_url = (base_url or settings.basalt_base_url).rstrip("/")
        self.service_token = service_token if service_token is not None else settings.basalt_service_token
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.basalt_timeout_seconds
        self.max_retries = max_retries if max_retries is not None else settings.basalt_max_retries
        self.s2s_client_id = settings.basalt_s2s_client_id
        self.s2s_client_secret = settings.basalt_s2s_client_secret

    @staticmethod
    def _decode_response(resp: httpx.Response) -> Any:
        if not resp.content:
            return {}
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                return resp.json()
            except ValueError:
                return {"raw": resp.text}
        return {"raw": resp.text}

    async def proxy(
        self,
        method: str,
        upstream_path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any = None,
        headers: dict[str, str] | None = None,
    ) -> BasaltProxyResponse:
        url = f"{self.base_url}{upstream_path}"
        merged_headers: dict[str, str] = {"Accept": "application/json"}
        if self.service_token:
            merged_headers["Authorization"] = f"Bearer {self.service_token}"
        if headers:
            merged_headers.update(headers)

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.request(
                        method=method.upper(),
                        url=url,
                        params=query or None,
                        json=body,
                        headers=merged_headers,
                    )
                if response.status_code in {429, 502, 503, 504} and attempt < self.max_retries:
                    await asyncio.sleep(0.25 * (attempt + 1))
                    continue
                return BasaltProxyResponse(
                    status_code=response.status_code,
                    payload=self._decode_response(response),
                )
            except httpx.RequestError as exc:
                if attempt >= self.max_retries:
                    return BasaltProxyResponse(
                        status_code=502,
                        payload={
                            "error": {
                                "code": "basalt_unreachable",
                                "message": str(exc),
                            }
                        },
                    )
                await asyncio.sleep(0.25 * (attempt + 1))

    def _require_s2s_credentials(self) -> None:
        if not self.s2s_client_id or not self.s2s_client_secret:
            raise ValueError("Basalt S2S credentials are not configured")

    async def _s2s_get(self, upstream_path: str, *, query: dict[str, Any] | None = None) -> Any:
        self._require_s2s_credentials()
        response = await self.proxy(
            method="GET",
            upstream_path=upstream_path,
            query=query,
            headers={
                "client_id": self.s2s_client_id,
                "client_secret": self.s2s_client_secret,
            },
        )
        if response.status_code >= 400:
            return {
                "error": {
                    "code": "s2s_request_failed",
                    "message": f"upstream status {response.status_code}",
                    "details": response.payload,
                }
            }
        payload = response.payload
        if isinstance(payload, dict) and "data" in payload:
            return payload.get("data")
        return payload

    async def s2s_get_user_permissions(self, user_id: str, tenant_id: str | None = None) -> Any:
        params: dict[str, Any] = {}
        if tenant_id:
            params["tenant_id"] = tenant_id
        return await self._s2s_get(f"/api/v1/s2s/users/{user_id}/permissions", query=params or None)

    async def s2s_get_user_roles(self, user_id: str, tenant_id: str | None = None) -> Any:
        params: dict[str, Any] = {}
        if tenant_id:
            params["tenant_id"] = tenant_id
        return await self._s2s_get(f"/api/v1/s2s/users/{user_id}/roles", query=params or None)

    async def s2s_get_me(self) -> Any:
        return await self._s2s_get("/api/v1/s2s/me")

    async def s2s_get_user_wallet(
        self,
        user_id: str,
        currency: str,
        limit: int = 20,
        tenant_id: str | None = None,
    ) -> Any:
        params: dict[str, Any] = {"currency": currency, "limit": limit}
        if tenant_id:
            params["tenant_id"] = tenant_id
        return await self._s2s_get(f"/api/v1/s2s/users/{user_id}/wallets", query=params)

