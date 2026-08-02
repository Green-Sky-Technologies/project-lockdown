"""Device-token store: mint, list, revoke, and resolve extension credentials.

Mirrors the PAT model — the plaintext is returned once at ``create`` and never
persisted; every other operation works off the SHA-256 hash. ``resolve`` is the
hot-path read (runs in the /classify auth dependency): it hashes the incoming
token, looks up a non-revoked row, and returns the owning account's identity.

Like the verdict repo, this is wired only at the composition root (imports
sqlalchemy) — never from the classifier hot-path import graph (§4.3).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from lockdown_core.auth.device_token import generate, hash_token
from lockdown_core.persistence.models import Account, DeviceToken
from lockdown_core.persistence.repository import get_or_create_account

logger = logging.getLogger("lockdown.persistence")

# Coarsen the last_used_at write so a valid token doesn't cause a DB write on
# every single classify — only refresh it when it's stale by more than this.
_LAST_USED_REFRESH = timedelta(hours=1)


@dataclass(frozen=True)
class ResolvedToken:
    """The account a device token belongs to (adapted to AuthContext by the caller)."""

    clerk_user_id: str
    clerk_org_id: str | None
    tier: str


@dataclass(frozen=True)
class TokenInfo:
    """A token as shown in the dashboard list — never includes the plaintext."""

    id: str
    name: str
    created_at: str
    last_used_at: str | None
    revoked: bool


class DeviceTokenRepository:
    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        self._sessionmaker = sessionmaker

    async def create(
        self, *, clerk_user_id: str, clerk_org_id: str | None, name: str
    ) -> tuple[str, TokenInfo]:
        """Mint a token for the caller's account. Returns ``(plaintext, info)`` —
        the plaintext is the ONLY time it exists in cleartext."""
        plaintext, token_hash = generate()
        async with self._sessionmaker() as session:
            account = await get_or_create_account(
                session, clerk_user_id=clerk_user_id, clerk_org_id=clerk_org_id
            )
            token = DeviceToken(account_id=account.id, token_hash=token_hash, name=name or "")
            session.add(token)
            await session.commit()
            await session.refresh(token)
            return plaintext, _to_info(token)

    async def list(self, *, clerk_user_id: str) -> list[TokenInfo]:
        async with self._sessionmaker() as session:
            rows = (
                await session.execute(
                    select(DeviceToken)
                    .join(Account, DeviceToken.account_id == Account.id)
                    .where(Account.clerk_user_id == clerk_user_id)
                    .order_by(DeviceToken.created_at.desc())
                )
            ).scalars()
            return [_to_info(t) for t in rows]

    async def revoke(self, *, clerk_user_id: str, token_id: str) -> bool:
        """Revoke a token the caller owns. Returns False if it isn't theirs / absent.
        Scoped by clerk_user_id in the query — never trust the id alone."""
        try:
            token_uuid = uuid.UUID(token_id)
        except (ValueError, AttributeError):
            return False  # malformed id — treat as not-found, not a 500
        async with self._sessionmaker() as session:
            token = (
                await session.execute(
                    select(DeviceToken)
                    .join(Account, DeviceToken.account_id == Account.id)
                    .where(DeviceToken.id == token_uuid, Account.clerk_user_id == clerk_user_id)
                )
            ).scalar_one_or_none()
            if token is None:
                return False
            if token.revoked_at is None:
                token.revoked_at = datetime.now(timezone.utc)
                await session.commit()
            return True

    async def resolve(self, token: str) -> ResolvedToken | None:
        """Hot path: map a presented token to its account, or None if unknown/revoked.

        Revocation takes effect immediately (no cache). Bumps last_used_at at most
        once per hour to keep this a read on the common path."""
        token_hash = hash_token(token)
        try:
            async with self._sessionmaker() as session:
                result = (
                    await session.execute(
                        select(DeviceToken, Account)
                        .join(Account, DeviceToken.account_id == Account.id)
                        .where(DeviceToken.token_hash == token_hash)
                    )
                ).first()
                if result is None:
                    return None
                dt, account = result
                if dt.revoked_at is not None:
                    return None
                now = datetime.now(timezone.utc)
                if dt.last_used_at is None or now - _aware(dt.last_used_at) > _LAST_USED_REFRESH:
                    dt.last_used_at = now
                    await session.commit()
                return ResolvedToken(
                    clerk_user_id=account.clerk_user_id,
                    clerk_org_id=account.clerk_org_id,
                    tier=account.tier,
                )
        except Exception:  # noqa: BLE001 — a store hiccup must read as "not authed", not 500
            logger.exception("device-token resolve failed")
            return None


def _aware(dt: datetime) -> datetime:
    """SQLite round-trips naive datetimes; treat those as UTC for the staleness math."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _to_info(t: DeviceToken) -> TokenInfo:
    return TokenInfo(
        id=str(t.id),
        name=t.name,
        created_at=t.created_at.isoformat() if t.created_at else "",
        last_used_at=t.last_used_at.isoformat() if t.last_used_at else None,
        revoked=t.revoked_at is not None,
    )
