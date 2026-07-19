from typing import Optional
import asyncio
import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import Depends, Header, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.core.errors import AppError
from app.db.session import SessionLocal
from app.db.models.public_model import PublicModel
from app.db.models.usage_session import UsageSession
from app.api.v1.admin_auth import require_admin_access
from app.services.admin_access import assert_admin_access
from app.services.basaltpass_client import BasaltPassClient
from app.services.billing_service import get_wallet, list_ledger
from app.services.dashboard_service import get_admin_usage_summary
from app.services.usage_analytics_service import usage_summary, usage_group_by, quota_summary


@strawberry.type
class RecentSession:
    id: str
    request_id: Optional[str] = None
    user_id: str
    user_email: Optional[str] = None
    model_id: str
    model_name: Optional[str] = None
    status: str
    provider: Optional[str] = None
    endpoint: Optional[str] = None
    credential_name: Optional[str] = None
    final_cost_credits: float
    total_tokens: int
    created_at: str
    completed_at: Optional[str] = None


@strawberry.type
class ModelUsageStat:
    model_id: str
    model_name: Optional[str] = None
    requests: int
    used_credits: float


@strawberry.type
class AdminUsageSummary:
    recent_sessions: list[RecentSession]
    by_model: list[ModelUsageStat]


@strawberry.type
class UsageSummary:
    request_count: int
    success_count: int
    error_count: int
    error_rate: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_credits: float
    final_cost_credits: float
    avg_latency_ms: float


@strawberry.type
class UsageByProvider:
    provider: str
    label: str
    request_count: int
    success_count: int
    error_count: int
    error_rate: float
    total_tokens: int
    final_cost_credits: float


@strawberry.type
class UsageByModel:
    model: str
    label: str
    request_count: int
    success_count: int
    error_count: int
    error_rate: float
    total_tokens: int
    final_cost_credits: float


@strawberry.type
class UsageByUser:
    user: str
    label: str
    request_count: int
    success_count: int
    error_count: int
    error_rate: float
    total_tokens: int
    final_cost_credits: float


@strawberry.type
class UsageByError:
    error: str
    label: str
    request_count: int
    success_count: int
    error_count: int
    error_rate: float
    total_tokens: int
    final_cost_credits: float


@strawberry.type
class QuotaSummary:
    entry_count: int
    reserved_count: int
    settled_count: int
    rejected_count: int
    failed_count: int
    reserved_delta: int
    total_tokens: int
    final_cost_credits: float


@strawberry.type
class AdminDashboardData:
    summary: UsageSummary
    by_provider: list[UsageByProvider]
    by_model: list[UsageByModel]
    top_users: list[UsageByUser]
    errors: list[UsageByError]
    quota: QuotaSummary


@strawberry.type
class UserSummary:
    balance_credits: float
    used_credits: float
    usage_sessions: int
    available_models: int


@strawberry.type
class UserLedgerEntry:
    id: str
    entry_type: str
    amount_credits: float
    status: Optional[str] = None
    created_at: Optional[str] = None


