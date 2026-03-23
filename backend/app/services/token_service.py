from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_api_token, hash_api_token
from app.db.models.api_token import ApiToken


async def create_token(db: AsyncSession, user_id: str, name: str, scopes: list[str]) -> tuple[ApiToken, str]:
    raw = generate_api_token()
    token_hash = hash_api_token(raw)
    api_token = ApiToken(user_id=user_id, name=name, scopes=scopes, token_hash=token_hash)
    db.add(api_token)
    await db.commit()
    await db.refresh(api_token)
    return api_token, raw


async def list_tokens(db: AsyncSession, user_id: str) -> list[ApiToken]:
    result = await db.execute(select(ApiToken).where(ApiToken.user_id == user_id))
    return list(result.scalars().all())


async def revoke_token(db: AsyncSession, user_id: str, token_id: str) -> None:
    token = await db.get(ApiToken, token_id)
    if not token or token.user_id != user_id:
        raise ValueError("not_found")
    token.status = "revoked"
    await db.commit()

