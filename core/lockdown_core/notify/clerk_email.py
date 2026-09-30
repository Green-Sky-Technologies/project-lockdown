"""Parent-email resolution via the Clerk Backend API.

The account row deliberately stores no contact info (§8: privacy-minimal) — the
parent's address is looked up from Clerk at send time, off the response path.
Imports ``clerk_backend_api`` and is therefore wired only at the composition
root (``app.py``), never from the hot path — the architecture test enforces it.
"""

from __future__ import annotations

import logging

from lockdown_core.notify.dispatcher import EmailResolver

logger = logging.getLogger("lockdown.notify")


def build_clerk_email_resolver(secret_key: str | None) -> EmailResolver:
    """Return an async ``clerk_user_id -> email | None`` resolver.

    Without a secret key the resolver always returns None (logged once per call
    site by the dispatcher's "no email resolvable" warning).
    """
    from clerk_backend_api import Clerk

    async def resolve(clerk_user_id: str) -> str | None:
        if not secret_key:
            return None
        try:
            async with Clerk(bearer_auth=secret_key) as clerk:
                user = await clerk.users.get_async(user_id=clerk_user_id)
        except Exception:  # noqa: BLE001 — resolution failure = no delivery, never a crash
            logger.exception("Clerk lookup failed for user %s", clerk_user_id)
            return None

        addresses = getattr(user, "email_addresses", None) or []
        primary_id = getattr(user, "primary_email_address_id", None)
        for addr in addresses:
            if primary_id and getattr(addr, "id", None) == primary_id:
                return getattr(addr, "email_address", None)
        # No primary marked (or it dangles): fall back to the first address.
        return getattr(addresses[0], "email_address", None) if addresses else None

    return resolve
