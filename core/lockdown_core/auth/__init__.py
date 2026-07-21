"""Authentication for the core (Clerk).

Per-user login (design doc §6): the extension carries no long-lived secret; each
adult signs in via Clerk and sends a short-lived session JWT, which the core
verifies statelessly (JWKS). This keeps the endpoint from being abused — no
anonymous access, every call attributable to a rate-limited account.

IMPORTANT: this package imports ``clerk_backend_api`` and must be wired only at
the composition root (``app.py``), never from the classifier hot path
(design doc §4.3). An architecture test enforces it.
"""

from lockdown_core.auth.clerk import AuthContext, AuthError, LOCAL_DEV, verify_request

__all__ = ["AuthContext", "AuthError", "LOCAL_DEV", "verify_request"]
