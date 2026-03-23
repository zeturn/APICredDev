import pytest
import httpx

from app.services.basaltpass_client import BasaltPassClient


class _DummyResponse:
    def __init__(self, status_code: int, payload: dict, *, content_type: str = "application/json", text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.headers = {"content-type": content_type}
        self.content = b"{}" if content_type == "application/json" else text.encode("utf-8")
        self.text = text

    def json(self):
        return self._payload


class _DummyAsyncClient:
    def __init__(self, responses):
        self._responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def request(self, **kwargs):
        return self._responses.pop(0)


class _CaptureAsyncClient:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def request(self, **kwargs):
        self.last_kwargs = kwargs
        return self.response


@pytest.mark.asyncio
async def test_basalt_client_retries_on_503(monkeypatch):
    responses = [_DummyResponse(503, {"retry": True}), _DummyResponse(200, {"ok": True})]

    def _factory(*args, **kwargs):
        return _DummyAsyncClient(responses)

    monkeypatch.setattr("app.services.basaltpass_client.httpx.AsyncClient", _factory)

    client = BasaltPassClient(base_url="http://localhost:8080", max_retries=2)
    resp = await client.proxy("GET", "/api/v1/health")
    assert resp.status_code == 200
    assert resp.payload["ok"] is True


@pytest.mark.asyncio
async def test_basalt_client_returns_502_on_request_error(monkeypatch):
    class _ErrorAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, **kwargs):
            raise httpx.RequestError("network down", request=httpx.Request("GET", "http://localhost"))

    monkeypatch.setattr("app.services.basaltpass_client.httpx.AsyncClient", lambda *a, **k: _ErrorAsyncClient())
    client = BasaltPassClient(base_url="http://localhost:8080", max_retries=1)
    resp = await client.proxy("GET", "/api/v1/health")
    assert resp.status_code == 502
    assert resp.payload["error"]["code"] == "basalt_unreachable"


@pytest.mark.asyncio
async def test_basalt_client_decodes_text_response(monkeypatch):
    responses = [_DummyResponse(200, {}, content_type="text/plain", text="ok")]
    monkeypatch.setattr("app.services.basaltpass_client.httpx.AsyncClient", lambda *a, **k: _DummyAsyncClient(responses))
    client = BasaltPassClient(base_url="http://localhost:8080", max_retries=0)
    resp = await client.proxy("GET", "/api/v1/health")
    assert resp.status_code == 200
    assert resp.payload["raw"] == "ok"


@pytest.mark.asyncio
async def test_basalt_client_decodes_empty_content(monkeypatch):
    response = _DummyResponse(200, {})
    response.content = b""
    monkeypatch.setattr("app.services.basaltpass_client.httpx.AsyncClient", lambda *a, **k: _DummyAsyncClient([response]))
    client = BasaltPassClient(base_url="http://localhost:8080", max_retries=0)
    resp = await client.proxy("GET", "/api/v1/health")
    assert resp.payload == {}


@pytest.mark.asyncio
async def test_basalt_client_decodes_invalid_json_fallback(monkeypatch):
    response = _DummyResponse(200, {}, content_type="application/json", text="broken-json")

    def _raise():
        raise ValueError("invalid json")

    response.json = _raise
    monkeypatch.setattr("app.services.basaltpass_client.httpx.AsyncClient", lambda *a, **k: _DummyAsyncClient([response]))
    client = BasaltPassClient(base_url="http://localhost:8080", max_retries=0)
    resp = await client.proxy("GET", "/api/v1/health")
    assert resp.payload["raw"] == "broken-json"


@pytest.mark.asyncio
async def test_basalt_client_applies_service_token_and_header_override(monkeypatch):
    capture = _CaptureAsyncClient(_DummyResponse(200, {"ok": True}))
    monkeypatch.setattr("app.services.basaltpass_client.httpx.AsyncClient", lambda *a, **k: capture)

    client = BasaltPassClient(base_url="http://localhost:8080", service_token="svc-token", max_retries=0)
    await client.proxy("GET", "/api/v1/health", headers={"Authorization": "Bearer custom", "X-Test": "1"})

    assert capture.last_kwargs["headers"]["Authorization"] == "Bearer custom"
    assert capture.last_kwargs["headers"]["X-Test"] == "1"


@pytest.mark.asyncio
async def test_basalt_client_s2s_permissions_uses_client_credentials(monkeypatch):
    capture = _CaptureAsyncClient(_DummyResponse(200, {"data": {"permission_codes": ["entry.read"]}}))
    monkeypatch.setattr("app.services.basaltpass_client.httpx.AsyncClient", lambda *a, **k: capture)

    client = BasaltPassClient(base_url="http://localhost:8080", max_retries=0)
    client.s2s_client_id = "s2s-id"
    client.s2s_client_secret = "s2s-secret"
    data = await client.s2s_get_user_permissions("u-1", tenant_id="t-1")

    assert data["permission_codes"] == ["entry.read"]
    assert capture.last_kwargs["headers"]["client_id"] == "s2s-id"
    assert capture.last_kwargs["headers"]["client_secret"] == "s2s-secret"
    assert capture.last_kwargs["params"]["tenant_id"] == "t-1"


@pytest.mark.asyncio
async def test_basalt_client_s2s_wallet_requires_credentials():
    client = BasaltPassClient(base_url="http://localhost:8080", max_retries=0)
    client.s2s_client_id = ""
    client.s2s_client_secret = ""
    with pytest.raises(ValueError):
        await client.s2s_get_user_wallet("u-1", currency="CNY")

