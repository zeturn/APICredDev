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

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.services.admin_access import assert_admin_access
from app.services.basaltpass_client import BasaltPassClient



def _get_basalt_client() -> BasaltPassClient:
    return BasaltPassClient()

# ``get_basalt_client`` is the public entry point kept for test imports that
# reach into ``app.api.v1.admin``.  It is intentionally an alias for the same
# factory object registered as a FastAPI dependency — overriding either name on
# an app's dependency map therefore overrides both.
#
# See: tests/test_api_extended.py and tests/test_api_smoke.py which import it via:
#     ``from app.api.v1.admin import get_basalt_client``
get_basalt_client = _get_basalt_client


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
    if x_admin_authorization or x_admin_token:
        await assert_admin_access(
            request=request,
            authorization=authorization,
            x_admin_authorization=x_admin_authorization,
            x_admin_token=x_admin_token,
            db=db,
            client=client,
        )
        return

    if authorization or request.cookies.get(settings.auth_cookie_name):
        await get_current_user(request=request, authorization=authorization, db=db)
        return

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
