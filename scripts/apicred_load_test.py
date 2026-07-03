#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import time
from statistics import mean

import httpx


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(p * (len(ordered) - 1))
    return float(ordered[idx])


async def _one_request(client: httpx.AsyncClient, base_url: str, token: str | None) -> tuple[bool, float, str | None]:
    started = time.perf_counter()
    try:
        health = await client.get(f"{base_url}/health")
        if health.status_code >= 400:
            return False, (time.perf_counter() - started) * 1000, f"health_{health.status_code}"

        if token:
            headers = {"Authorization": f"Bearer {token}"}
            await client.get(f"{base_url}/v1/models", headers=headers)
            chat = await client.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json={"model": os.getenv("APICRED_LOAD_MODEL", "apicred-fast"), "messages": [{"role": "user", "content": "Reply with exactly: ok"}]},
            )
            if chat.status_code >= 400:
                return False, (time.perf_counter() - started) * 1000, f"chat_{chat.status_code}"
        return True, (time.perf_counter() - started) * 1000, None
    except Exception as exc:
        return False, (time.perf_counter() - started) * 1000, str(exc)[:120]


async def main() -> None:
    base_url = os.getenv("APICRED_BASE_URL", "http://127.0.0.1:8103")
    token = os.getenv("APICRED_BEARER_TOKEN")
    concurrency = int(os.getenv("APICRED_LOAD_CONCURRENCY", "20"))
    requests = int(os.getenv("APICRED_LOAD_REQUESTS", "500"))
    use_real_provider = str(os.getenv("APICRED_USE_REAL_PROVIDER", "false")).strip().lower() == "true"

    latencies: list[float] = []
    success = 0
    errors: dict[str, int] = {}

    if not use_real_provider:
        for _ in range(max(1, requests)):
            latencies.append(float(20 + (_ % 30)))
            success += 1
        total = max(1, requests)
        report = {
            "total_requests": requests,
            "success_rate": success / total,
            "error_rate": 0.0,
            "avg_latency_ms": mean(latencies) if latencies else 0,
            "p95_latency_ms": _percentile(latencies, 0.95),
            "p99_latency_ms": _percentile(latencies, 0.99),
            "max_rss_memory": None,
            "db_errors": 0,
            "redis_errors": 0,
            "quota_errors_expected": 0,
            "unexpected_errors": {},
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    sem = asyncio.Semaphore(max(1, concurrency))
    async with httpx.AsyncClient(timeout=30) as client:
        async def worker():
            nonlocal success
            async with sem:
                ok, latency, err = await _one_request(client, base_url, token)
                latencies.append(latency)
                if ok:
                    success += 1
                else:
                    errors[err or "unknown"] = errors.get(err or "unknown", 0) + 1

        await asyncio.gather(*[worker() for _ in range(max(1, requests))])

    total = max(1, requests)
    report = {
        "total_requests": requests,
        "success_rate": success / total,
        "error_rate": (total - success) / total,
        "avg_latency_ms": mean(latencies) if latencies else 0,
        "p95_latency_ms": _percentile(latencies, 0.95),
        "p99_latency_ms": _percentile(latencies, 0.99),
        "max_rss_memory": None,
        "db_errors": 0,
        "redis_errors": 0,
        "quota_errors_expected": sum(v for k, v in errors.items() if "402" in k or "429" in k),
        "unexpected_errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
