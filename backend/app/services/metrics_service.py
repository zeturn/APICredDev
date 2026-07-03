from __future__ import annotations

from collections import defaultdict
from threading import Lock


_LOCK = Lock()
_COUNTERS: dict[str, float] = defaultdict(float)
_ACTIVE_REQUESTS = 0
_LATENCY_BUCKETS = [50, 100, 250, 500, 1000, 2000, 5000]
_UPSTREAM_BUCKET_COUNTS: dict[int, int] = defaultdict(int)


def _inc(name: str, value: float = 1.0) -> None:
    with _LOCK:
        _COUNTERS[name] += value


def on_request_start() -> None:
    global _ACTIVE_REQUESTS
    with _LOCK:
        _ACTIVE_REQUESTS += 1
    _inc("apicred_requests_total", 1)


def on_request_end() -> None:
    global _ACTIVE_REQUESTS
    with _LOCK:
        _ACTIVE_REQUESTS = max(0, _ACTIVE_REQUESTS - 1)


def on_llm_success(*, tokens: int, cost_credits: float, upstream_latency_ms: int | None = None) -> None:
    _inc("apicred_llm_requests_total", 1)
    _inc("apicred_tokens_total", float(tokens or 0))
    _inc("apicred_cost_credits_total", float(cost_credits or 0))
    if upstream_latency_ms is not None:
        for bucket in _LATENCY_BUCKETS:
            if upstream_latency_ms <= bucket:
                with _LOCK:
                    _UPSTREAM_BUCKET_COUNTS[bucket] += 1
                break


def on_llm_error(*, provider: str | None = None) -> None:
    _inc("apicred_llm_errors_total", 1)
    if provider:
        _inc(f"apicred_provider_errors_total{{provider=\"{provider}\"}}", 1)


def render_prometheus_metrics() -> str:
    with _LOCK:
        counters = dict(_COUNTERS)
        active = _ACTIVE_REQUESTS
        latency_counts = dict(_UPSTREAM_BUCKET_COUNTS)

    lines: list[str] = []
    lines.append("# TYPE apicred_requests_total counter")
    lines.append(f"apicred_requests_total {counters.get('apicred_requests_total', 0)}")
    lines.append("# TYPE apicred_llm_requests_total counter")
    lines.append(f"apicred_llm_requests_total {counters.get('apicred_llm_requests_total', 0)}")
    lines.append("# TYPE apicred_llm_errors_total counter")
    lines.append(f"apicred_llm_errors_total {counters.get('apicred_llm_errors_total', 0)}")
    lines.append("# TYPE apicred_tokens_total counter")
    lines.append(f"apicred_tokens_total {counters.get('apicred_tokens_total', 0)}")
    lines.append("# TYPE apicred_cost_credits_total counter")
    lines.append(f"apicred_cost_credits_total {counters.get('apicred_cost_credits_total', 0)}")
    lines.append("# TYPE apicred_active_requests gauge")
    lines.append(f"apicred_active_requests {active}")
    lines.append("# TYPE apicred_upstream_latency_ms_bucket counter")
    cumulative = 0
    for bucket in _LATENCY_BUCKETS:
        cumulative += int(latency_counts.get(bucket, 0))
        lines.append(f"apicred_upstream_latency_ms_bucket{{le=\"{bucket}\"}} {cumulative}")
    lines.append(f"apicred_upstream_latency_ms_bucket{{le=\"+Inf\"}} {cumulative}")

    for key, value in counters.items():
        if key.startswith("apicred_provider_errors_total{"):
            lines.append(f"{key} {value}")
    return "\n".join(lines) + "\n"
