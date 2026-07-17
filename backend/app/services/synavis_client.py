"""
synavis_client.py
-----------------
轻量级异步客户端，用于将计费事件转发给 Synavis Core（OCaml 账本引擎）。

第一阶段（纯内存 + HTTP 联调）：
- 在充值、扣费等操作完成后，异步将事件镜像到 OCaml 引擎
- 若引擎不可达，仅记录警告日志，不影响原有业务流程
- 幂等性由 OCaml 引擎保证（重复 request_id / stripe_payment_id 会被自动去重）
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# 从配置读取引擎地址，默认 localhost:10622
_SYNAVIS_BASE_URL: str = getattr(settings, "synavis_base_url", "http://localhost:10622")
_SYNAVIS_TIMEOUT: float = 5.0  # 宽松超时：引擎不在线时快速失败，不阻塞主流程


async def _post_event(payload: Any) -> bool:
    """
    向 Synavis Core 发送一个计费事件。
    返回 True 表示引擎接收成功，False 表示失败（调用方无需处理失败）。
    """
    url = f"{_SYNAVIS_BASE_URL}/api/b1/events"
    try:
        async with httpx.AsyncClient(timeout=_SYNAVIS_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            return True
        # 402 = 余额不足（引擎已处理，非网络错误）
        if resp.status_code == 402:
            logger.warning(
                "[synavis] engine rejected event (insufficient funds): %s",
                resp.text[:300],
            )
            return False
        logger.warning(
            "[synavis] engine returned unexpected status %s: %s",
            resp.status_code,
            resp.text[:300],
        )
        return False
    except httpx.RequestError as exc:
        # 引擎不可达时，只记录调试日志，不抛出异常
        logger.debug("[synavis] engine unreachable, skipping event mirror: %s", exc)
        return False


async def notify_funds_received(
    *,
    user_id: str,
    tenant_id: str,
    amount_microcredits: int,
    stripe_payment_id: str,
    currency: str = "USD",
) -> bool:
    """
    通知 OCaml 引擎：用户钱包已充值（Stripe 扣款成功后调用）。

    Args:
        user_id: APICredDev 内部用户 ID（作为 OCaml 账本 user_id）
        tenant_id: 所属租户 ID
        amount_microcredits: 充值金额（微credit，1 credit = 1_000_000 microcredits）
        stripe_payment_id: Stripe Payment Intent ID（用于幂等去重）
        currency: 货币代码，默认 "USD"
    """
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
        "[synavis] notifying FundsReceived: user=%s stripe_id=%s amount=%d",
        user_id,
        stripe_payment_id,
        amount_microcredits,
    )
    return await _post_event(payload)


async def notify_usage_completed(
    *,
    user_id: str,
    tenant_id: str,
    resource_type: str,
    usage_units: int,
    unit_price_microcredits: int,
    request_id: str,
) -> bool:
    """
    通知 OCaml 引擎：API 用量已结算（settle_usage 完成后调用）。

    Args:
        user_id: APICredDev 内部用户 ID
        tenant_id: 所属租户 ID
        resource_type: 资源类型（如 "llm_tokens", "storage_gb"）
        usage_units: 实际消耗的单元数量（如 Token 数）
        unit_price_microcredits: 每单元价格（微credit）
        request_id: 请求唯一 ID（用于幂等去重，必须全局唯一）
    """
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
        "[synavis] notifying UsageCompleted: user=%s request=%s units=%d",
        user_id,
        request_id,
        usage_units,
    )
    return await _post_event(payload)


async def query_balance(*, user_id: str) -> dict | None:
    """
    从 OCaml 引擎查询用户的权威账本余额（可选，用于对账）。
    返回 None 表示引擎不可达或用户不存在。
    """
    url = f"{_SYNAVIS_BASE_URL}/api/b1/wallets/{user_id}/balance"
    try:
        async with httpx.AsyncClient(timeout=_SYNAVIS_TIMEOUT) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            return resp.json()
        return None
    except httpx.RequestError as exc:
        logger.debug("[synavis] balance query failed: %s", exc)
        return None
