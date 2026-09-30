"""Notification preferences: repo round-trip (async SQLite) and the
/notification-settings endpoints — mirroring test_device_tokens.py."""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import lockdown_core.app as appmod
from lockdown_core.persistence.models import Base
from lockdown_core.persistence.preferences import NotificationPreferencesRepository
from lockdown_core.settings import Settings


async def _repo() -> NotificationPreferencesRepository:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return NotificationPreferencesRepository(async_sessionmaker(engine, expire_on_commit=False))


# --- repo round-trip --------------------------------------------------------- #
def test_default_channel_is_dashboard_only():
    async def run():
        repo = await _repo()
        assert await repo.get(clerk_user_id="user_parent") == "dashboard_only"

    asyncio.run(run())


def test_set_then_get_round_trip_and_per_user_scoping():
    async def run():
        repo = await _repo()
        assert await repo.set(clerk_user_id="user_a", channel="email") == "email"
        assert await repo.get(clerk_user_id="user_a") == "email"
        # Another account keeps its own default.
        assert await repo.get(clerk_user_id="user_b") == "dashboard_only"

    asyncio.run(run())


# --- endpoints --------------------------------------------------------------- #
def _client(prefs_repo) -> TestClient:
    import lockdown_core.app as appmod_local

    app = appmod_local.create_app(
        Settings(
            _env_file=None,
            use_fake_classifier=True,
            use_langgraph_pipeline=False,
            require_auth=False,  # clerk authorizer returns the local-dev context
        )
    )
    return TestClient(app)


def test_endpoints_get_put_and_sms_rejection(monkeypatch):
    prefs_repo = asyncio.run(_repo())
    monkeypatch.setattr(appmod, "_build_persistence", lambda s: (None, None, prefs_repo))
    client = _client(prefs_repo)

    r = client.get("/notification-settings")
    assert r.status_code == 200 and r.json() == {"channel": "dashboard_only"}

    r = client.put("/notification-settings", json={"channel": "email"})
    assert r.status_code == 200 and r.json() == {"channel": "email"}
    assert client.get("/notification-settings").json() == {"channel": "email"}

    # SMS is not offered until Twilio lands — the request model rejects it.
    r = client.put("/notification-settings", json={"channel": "sms"})
    assert r.status_code == 422
    # And the stored choice is untouched.
    assert client.get("/notification-settings").json() == {"channel": "email"}


def test_endpoints_503_without_store(monkeypatch):
    monkeypatch.setattr(appmod, "_build_persistence", lambda s: (None, None, None))
    client = _client(None)
    assert client.get("/notification-settings").status_code == 503
    assert client.put("/notification-settings", json={"channel": "email"}).status_code == 503
