from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.access_policy import AccessPolicy


async def list_policies(db: AsyncSession) -> list[AccessPolicy]:
    return list((await db.execute(select(AccessPolicy).order_by(AccessPolicy.created_at.desc()))).scalars().all())


async def get_policy(db: AsyncSession, policy_id: str) -> AccessPolicy | None:
    return await db.get(AccessPolicy, policy_id)


async def upsert_policy(db: AsyncSession, payload: dict, policy_id: str | None = None) -> AccessPolicy:
    if policy_id:
        policy = await db.get(AccessPolicy, policy_id)
        if not policy:
            raise ValueError("policy_not_found")
        for key, value in payload.items():
            setattr(policy, key, value)
    else:
        policy = AccessPolicy(**payload)
        db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


async def delete_policy(db: AsyncSession, policy_id: str) -> bool:
    policy = await db.get(AccessPolicy, policy_id)
    if not policy:
        return False
    await db.delete(policy)
    await db.commit()
    return True


async def set_policy_enabled(db: AsyncSession, policy_id: str, enabled: bool) -> AccessPolicy:
    policy = await db.get(AccessPolicy, policy_id)
    if not policy:
        raise ValueError("policy_not_found")
    policy.enabled = enabled
    await db.commit()
    await db.refresh(policy)
    return policy
