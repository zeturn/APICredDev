from typing import Optional
import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db
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
        db = info.context["db"]
        
        # Sequentially await to avoid asyncpg single connection concurrent issues
        summary_data = await usage_summary(db)
        by_provider_data = await usage_group_by(db, "provider")
        by_model_data = await usage_group_by(db, "model")
        top_users_data = await usage_group_by(db, "user")
        errors_data = await usage_group_by(db, "error")
        quota_data = await quota_summary(db)
        
        return AdminDashboardData(
            summary=UsageSummary(**summary_data),
            by_provider=[UsageByProvider(**p) for p in by_provider_data],
            by_model=[UsageByModel(**m) for m in by_model_data],
            top_users=[UsageByUser(**u) for u in top_users_data],
            errors=[UsageByError(**e) for e in errors_data],
            quota=QuotaSummary(**quota_data)
        )

async def get_context(db: AsyncSession = Depends(get_db)):
    return {"db": db}

schema = strawberry.Schema(query=Query)

router = GraphQLRouter(schema, context_getter=get_context)