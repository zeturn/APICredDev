import pytest

from app.core.secrets import encrypt_secret
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_benchmark_result import ProviderBenchmarkResult
from app.db.models.provider_benchmark_run import ProviderBenchmarkRun
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.services.provider_benchmark_service import get_benchmark_run, run_provider_benchmark


@pytest.mark.asyncio
async def test_provider_benchmark_persisted(db_session):
    provider = Provider(name="OpenAI", slug="openai", enabled=True)
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    endpoint = ProviderEndpoint(provider_id=provider.id, slug="main", display_name="main", base_url="https://api.openai.com", enabled=True, health_state="healthy")
    public_model = PublicModel(slug="apicred-fast", display_name="apicred-fast", category="llm", enabled=True, pricing={"mode": "free"}, multiplier=1)
    upstream = UpstreamModel(provider_id=provider.id, upstream_name="gpt-4o-mini", display_name="gpt-4o-mini", capabilities={}, default_pricing={}, enabled=True)
    db_session.add_all([endpoint, public_model, upstream])
    await db_session.commit()
    await db_session.refresh(endpoint)
    await db_session.refresh(public_model)
    await db_session.refresh(upstream)
    credential = ProviderCredential(provider_endpoint_id=endpoint.id, display_name="c1", secret_encrypted=encrypt_secret("sk-test"), enabled=True, health_state="healthy")
    db_session.add(credential)
    await db_session.commit()
    await db_session.refresh(credential)
    db_session.add(ModelRoute(public_model_id=public_model.id, upstream_model_id=upstream.id, provider_credential_id=credential.id, enabled=True, priority=1, weight=1, quota_unit="requests", quota_rules={}))
    await db_session.commit()

    result = await run_provider_benchmark(db_session, public_model="apicred-fast", provider=None, runs=3, dry_run=True, mock_mode=True)
    assert result["targets"] >= 1
    assert len(result["items"]) >= 1

    runs = list((await db_session.execute(__import__("sqlalchemy").select(ProviderBenchmarkRun))).scalars().all())
    rows = list((await db_session.execute(__import__("sqlalchemy").select(ProviderBenchmarkResult))).scalars().all())
    assert len(runs) == 1
    assert len(rows) >= 1

    loaded = await get_benchmark_run(db_session, runs[0].id)
    assert loaded["id"] == runs[0].id
    assert len(loaded["results"]) >= 1
