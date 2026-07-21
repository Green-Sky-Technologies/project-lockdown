"""Clerk session-token verification.

Wraps ``clerk_backend_api.authenticate_request`` (networkless JWKS verification,
keys cached ~5 min). Returns an :class:`AuthContext` identifying the account, or
raises :class:`AuthError` for the caller to turn into a 401.
"""

from __future__ import annotations

from dataclasses import dataclass

from clerk_backend_api import AuthenticateRequestOptions, authenticate_request


@dataclass(frozen=True)
class AuthContext:
    """The authenticated caller. ``tier`` seeds family vs. school routing (§6)."""

    user_id: str
    org_id: str | None = None
    tier: str = "family"


# Returned when auth is disabled for local dev (settings.require_auth = False).
LOCAL_DEV = AuthContext(user_id="local-dev", org_id=None, tier="family")


class AuthError(Exception):
    """Raised when a request is not authenticated."""


def _has_session_token(request) -> bool:
    """True if the request carries a bearer token or a Clerk ``__session`` cookie.

    We short-circuit the no-token case so an anonymous request 401s immediately
    without a JWKS/network round-trip (and so tests need no network)."""
    authz = request.headers.get("authorization") or request.headers.get("Authorization")
    if authz and authz.lower().startswith("bearer ") and len(authz) > 7:
        return True
    cookie = request.headers.get("cookie") or ""
    return "__session=" in cookie


def verify_request(
    request,
    *,
    secret_key: str | None,
    authorized_parties: list[str],
) -> AuthContext:
    """Verify a Clerk session token on ``request``. Raises ``AuthError`` if absent
    or invalid."""
    if not _has_session_token(request):
        raise AuthError("no session token")
    if not secret_key:
        # Misconfiguration: auth required but no key to verify against.
        raise AuthError("clerk secret key not configured")

    state = authenticate_request(
        request,
        AuthenticateRequestOptions(
            secret_key=secret_key,
            # Must be a real list (a comma-string → TOKEN_INVALID_AUTHORIZED_PARTIES).
            # Empty list → skip the azp check.
            authorized_parties=authorized_parties or None,
        ),
    )
    if not state.is_signed_in:
        raise AuthError(f"not signed in: {state.reason}")

    payload = state.payload or {}
    org_id = payload.get("org_id")
    return AuthContext(
        user_id=payload["sub"],
        org_id=org_id,
        tier="school" if org_id else "family",
    )
