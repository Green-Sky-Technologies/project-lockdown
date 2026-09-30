"""``/notification-settings`` — parent-facing channel choice.

Called by the dashboard (with the parent's Clerk session), same posture as
``/device-tokens``. Imports the sqlalchemy-backed prefs repository, so this
module is wired only at the composition root — never exported from
``notify/__init__`` (the architecture test enforces the hot path stays clean).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from lockdown_core.auth.clerk import AuthContext
from lockdown_core.persistence.preferences import NotificationPreferencesRepository


class NotificationSettingsView(BaseModel):
    channel: Literal["dashboard_only", "email", "sms"]


class UpdateNotificationSettings(BaseModel):
    # "sms" is deliberately absent until Twilio lands — requesting it 422s.
    channel: Literal["dashboard_only", "email"]


def build_notification_settings_router(
    repository: NotificationPreferencesRepository | None,
    authorize: Callable[[Request], Awaitable[AuthContext]],
) -> APIRouter:
    router = APIRouter(prefix="/notification-settings", tags=["notification-settings"])

    def _repo() -> NotificationPreferencesRepository:
        if repository is None:
            raise HTTPException(status_code=503, detail="preferences store not configured")
        return repository

    @router.get("", response_model=NotificationSettingsView)
    async def get_settings(auth: AuthContext = Depends(authorize)) -> NotificationSettingsView:
        channel = await _repo().get(clerk_user_id=auth.user_id, clerk_org_id=auth.org_id)
        return NotificationSettingsView(channel=channel)

    @router.put("", response_model=NotificationSettingsView)
    async def update_settings(
        body: UpdateNotificationSettings, auth: AuthContext = Depends(authorize)
    ) -> NotificationSettingsView:
        channel = await _repo().set(
            clerk_user_id=auth.user_id, clerk_org_id=auth.org_id, channel=body.channel
        )
        return NotificationSettingsView(channel=channel)

    return router
