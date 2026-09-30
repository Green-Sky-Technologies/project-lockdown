"""Notification-preferences repository.

One channel value per account, riding on ``accounts.notify_channel``. ``get``
satisfies the dispatcher's ``ChannelPrefs`` protocol (it may raise; the
dispatcher catches). ``set`` raises to the router so a failed save surfaces as a
5xx rather than silently keeping the old channel.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from lockdown_core.persistence.repository import get_or_create_account


class NotificationPreferencesRepository:
    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        self._sessionmaker = sessionmaker

    async def get(self, *, clerk_user_id: str, clerk_org_id: str | None = None) -> str:
        async with self._sessionmaker() as session:
            account = await get_or_create_account(
                session, clerk_user_id=clerk_user_id, clerk_org_id=clerk_org_id
            )
            channel = account.notify_channel
            await session.commit()  # persist the account if it was just created
            return channel

    async def set(
        self, *, clerk_user_id: str, clerk_org_id: str | None = None, channel: str
    ) -> str:
        async with self._sessionmaker() as session:
            account = await get_or_create_account(
                session, clerk_user_id=clerk_user_id, clerk_org_id=clerk_org_id
            )
            account.notify_channel = channel
            await session.commit()
            return channel
