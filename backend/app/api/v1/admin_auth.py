"""Shared admin-access dependency used by multiple v1 sub-routers.

Extracted from ``admin.py`` so other routers (e.g. the GraphQL router) can
enforce the same policy without duplicating logic.

The contract is identical to ``require_admin_access`` on ``router.py``:::

    Read X-Admin-Authorization / Authorization headers, decode the admin JWT,
    verify it against BasaltPass roles and raise ``AppError`` when access is
    denied. The resolved user object is returned by the dependency.

All callers must depend on this (e.g. via FastAPI default router dependencies)
to ensure every route under their prefix is protected uniformly.
"""

from __future__ import annotations

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.admin_access import assert_admin_access
from app.services.basaltpass_client import BasaltPassClient


def _get_basalt_client() -> BasaltPassClient:
    return BasaltPassClient()


async def require_admin_access(
    request: Request,
    authorization: str | None = Header(default=None),
    x_admin_authorization: str | None = Header(
        default=None, alias="X-Admin-Authorization"
    ),
    x_admin_token: str | None = Header(
        default=None, alias="X-Admin-Token"
    ),
    db: AsyncSession = Depends(get_db),
    client: BasaltPassClient = Depends(_get_basalt_client),
) -> None:
    """Guards a route by asserting the request carries admin authority.

    Raises ``AppError`` with status 401/403 when authentication or authorization
    fails, matching the contract of the original dependency in ``admin.py``.
    """
    await assert_admin_access(
        request=request,
        authorization=authorization,
        x_admin_authorization=x_admin_authorization,
        x_admin_token=x_admin_token,
        db=db,
        client=client,
    )


# The module is imported directly by consumers — there is no router exposed
# here because each caller composes its own ``APIRouter`` with the dependency.
# See:  ``api/v1/admin.py`` for its own public admin router, and
#       ``api/v1/tableGraphql.py`` for how to wire it into a GraphQL endpoint.
