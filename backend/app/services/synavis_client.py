"""
synavis_client.py
-----------------
轻量级异步 Kafka 客户端，用于将计费事件通过消息队列转发给 Synavis Core（OCaml 账本引擎）。

第三阶段（Strimzi / Kafka 异步集成）：
- 在充值、扣费等操作完成后，通过 Kafka 异步将事件投递到 OCaml 引擎。
- 采用 aiokafka 实现，若 MQ 不可达仅记录警告日志，不影响原有业务流程。
- 幂等性由 OCaml 引擎保证（重复 request_id / stripe_payment_id 会被自动去重）。
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from aiokafka import AIOKafkaProducer

from app.core.config import settings

logger = logging.getLogger(__name__)

_KAFKA_BROKERS: str = getattr(settings, "synavis_kafka_brokers", "localhost:9092")
_SYNAVIS_BASE_URL: str = getattr(settings, "synavis_base_url", "http://localhost:10622")
_TOPIC_NAME = "synavis-events"
_TIMEOUT: float = 5.0

# 全局复用的 Kafka Producer
_producer: AIOKafkaProducer | None = None

async def _get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        # Request timeout for metadata fetch
        _producer = AIOKafkaProducer(
            bootstrap_servers=_KAFKA_BROKERS,
            request_timeout_ms=int(_TIMEOUT * 1000),
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await _producer.start()
    return _producer


async def _publish_event(payload: Any) -> bool:
    """
    向 Kafka 投递一个计费事件。
    返回 True 表示投递成功，False 表示失败（调用方无需处理失败）。
    """
    try:
        producer = await _get_producer()
        await producer.send_and_wait(_TOPIC_NAME, value=payload)
        return True
    except Exception as exc:
        # MQ 不可达时，只记录调试日志，不抛出异常
        logger.warning("[synavis] Kafka unreachable, skipping event mirror: %s", exc)
        return False


async def notify_funds_received(
    *,
    user_id: str,
    tenant_id: str,
    amount_microcredits: int,
    stripe_payment_id: str,
    currency: str = "USD",
) -> bool:
    """通知 OCaml 引擎：用户钱包已充值。"""
    payload = [
        "FundsReceived",
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "amount": amount_microcredits,
            "currency": [currency],
            "stripe_payment_id": stripe_payment_id,
        },
    ]
    logger.debug(
        "[synavis] publishing FundsReceived to Kafka: user=%s stripe_id=%s amount=%d",
        user_id, stripe_payment_id, amount_microcredits,
    )
    return await _publish_event(payload)


async def notify_usage_completed(
    *,
    user_id: str,
    tenant_id: str,
    resource_type: str,
    usage_units: int,
    unit_price_microcredits: int,
    request_id: str,
) -> bool:
    """通知 OCaml 引擎：API 用量已结算。"""
    payload = [
        "UsageCompleted",
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "resource_type": resource_type,
            "usage_units": usage_units,
            "unit_price": unit_price_microcredits,
            "request_id": request_id,
        },
    ]
    logger.debug(
        "[synavis] publishing UsageCompleted to Kafka: user=%s request=%s units=%d",
        user_id, request_id, usage_units,
    )
    return await _publish_event(payload)


async def query_balance(*, user_id: str) -> dict | None:
    """
    从 OCaml 引擎查询权威余额 (依然使用 HTTP，因为查询是同步的)。
    """
    url = f"{_SYNAVIS_BASE_URL}/api/b1/wallets/{user_id}/balance"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            return resp.json()
        return None
    except httpx.RequestError as exc:
        logger.debug("[synavis] balance query failed: %s", exc)
        return None