@strawberry.type
class UserDashboardData:
    summary: UserSummary
    balance_credits: float
    ledger: list[UserLedgerEntry]
    user_email: str


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello from APICred GraphQL API!"

    @strawberry.field
    async def admin_usage_summary(self, info: strawberry.Info) -> AdminUsageSummary:
        db = info.context["db"]
        summary = await get_admin_usage_summary(db)

        recent_sessions = [
            RecentSession(
                id=str(s["id"]),
                request_id=s.get("request_id"),
                user_id=str(s["user_id"]),
                user_email=s.get("user_email"),
                model_id=str(s["model_id"]),
                model_name=s.get("model_name"),
                status=str(s["status"]),
                provider=s.get("provider"),
                endpoint=s.get("endpoint"),
                credential_name=s.get("credential_name"),
                final_cost_credits=float(s.get("final_cost_credits", 0)),
                total_tokens=int(s.get("total_tokens", 0)),
                created_at=s["created_at"],
                completed_at=s.get("completed_at"),
            )
            for s in summary["recent_sessions"]
        ]

        by_model = [
            ModelUsageStat(
                model_id=str(m["model_id"]),
                model_name=m.get("model_name"),
                requests=int(m.get("requests", 0)),
                used_credits=float(m.get("used_credits", 0)),
            )
            for m in summary["by_model"]
        ]

        return AdminUsageSummary(recent_sessions=recent_sessions, by_model=by_model)

    @strawberry.field
    async def admin_dashboard_data(self, info: strawberry.Info) -> AdminDashboardData:
        # Run independent analytical aggregation queries in parallel over DB pool
        async def _run(fn, *args):
            async with SessionLocal() as db:
                return await fn(db, *args)

        summary_data, by_provider_data, by_model_data, top_users_data, errors_data, quota_data = await asyncio.gather(
            _run(usage_summary),
            _run(usage_group_by, "provider"),
            _run(usage_group_by, "model"),
            _run(usage_group_by, "user"),
            _run(usage_group_by, "error"),
            _run(quota_summary),
        )

        return AdminDashboardData(
            summary=UsageSummary(**summary_data),
            by_provider=[UsageByProvider(**p) for p in by_provider_data],
            by_model=[UsageByModel(**m) for m in by_model_data],
            top_users=[UsageByUser(**u) for u in top_users_data],
            errors=[UsageByError(**e) for e in errors_data],
            quota=QuotaSummary(**quota_data),
        )

    @strawberry.field
    async def user_dashboard_data(self, info: strawberry.Info) -> UserDashboardData:
        current_user = info.context.get("current_user")
        request = info.context.get("request")
        if not current_user:
            req_id = getattr(getattr(request, "state", None), "request_id", "req-0") if request else "req-0"
            raise AppError("unauthorized", "User authentication required", req_id, 401)

        user_id = current_user.id

        async def _fetch_summary():
            async with SessionLocal() as db:
                wallet_obj = await get_wallet(db, user_id)
                used_credits = float(
                    (await db.execute(select(func.coalesce(func.sum(UsageSession.final_cost_credits), 0)).where(UsageSession.user_id == user_id))).scalar() or 0
                )
                usage_sessions = int((await db.execute(select(func.count()).select_from(UsageSession).where(UsageSession.user_id == user_id))).scalar() or 0)
                available_models = int((await db.execute(select(func.count()).select_from(PublicModel).where(PublicModel.enabled.is_(True)))).scalar() or 0)
                return {
                    "balance_credits": float(wallet_obj.balance_credits),
                    "used_credits": used_credits,
                    "usage_sessions": usage_sessions,
                    "available_models": available_models,
                }

        async def _fetch_ledger():
            async with SessionLocal() as db:
                entries = await list_ledger(db, user_id, limit=10)
                return [
                    UserLedgerEntry(
                        id=e.id,
                        entry_type=e.entry_type,
                        amount_credits=float(e.amount_credits),
                        status=getattr(e, "status", None),
                        created_at=e.created_at.isoformat() if hasattr(e, "created_at") and e.created_at else None,
                    )
                    for e in entries
                ]

        summary_res, ledger_res = await asyncio.gather(_fetch_summary(), _fetch_ledger())

        return UserDashboardData(
            summary=UserSummary(
                balance_credits=summary_res["balance_credits"],
                used_credits=summary_res["used_credits"],
                usage_sessions=summary_res["usage_sessions"],
                available_models=summary_res["available_models"],
            ),
            balance_credits=summary_res["balance_credits"],
            ledger=ledger_res,
            user_email=getattr(current_user, "email", "") or getattr(current_user, "name", "") or "-",
        )





async def get_context(
    request: Request,
    authorization: str | None = Header(default=None),
    x_admin_authorization: str | None = Header(default=None, alias="X-Admin-Authorization"),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    db: AsyncSession = Depends(get_db),
):
    current_user = None
    is_admin = False

    if x_admin_authorization or x_admin_token:
        try:
            await assert_admin_access(
                request=request,
                authorization=authorization,
                x_admin_authorization=x_admin_authorization,
                x_admin_token=x_admin_token,
                db=db,
                client=BasaltPassClient(),
            )
            is_admin = True
        except Exception:
            pass

    if authorization or request.cookies.get(settings.auth_cookie_name):
        try:
            current_user = await get_current_user(request=request, authorization=authorization, db=db)
        except Exception:
            pass

    return {
        "db": db,
        "request": request,
        "current_user": current_user,
        "is_admin": is_admin,
    }


schema = strawberry.Schema(query=Query)

router = GraphQLRouter(
    schema=schema,
    dependencies=[Depends(require_admin_access)],
    context_getter=get_context,
)