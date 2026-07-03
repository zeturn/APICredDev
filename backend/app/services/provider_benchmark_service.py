from __future__ import annotations

import random
import time
from collections import defaultdict
from statistics import mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets import decrypt_secret
from app.core.time import utc_now
from app.db.models.model_route import ModelRoute
from app.db.models.provider import Provider
from app.db.models.provider_benchmark_result import ProviderBenchmarkResult
from app.db.models.provider_benchmark_run import ProviderBenchmarkRun
from app.db.models.provider_credential import ProviderCredential
from app.db.models.provider_endpoint import ProviderEndpoint
from app.db.models.public_model import PublicModel
from app.db.models.upstream_model import UpstreamModel
from app.services.providers.factory import get_provider_adapter
from app.services.providers.presets import get_provider_default_base_url


def _safe_prompt() -> list[dict]:
    return [{"role": "user", "content": "Reply with exactly: ok"}]


async def _collect_targets(db: AsyncSession, public_model: str | None, provider_filter: str | None) -> list[dict]:
    query = (
        select(ModelRoute, PublicModel, UpstreamModel, ProviderCredential, ProviderEndpoint, Provider)
        .join(PublicModel, PublicModel.id == ModelRoute.public_model_id)
        .join(UpstreamModel, UpstreamModel.id == ModelRoute.upstream_model_id)
        .join(Provider, Provider.id == UpstreamModel.provider_id)
        .outerjoin(ProviderCredential, ProviderCredential.id == ModelRoute.provider_credential_id)
        .outerjoin(ProviderEndpoint, ProviderEndpoint.id == ProviderCredential.provider_endpoint_id)
        .where(ModelRoute.enabled.is_(True))
        .order_by(ModelRoute.priority.asc(), ModelRoute.weight.desc())
    )
    rows = list((await db.execute(query)).all())
    targets = []
    for route, pmodel, upstream, credential, endpoint, provider in rows:
        if public_model and pmodel.slug != public_model:
            continue
        if provider_filter and provider.slug != provider_filter:
            continue
        targets.append(
            {
                "route_id": route.id,
                "public_model": pmodel.slug,
                "provider": provider.slug,
                "upstream_model": upstream.upstream_name,
                "credential_id": credential.id if credential else None,
                "health_state_before": credential.health_state if credential else None,
                "api_key": decrypt_secret(credential.secret_encrypted) if credential and credential.secret_encrypted else "",
                "base_url": (route.base_url_override or (endpoint.base_url if endpoint else "") or get_provider_default_base_url(provider.slug)),
            }
        )
    return targets


def _summarize_result(run_id: str, target: dict, latencies: list[int], success: int, failure: int, tokens: int, estimated_cost: float) -> ProviderBenchmarkResult:
    sorted_lat = sorted(latencies)
    p95 = sorted_lat[int(0.95 * (len(sorted_lat) - 1))] if sorted_lat else None
    total = success + failure
    return ProviderBenchmarkResult(
        run_id=run_id,
        provider=target["provider"],
        credential_id=target["credential_id"],
        upstream_model=target["upstream_model"],
        success_rate=(success / total) if total else 0,
        avg_latency_ms=mean(sorted_lat) if sorted_lat else None,
        p95_latency_ms=p95,
        error_rate=(failure / total) if total else 0,
        tokens=tokens,
        estimated_cost=estimated_cost,
        health_state_before=target["health_state_before"],
        health_state_after=target["health_state_before"],
    )


async def run_provider_benchmark(
    db: AsyncSession,
    *,
    public_model: str | None,
    provider: str | None,
    runs: int,
    dry_run: bool,
    mock_mode: bool,
) -> dict:
    run = ProviderBenchmarkRun(
        status="running",
        dry_run=dry_run,
        public_model=public_model,
        provider=provider,
        runs=runs,
        prompt="Reply with exactly: ok",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    targets = await _collect_targets(db, public_model, provider)
    results: list[ProviderBenchmarkResult] = []
    for target in targets:
        latencies = []
        success = 0
        failure = 0
        tokens = 0
        estimated_cost = 0.0
        adapter = get_provider_adapter(target["provider"])
        for _ in range(max(1, runs)):
            if dry_run or mock_mode:
                latency = random.randint(30, 120)
                latencies.append(latency)
                success += 1
                tokens += 2
                continue
            payload = {"model": target["upstream_model"], "messages": _safe_prompt(), "max_tokens": 4}
            started = time.perf_counter()
            try:
                _, usage = await adapter.chat_completions(payload, target["api_key"], target["base_url"])
                success += 1
                latencies.append(int((time.perf_counter() - started) * 1000))
                tokens += int((usage or {}).get("total_tokens", 0) or 0)
            except Exception:
                failure += 1
                latencies.append(int((time.perf_counter() - started) * 1000))
        result = _summarize_result(run.id, target, latencies, success, failure, tokens, estimated_cost)
        db.add(result)
        results.append(result)
    run.status = "completed"
    run.completed_at = utc_now()
    run.summary_json = {
        "targets": len(targets),
        "results": len(results),
        "success_rate": float(mean([float(r.success_rate or 0) for r in results])) if results else 0.0,
    }
    await db.commit()
    return {
        "run_id": run.id,
        "status": run.status,
        "targets": len(targets),
        "items": [
            {
                "provider": r.provider,
                "credential_id": r.credential_id,
                "upstream_model": r.upstream_model,
                "success_rate": float(r.success_rate or 0),
                "avg_latency_ms": float(r.avg_latency_ms or 0),
                "p95_latency_ms": float(r.p95_latency_ms or 0),
                "error_rate": float(r.error_rate or 0),
                "tokens": int(r.tokens or 0),
                "estimated_cost": float(r.estimated_cost or 0),
                "health_state_before": r.health_state_before,
                "health_state_after": r.health_state_after,
            }
            for r in results
        ],
    }


async def list_benchmark_runs(db: AsyncSession, limit: int = 20) -> list[dict]:
    runs = list((await db.execute(select(ProviderBenchmarkRun).order_by(ProviderBenchmarkRun.created_at.desc()).limit(limit))).scalars().all())
    return [
        {
            "id": item.id,
            "status": item.status,
            "dry_run": item.dry_run,
            "public_model": item.public_model,
            "provider": item.provider,
            "runs": item.runs,
            "summary_json": item.summary_json or {},
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        }
        for item in runs
    ]


async def get_benchmark_run(db: AsyncSession, run_id: str) -> dict:
    run = await db.get(ProviderBenchmarkRun, run_id)
    if not run:
        raise ValueError("benchmark_run_not_found")
    results = list((await db.execute(select(ProviderBenchmarkResult).where(ProviderBenchmarkResult.run_id == run_id))).scalars().all())
    return {
        "id": run.id,
        "status": run.status,
        "dry_run": run.dry_run,
        "public_model": run.public_model,
        "provider": run.provider,
        "runs": run.runs,
        "summary_json": run.summary_json or {},
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "results": [
            {
                "provider": r.provider,
                "credential_id": r.credential_id,
                "upstream_model": r.upstream_model,
                "success_rate": float(r.success_rate or 0),
                "avg_latency_ms": float(r.avg_latency_ms or 0),
                "p95_latency_ms": float(r.p95_latency_ms or 0),
                "error_rate": float(r.error_rate or 0),
                "tokens": int(r.tokens or 0),
                "estimated_cost": float(r.estimated_cost or 0),
                "health_state_before": r.health_state_before,
                "health_state_after": r.health_state_after,
            }
            for r in results
        ],
    }
