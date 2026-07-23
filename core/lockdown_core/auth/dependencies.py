"""FastAPI auth dependency, wired at the composition root (``app.py``).

``build_authorizer`` closes over settings + a rate limiter and returns a single
dependency that (1) resolves the caller to an :class:`AuthContext` (or the
local-dev context when ``require_auth`` is off), and (2) enforces the per-account
rate limit — 401 for anonymous, 429 when over the limit.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request

from lockdown_core.auth.clerk import LOCAL_DEV, AuthContext, AuthError, verify_request
from lockdown_core.auth.ratelimit import RateLimiter
from lockdown_core.settings import Settings


def build_authorizer(settings: Settings, limiter: RateLimiter) -> Callable[[Request], AuthContext]:
    def authorize(request: Request) -> AuthContext:
        if settings.require_auth:
            try:
                auth = verify_request(
                    request,
                    secret_key=settings.clerk_secret_key,
                    authorized_parties=settings.clerk_authorized_parties,
                )
            except AuthError:
                # Don't leak the reason to the caller; log server-side if needed.
                raise HTTPException(status_code=401, detail="authentication required")
        else:
            auth = LOCAL_DEV

        if not limiter.check(auth.user_id):
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        return auth

    return authorize
