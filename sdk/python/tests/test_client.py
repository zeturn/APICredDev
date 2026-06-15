from __future__ import annotations

import pytest

from apicred_sdk import ApiCredClient, ApiCredConfig


class _DummyResponse:
    def __init__(self, payload=None, *, content: bytes = b"{}", exc: Exception | None = None) -> None:
        self._payload = payload if payload is not None else {}
        self.content = content
        self._exc = exc
        self.raise_called = False

    def raise_for_status(self) -> None:
        self.raise_called = True
        if self._exc:
            raise self._exc

    def json(self):
        return self._payload


class _CaptureClient:
    def __init__(self, response: _DummyResponse) -> None:
        self.response = response
        self.calls: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def request(self, method, url, params=None, json=None, headers=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
                "headers": headers,
            }
        )
        return self.response


def test_request_builds_url_headers_params_and_body(monkeypatch):
    response = _DummyResponse({"ok": True})
    capture = _CaptureClient(response)
    monkeypatch.setattr("apicred_sdk.client.httpx.Client", lambda timeout: capture)

    client = ApiCredClient(ApiCredConfig(base_url="http://api.test/v1/", timeout_seconds=3, access_token="access-token"))
    data = client.request(
        "post",
        "/tokens",
        params={"page": 1},
        json_body={"name": "cli"},
        extra_headers={"X-Test": "1"},
    )

    assert data == {"ok": True}
    assert response.raise_called is True
    assert capture.calls == [
        {
            "method": "POST",
            "url": "http://api.test/v1/tokens",
            "params": {"page": 1},
            "json": {"name": "cli"},
            "headers": {
                "Accept": "application/json",
                "Authorization": "Bearer access-token",
                "X-Test": "1",
            },
        }
    ]


def test_admin_request_requires_and_uses_admin_token(monkeypatch):
    client = ApiCredClient(ApiCredConfig(base_url="http://api.test/v1"))

    with pytest.raises(ValueError, match="admin_token is required"):
        client.request("GET", "/admin/models", admin=True)

    response = _DummyResponse({"items": []})
    capture = _CaptureClient(response)
    monkeypatch.setattr("apicred_sdk.client.httpx.Client", lambda timeout: capture)

    client.set_admin_token("admin-token")
    assert client.request("GET", "/admin/models", admin=True) == {"items": []}
    assert capture.calls[0]["headers"] == {
        "Accept": "application/json",
        "X-Admin-Token": "admin-token",
    }


def test_login_stores_access_token(monkeypatch):
    response = _DummyResponse({"access_token": "new-token", "user": {"id": "u1"}})
    monkeypatch.setattr("apicred_sdk.client.httpx.Client", lambda timeout: _CaptureClient(response))

    client = ApiCredClient(ApiCredConfig(base_url="http://api.test/v1"))
    payload = client.login("user@example.com", "pass")

    assert payload["access_token"] == "new-token"
    assert client.config.access_token == "new-token"


def test_empty_response_returns_empty_dict(monkeypatch):
    response = _DummyResponse(content=b"")
    monkeypatch.setattr("apicred_sdk.client.httpx.Client", lambda timeout: _CaptureClient(response))

    client = ApiCredClient(ApiCredConfig(base_url="http://api.test/v1"))

    assert client.request("DELETE", "/tokens/t1") == {}


def test_basalt_helpers_prefix_paths(monkeypatch):
    response = _DummyResponse({"ok": True})
    capture = _CaptureClient(response)
    monkeypatch.setattr("apicred_sdk.client.httpx.Client", lambda timeout: capture)

    client = ApiCredClient(ApiCredConfig(base_url="http://api.test/v1", admin_token="admin-token"))
    client.basalt("GET", "wallet/balance", params={"currency": "CREDIT"})
    client.admin_basalt("POST", "/users", json_body={"email": "a@example.com"})

    assert capture.calls[0]["url"] == "http://api.test/v1/basalt/wallet/balance"
    assert capture.calls[0]["params"] == {"currency": "CREDIT"}
    assert capture.calls[1]["url"] == "http://api.test/v1/admin/basalt/users"
    assert capture.calls[1]["json"] == {"email": "a@example.com"}
