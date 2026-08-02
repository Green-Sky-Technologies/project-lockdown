"""FastAPI auth dependencies, wired at the composition root (``app.py``).

``build_authorizer`` guards ``/classify``: it accepts EITHER a device token
(``pld_live_…`` — the extension's long-lived credential) OR a Clerk session JWT
(the dashboard), resolves the caller to an :class:`AuthContext`, and enforces the
per-account rate limit. ``build_clerk_authorizer`` guards the token-management
endpoints — those require a real Clerk login (a device token can't mint more
device tokens).

Both return the ``local-dev`` context when ``require_auth`` is off.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request

from lockdown_core.auth.clerk import LOCAL_DEV, AuthContext, AuthError, verify_request
from lockdown_core.auth.device_token import looks_like_device_token
from lockdown_core.auth.ratelimit import RateLimiter
from lockdown_core.settings import Settings

logger = logging.getLogger("lockdown.auth")

# Resolves a device-token plaintext to an AuthContext, or None if unknown/revoked.
DeviceResolver = Callable[[str], Awaitable[AuthContext | None]]


def _bearer(request: Request) -> str | None:
    """The bearer token value (scheme stripped), or None."""
    authz = request.headers.get("authorization") or request.headers.get("Authorization")
    if authz and authz.lower().startswith("bearer ") and len(authz) > 7:
        return authz[7:].strip()
    return None


def _verify_clerk(request: Request, settings: Settings) -> AuthContext:
    try:
        return verify_request(
            request,
            secret_key=settings.clerk_secret_key,
            authorized_parties=settings.clerk_authorized_parties,
        )
    except AuthError as e:
        # 401 to the caller (no reason leaked), but log the reason + configured
        # authorized_parties server-side so misconfigured deploys are debuggable.
        logger.warning("auth rejected: %s | authorized_parties=%s", e, settings.clerk_authorized_parties)
        raise HTTPException(status_code=401, detail="authentication required") from e


def build_authorizer(
    settings: Settings,
    limiter: RateLimiter,
    device_resolver: DeviceResolver | None = None,
) -> Callable[[Request], Awaitable[AuthContext]]:
    async def authorize(request: Request) -> AuthContext:
        if not settings.require_auth:
            auth = LOCAL_DEV
        else:
            token = _bearer(request)
            if token and looks_like_device_token(token) and device_resolver is not None:
                auth = await device_resolver(token)
                if auth is None:
                    logger.warning("auth rejected: invalid or revoked device token")
                    raise HTTPException(status_code=401, detail="authentication required")
            else:
                auth = _verify_clerk(request, settings)

        if not limiter.check(auth.user_id):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        return auth

    return authorize


def build_clerk_authorizer(settings: Settings) -> Callable[[Request], Awaitable[AuthContext]]:
    """Clerk-only guard for token management (device tokens are not accepted here)."""

    async def authorize(request: Request) -> AuthContext:
        if not settings.require_auth:
            return LOCAL_DEV
        return _verify_clerk(request, settings)

    return authorize
