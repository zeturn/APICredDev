"""Tests for the admin-only ``/graphql`` endpoint.

Covers:

* Unauthenticated GET / POST requests are rejected with **401**.
* A request carrying a valid ``X-Admin-Authorization`` bearer token reaches the
  schema and returns **200** (with data).
* An introspection query behaves identically — admin auth is required.

The tests bypass real BasaltPass calls by overriding :func:`require_admin_access`
to short-circuit to success — consistent with how other admin-route tests in this
project skip the full admin-token flow (see ``test_admin_provider_health_api.py``).
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.admin_auth import require_admin_access
from app.core.deps import get_db
from app.main import create_app


@pytest.mark.asyncio
async def test_graphql_rejects_unauthenticated_request():
    """``/graphql`` must deny unauthenticated callers — not the schema itself."""
    app = create_app()

    async def _allow_admin():
        return None

    async def _override_db():
        # Yield is needed because ``get_db`` returns an async generator.
        yield None

    app.dependency_overrides[require_admin_access] = _allow_admin
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET (default to schema introspection UI in strawberry).
        get_resp = await client.get("/graphql")
        assert get_resp.status_code == 401

        # 2. POST without ``X-Admin-Authorization`` header — plain JSON query.
        post_resp = await client.post(
            "/graphql",
            json={"query": "{ hello }"},
        )
        assert post_resp.status_code == 401


@pytest.mark.asyncio
async def test_graphql_returns_200_with_valid_admin_token():
    """A valid ``X-Admin-Authorization`` bearer token should reach the schema."""
    app = create_app()

    async def _allow_admin():
        return None

    async def _override_db():
        yield None

    app.dependency_overrides[require_admin_access] = _allow_admin
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # POST a simple query — the schema always exposes ``hello``.
        resp = await client.post(
            "/graphql",
            json={"query": "{ hello }"},
            headers={"X-Admin-Authorization": "Bearer test-admin-token"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        # Schema returns a data dict, not an error.
        assert "data" in payload
        assert payload["data"]["hello"] == "Hello from APICred GraphQL API!"


@pytest.mark.asyncio
async def test_graphql_rejects_expired_admin_token():
    """
    A request with an obviously malformed token must be rejected at the
    ``require_admin_access`` dependency level — not silently reach the schema.

    We do NOT override ``require_admin_access`` here, so the real JWT decoder
    runs and raises :class:`AppError` on a non-JWT value.
    """
    app = create_app()

    async def _override_db():
        yield None

    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # An obviously-non-JWT value must fail the JWT-decode step in
        # ``assert_admin_access``, which raises AppError(status_code=401).
        resp = await client.post(
            "/graphql",
            json={"query": "{ hello }"},
            headers={"X-Admin-Authorization": "Bearer totally-not-a-jwt"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_graphql_rejects_introspection_without_auth():
    """Introspection queries are served by the same route and must also require admin auth."""
    app = create_app()

    async def _allow_admin():
        return None

    async def _override_db():
        yield None

    app.dependency_overrides[require_admin_access] = _allow_admin
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Introspection query without admin header — must be rejected (401).
        resp = await client.post(
            "/graphql",
            json={
                "query": "{ __schema { types { name } } }",
            },
        )
        assert resp.status_code == 401
