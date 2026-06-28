import base64
import hashlib
import secrets
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import _get_cross_app_bearer_token, get_current_user, get_db, permission
from app.core.errors import AppError
from app.core.security import create_access_token, hash_api_token
from app.core.time import utc_now
from app.db.models.api_token import ApiToken
from app.schemas.auth import AdminTokenResponse, LoginRequest, LoginResponse, MeResponse, RegisterRequest
from app.services.auth_service import get_or_create_oauth_user, login_user, register_user
from app.services.admin_access import issue_admin_access_token
from app.services.basaltpass_client import BasaltPassClient


router = APIRouter(prefix='/auth', tags=['auth'])
runtime_auth_router = APIRouter(prefix='/runtime/auth', tags=['runtime-auth'])
OAUTH_STATE_COOKIE = 'apicred_basalt_oauth_state'
OAUTH_VERIFIER_COOKIE = 'apicred_basalt_oauth_verifier'
OAUTH_NONCE_COOKIE = 'apicred_basalt_oauth_nonce'
OAUTH_NEXT_COOKIE = 'apicred_basalt_oauth_next'
OAUTH_COOKIE_PATH = '/v1/auth/basalt'
OAUTH_COOKIE_MAX_AGE = 600


class RuntimeAuthVerifyRequest(BaseModel):
    purpose: str | None = None
    access_token: str | None = None
    authorization: str | None = None
    forwarded_user_id: str | None = None
    forwarded_tenant: str | None = None


def get_basalt_client() -> BasaltPassClient:
    return BasaltPassClient()


def _auth_cookie_secure() -> bool:
    return settings.apicred_public_base_url.startswith('https://')


def _set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.auth_cookie_name,
        token,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
        secure=_auth_cookie_secure(),
        max_age=settings.jwt_exp_minutes * 60,
        path='/',
    )


def _clear_access_cookie(response: Response) -> None:
    response.delete_cookie(settings.auth_cookie_name, path='/')


def _allow_local_auth(request: Request) -> bool:
    if settings.allow_local_password_auth:
        return True
    if not settings.allow_test_cli_local_auth:
        return False
    is_test_env = settings.app_env == 'test' or (request.url.hostname or '').strip().lower() == 'test'
    if not is_test_env:
        return False
    client_type = (request.headers.get('X-APICRED-Client') or '').strip().lower()
    user_agent = (request.headers.get('User-Agent') or '').strip().lower()
    is_cli = client_type == 'cli' or 'python-httpx' in user_agent or 'curl' in user_agent or 'powershell' in user_agent
    if not is_cli:
        return False
    shared_secret = (request.headers.get('X-APICRED-CLI-Auth') or '').strip()
    if settings.test_cli_auth_secret:
        return shared_secret == settings.test_cli_auth_secret
    return True


def _test_cli_context(request: Request) -> bool:
    is_test_env = settings.app_env == 'test' or (request.url.hostname or '').strip().lower() == 'test'
    user_agent = (request.headers.get('User-Agent') or '').strip().lower()
    return is_test_env and ('python-httpx' in user_agent or 'curl' in user_agent or 'powershell' in user_agent or (request.headers.get('X-APICRED-Client') or '').strip().lower() == 'cli')


def _assert_local_auth_allowed(request: Request) -> None:
    if _allow_local_auth(request):
        return
    raise AppError('local_auth_disabled', 'local login/register is disabled; use BasaltPass SSO', request.state.request_id, 403)


def _extract_bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    scheme, _, token = value.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token.strip()
    return value.strip()


