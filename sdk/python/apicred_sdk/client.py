from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class ApiCredConfig:
    base_url: str = "http://localhost:8103/v1"
    timeout_seconds: float = 20.0
    access_token: str | None = None
    admin_token: str | None = None


class ApiCredClient:
    def __init__(self, config: ApiCredConfig | None = None) -> None:
        self.config = config or ApiCredConfig()

    def set_access_token(self, token: str) -> None:
        self.config.access_token = token

    def set_admin_token(self, token: str) -> None:
        self.config.admin_token = token

    def _build_headers(self, *, admin: bool = False, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if admin:
            if not self.config.admin_token:
                raise ValueError("admin_token is required for admin requests")
            headers["X-Admin-Token"] = self.config.admin_token
        else:
            if self.config.access_token:
                headers["Authorization"] = f"Bearer {self.config.access_token}"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        admin: bool = False,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = self._build_headers(admin=admin, extra_headers=extra_headers)
        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            response = client.request(method.upper(), url, params=params, json=json_body, headers=headers)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()

    # Auth
    def register(self, email: str, password: str) -> dict[str, Any]:
        return self.request("POST", "/auth/register", json_body={"email": email, "password": password})

    def login(self, email: str, password: str) -> dict[str, Any]:
        data = self.request("POST", "/auth/login", json_body={"email": email, "password": password})
        token = data.get("access_token")
        if token:
            self.set_access_token(token)
        return data

    def me(self) -> dict[str, Any]:
        return self.request("GET", "/auth/me")

    # User business APIs
    def list_models(self) -> list[dict[str, Any]]:
        return self.request("GET", "/models")

    def create_token(self, name: str, scopes: list[str]) -> dict[str, Any]:
        return self.request("POST", "/tokens", json_body={"name": name, "scopes": scopes})

    def list_tokens(self) -> list[dict[str, Any]]:
        return self.request("GET", "/tokens")

    def wallet(self) -> dict[str, Any]:
        return self.request("GET", "/billing/wallet")

    def ledger(self) -> list[dict[str, Any]]:
        return self.request("GET", "/billing/ledger")

    def redeem(self, code: str) -> dict[str, Any]:
        return self.request("POST", "/billing/redeem", json_body={"code": code})

    # Basalt integration
    def basalt(self, method: str, path: str, *, json_body: Any = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request(method, f"/basalt/{path.lstrip('/')}", json_body=json_body, params=params)

    def admin_basalt(self, method: str, path: str, *, json_body: Any = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request(method, f"/admin/basalt/{path.lstrip('/')}", json_body=json_body, params=params, admin=True)

