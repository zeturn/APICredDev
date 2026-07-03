import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services.metrics_service import on_llm_error, on_llm_success


@pytest.mark.asyncio
async def test_metrics_endpoint_ready_and_secret_not_logged():
    app = create_app()
    on_llm_success(tokens=10, cost_credits=0.5, upstream_latency_ms=80)
    on_llm_error(provider="openai")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/health")
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "apicred_requests_total" in text
    assert "apicred_llm_requests_total" in text
    assert "apicred_llm_errors_total" in text
    assert "apicred_tokens_total" in text
    assert "apicred_cost_credits_total" in text
    assert "sk-" not in text