@runtime_auth_router.post('/verify')
async def runtime_auth_verify(
    payload: RuntimeAuthVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    raw = _extract_bearer_token(payload.access_token) or _extract_bearer_token(payload.authorization)
    if not raw:
        return {"allowed": False, "active": False, "reason": "token_missing"}

    if raw.startswith("bp_xat_"):
        try:
            token = await _get_cross_app_bearer_token(request, raw, db)
        except AppError as exc:
            return {"allowed": False, "active": False, "reason": exc.code}
        return {
            "allowed": True,
            "active": True,
            "user_id": token.user_id,
            "tenant": token.basalt_tenant_id,
            "tenant_id": token.basalt_tenant_id,
            "scopes": token.scopes,
            "auth_source": "basalt_cross_app",
            "client_id": token.basalt_client_id,
        }

    token_hash = hash_api_token(raw)
    result = await db.execute(select(ApiToken).where(ApiToken.token_hash == token_hash))
    token = result.scalar_one_or_none()
    if not token or token.status != "active":
        return {"allowed": False, "active": False, "reason": "token_invalid"}
    token.last_used_at = utc_now()
    await db.commit()
    return {
        "allowed": True,
        "active": True,
        "user_id": token.user_id,
        "scopes": token.scopes or [],
        "auth_source": "apicred_token",
    }


@router.post('/register', response_model=MeResponse)
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)) -> MeResponse:
    _assert_local_auth_allowed(request)
    request_id = request.state.request_id
    try:
        user = await register_user(db, payload.email, payload.password)
    except ValueError:
        raise AppError('email_exists', 'email already exists', request_id, 400)
    return MeResponse(id=user.id, email=user.email, status=user.status)


