import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token
from app.db.models.user import User
from app.db.models.wallet import Wallet


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError("email_exists")
    user_id = str(uuid.uuid4())
    user = User(id=user_id, email=email, password_hash=hash_password(password))
    wallet = Wallet(user_id=user_id, balance_credits=0)
    db.add(user)
    db.add(wallet)
    await db.commit()
    return user


async def login_user(db: AsyncSession, email: str, password: str) -> str:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("invalid_credentials")
    return create_access_token(user.id)


async def get_or_create_oauth_user(
    db: AsyncSession,
    email: str,
    basalt_user_id: str | None = None,
    basalt_tenant_id: str | None = None,
) -> User:
    email_result = await db.execute(
        select(User)
        .where(User.email == email)
        .order_by(User.created_at.desc(), User.id.desc())
    )
    email_user = email_result.scalars().first()

    user = None
    if basalt_user_id:
        by_basalt = await db.execute(
            select(User)
            .where(User.basalt_user_id == basalt_user_id)
            .order_by(User.created_at.desc(), User.id.desc())
        )
        basalt_matches = by_basalt.scalars().all()
        if basalt_matches:
            if basalt_tenant_id:
                user = next((candidate for candidate in basalt_matches if candidate.basalt_tenant_id == basalt_tenant_id), None)
            if not user and email_user:
                user = next((candidate for candidate in basalt_matches if candidate.id == email_user.id), None)
            if not user:
                user = next((candidate for candidate in basalt_matches if candidate.email == email), None)
            if not user:
                user = basalt_matches[0]

    if not user:
        user = email_user

    if user:
        changed = False
        if user.email != email:
            email_conflict = await db.execute(
                select(User.id)
                .where(User.email == email, User.id != user.id)
                .limit(1)
            )
            if email_conflict.scalar_one_or_none() is None:
                user.email = email
                changed = True
        if user.status != "active":
            user.status = "active"
            changed = True
        if basalt_user_id and user.basalt_user_id != basalt_user_id:
            user.basalt_user_id = basalt_user_id
            changed = True
        if basalt_tenant_id and user.basalt_tenant_id != basalt_tenant_id:
            user.basalt_tenant_id = basalt_tenant_id
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)
        return user

    user_id = str(uuid.uuid4())
    random_password = str(uuid.uuid4()) + str(uuid.uuid4())
    user = User(
        id=user_id,
        email=email,
        basalt_user_id=basalt_user_id,
        basalt_tenant_id=basalt_tenant_id,
        password_hash=hash_password(random_password),
        status="active",
    )
    wallet = Wallet(user_id=user_id, balance_credits=0)
    db.add(user)
    db.add(wallet)
    await db.commit()
    await db.refresh(user)
    return user