@router.post('/login', response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    _assert_local_auth_allowed(request)
    request_id = request.state.request_id
    try:
        token = await login_user(db, payload.email, payload.password)
    except ValueError:
        raise AppError('invalid_credentials', 'invalid credentials', request_id, 401)
    _set_access_cookie(response, token)
    return LoginResponse(ok=True, access_token=token if _test_cli_context(request) else None)


@router.post('/logout')
async def logout(response: Response) -> dict[str, bool]:
    _clear_access_cookie(response)
    return {'ok': True}


@router.get('/me', response_model=MeResponse)
async def me(
    user=Depends(get_current_user),
    _: None = Depends(permission("user_console")),
) -> MeResponse:
    return MeResponse(id=user.id, email=user.email, status=user.status)


@router.get('/admin-token', response_model=AdminTokenResponse)
async def admin_token(
    request: Request,
    user=Depends(get_current_user),
    client: BasaltPassClient = Depends(get_basalt_client),
) -> AdminTokenResponse:
    try:
        admin_access_token = await issue_admin_access_token(user, client)
    except PermissionError:
        raise AppError('admin_unauthorized', 'missing admin role', request.state.request_id, 403)
    except ValueError as exc:
        raise AppError('admin_check_unavailable', str(exc), request.state.request_id, 503)
    return AdminTokenResponse(
        admin_access_token=admin_access_token,
        expires_in=settings.admin_jwt_exp_minutes * 60,
    )


def _safe_next(next_path: str | None) -> str:
    if not next_path:
        return '/workspace/dashboard'
    if next_path.startswith('/'):
        return next_path
    return '/workspace/dashboard'


def _extract_email(data: dict[str, Any]) -> str | None:
    candidates = [
        data.get('email'),
        data.get('user', {}).get('email') if isinstance(data.get('user'), dict) else None,
        data.get('data', {}).get('email') if isinstance(data.get('data'), dict) else None,
        data.get('profile', {}).get('email') if isinstance(data.get('profile'), dict) else None,
    ]
    for value in candidates:
        if isinstance(value, str) and value:
            return value
    return None


def _extract_claim(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _urlsafe_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _create_pkce_pair() -> tuple[str, str]:
    verifier = _urlsafe_b64(secrets.token_bytes(32))
    challenge = _urlsafe_b64(hashlib.sha256(verifier.encode('ascii')).digest())
    return verifier, challenge


def _build_callback_url(provider: str | None = None) -> str:
    base = settings.apicred_public_base_url.rstrip('/')
    if provider:
        return f'{base}/v1/auth/basalt/oauth/{provider}/callback'
    return f'{base}/v1/auth/basalt/callback'


def _build_authorize_url(redirect_uri: str, state: str, challenge: str, nonce: str) -> str:
    if not settings.basalt_oauth_client_id:
        raise ValueError('missing BASALT_OAUTH_CLIENT_ID')
    params: dict[str, str] = {
        'response_type': 'code',
        'client_id': settings.basalt_oauth_client_id,
        'redirect_uri': redirect_uri,
        'scope': settings.basalt_oauth_scopes,
        'state': state,
        'nonce': nonce,
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
    }
    if settings.basalt_oauth_audience:
        params['audience'] = settings.basalt_oauth_audience
    return str(httpx.URL(f"{settings.basalt_base_url.rstrip('/')}/api/v1/oauth/authorize", params=params))


def _set_oauth_cookies(resp: RedirectResponse, *, state: str, verifier: str, nonce: str, next_path: str) -> None:
    cookie_kwargs = {
        'httponly': True,
        'samesite': 'lax',
        'secure': settings.apicred_public_base_url.startswith('https://'),
        'max_age': OAUTH_COOKIE_MAX_AGE,
        'path': OAUTH_COOKIE_PATH,
    }
    resp.set_cookie(OAUTH_STATE_COOKIE, state, **cookie_kwargs)
    resp.set_cookie(OAUTH_VERIFIER_COOKIE, verifier, **cookie_kwargs)
    resp.set_cookie(OAUTH_NONCE_COOKIE, nonce, **cookie_kwargs)
    resp.set_cookie(OAUTH_NEXT_COOKIE, next_path, **cookie_kwargs)


def _clear_oauth_cookies(resp: RedirectResponse) -> None:
    resp.delete_cookie(OAUTH_STATE_COOKIE, path=OAUTH_COOKIE_PATH)
    resp.delete_cookie(OAUTH_VERIFIER_COOKIE, path=OAUTH_COOKIE_PATH)
    resp.delete_cookie(OAUTH_NONCE_COOKIE, path=OAUTH_COOKIE_PATH)
    resp.delete_cookie(OAUTH_NEXT_COOKIE, path=OAUTH_COOKIE_PATH)


async def _exchange_oauth_code(code: str, code_verifier: str, redirect_uri: str, request_id: str) -> dict[str, Any]:
    payload = {
        'grant_type': 'authorization_code',
        'client_id': settings.basalt_oauth_client_id,
        'code': code,
        'redirect_uri': redirect_uri,
        'code_verifier': code_verifier,
    }
    if settings.basalt_oauth_client_secret:
        payload['client_secret'] = settings.basalt_oauth_client_secret
    token_url = f"{settings.basalt_internal_base_url.rstrip('/')}/api/v1/oauth/token"
    try:
        async with httpx.AsyncClient(timeout=settings.basalt_timeout_seconds) as client:
            response = await client.post(token_url, data=payload)
    except httpx.RequestError as exc:
        raise AppError('basalt_unreachable', str(exc), request_id, 502)
    if response.status_code >= 400:
        raise AppError('basalt_oauth_failed', f'token exchange failed: {response.text}', request_id, 502)
    try:
        return response.json()
    except ValueError:
        raise AppError('basalt_oauth_failed', 'token exchange returned invalid json', request_id, 502)


async def _fetch_userinfo(access_token: str, request_id: str) -> dict[str, Any]:
    userinfo_url = f"{settings.basalt_internal_base_url.rstrip('/')}/api/v1/oauth/userinfo"
    try:
        async with httpx.AsyncClient(timeout=settings.basalt_timeout_seconds) as client:
            response = await client.get(
                userinfo_url,
                headers={'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'},
            )
    except httpx.RequestError as exc:
        raise AppError('basalt_unreachable', str(exc), request_id, 502)
    if response.status_code >= 400:
        raise AppError('basalt_oauth_failed', f'userinfo failed: status {response.status_code}', request_id, 502)
    try:
        return response.json()
    except ValueError:
        raise AppError('basalt_oauth_failed', 'userinfo returned invalid json', request_id, 502)


def _claims_from_id_token(id_token: str | None) -> dict[str, Any]:
    if not id_token:
        return {}
    try:
        claims = jwt.get_unverified_claims(id_token)
        if isinstance(claims, dict):
            return claims
    except JWTError:
        pass
    return {}


async def _handle_oauth_callback(
    request: Request,
    db: AsyncSession,
    *,
    code: str | None,
    state: str | None,
    error: str | None,
    error_description: str | None,
    provider: str | None,
) -> RedirectResponse:
    request_id = request.state.request_id
    if error:
        msg = error
        if error_description:
            msg = f'{error}: {error_description}'
        raise AppError('basalt_oauth_failed', msg, request_id, 400)

    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
    verifier = request.cookies.get(OAUTH_VERIFIER_COOKIE)
    expected_nonce = request.cookies.get(OAUTH_NONCE_COOKIE)
    next_path = _safe_next(request.cookies.get(OAUTH_NEXT_COOKIE) or request.query_params.get('next'))
    if not state or not cookie_state or state != cookie_state:
        raise AppError('oauth_state_invalid', 'invalid oauth state', request_id, 400)
    if not verifier:
        raise AppError('oauth_state_invalid', 'missing oauth verifier', request_id, 400)
    if not code:
        raise AppError('basalt_oauth_failed', 'missing authorization code', request_id, 400)

    redirect_uri = _build_callback_url(provider=provider)
    token_payload = await _exchange_oauth_code(code=code, code_verifier=verifier, redirect_uri=redirect_uri, request_id=request_id)
    access_token = token_payload.get('access_token')
    if not isinstance(access_token, str) or not access_token:
        raise AppError('basalt_oauth_failed', 'missing access token', request_id, 502)

    userinfo = await _fetch_userinfo(access_token, request_id)
    claims = _claims_from_id_token(token_payload.get('id_token'))
    token_nonce = claims.get('nonce') if isinstance(claims, dict) else None
    if isinstance(token_payload.get('id_token'), str) and (not expected_nonce or token_nonce != expected_nonce):
        raise AppError('oauth_nonce_invalid', 'invalid id_token nonce', request_id, 400)
    email = _extract_email(userinfo) or _extract_claim(claims, 'email')
    basalt_user_id = _extract_claim(userinfo, 'sub', 'id', 'user_id') or _extract_claim(claims, 'sub')
    basalt_tenant_id = _extract_claim(userinfo, 'tid', 'tenant_id') or _extract_claim(claims, 'tid', 'tenant_id')

    if not email:
        raise AppError('basalt_email_missing', 'missing email from oauth userinfo', request_id, 400)
    if not basalt_user_id:
        raise AppError('basalt_user_missing', 'missing sub from oauth userinfo', request_id, 400)

    user = await get_or_create_oauth_user(
        db,
        email=email,
        basalt_user_id=basalt_user_id,
        basalt_tenant_id=basalt_tenant_id,
    )
    token = create_access_token(user.id)
    frontend_next_url = f"{settings.frontend_base_url.rstrip('/')}{next_path}"
    resp = RedirectResponse(url=frontend_next_url, status_code=302)
    _set_access_cookie(resp, token)
    _clear_oauth_cookies(resp)
    return resp


@router.get('/basalt/login')
async def basalt_oauth_login(request: Request, next: str | None = None) -> RedirectResponse:
    safe_next = _safe_next(next)
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    verifier, challenge = _create_pkce_pair()
    callback_url = _build_callback_url(provider=None)
    try:
        login_url = _build_authorize_url(callback_url, state, challenge, nonce)
    except ValueError as exc:
        raise AppError('config_invalid', str(exc), request.state.request_id, status_code=500)
    resp = RedirectResponse(url=login_url, status_code=302)
    _set_oauth_cookies(resp, state=state, verifier=verifier, nonce=nonce, next_path=safe_next)
    return resp


@router.get('/basalt/oauth/{provider}/login')
async def basalt_oauth_login_legacy(provider: str, request: Request, next: str | None = None) -> RedirectResponse:
    safe_next = _safe_next(next)
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    verifier, challenge = _create_pkce_pair()
    callback_url = _build_callback_url(provider=provider)
    try:
        login_url = _build_authorize_url(callback_url, state, challenge, nonce)
    except ValueError as exc:
        raise AppError('config_invalid', str(exc), request.state.request_id, status_code=500)
    resp = RedirectResponse(url=login_url, status_code=302)
    _set_oauth_cookies(resp, state=state, verifier=verifier, nonce=nonce, next_path=safe_next)
    return resp


@router.get('/basalt/callback')
async def basalt_oauth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    return await _handle_oauth_callback(
        request,
        db,
        code=code,
        state=state,
        error=error,
        error_description=error_description,
        provider=None,
    )


@router.get('/basalt/oauth/{provider}/callback')
async def basalt_oauth_callback_legacy(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    return await _handle_oauth_callback(
        request,
        db,
        code=code,
        state=state,
        error=error,
        error_description=error_description,
        provider=provider,
    )
