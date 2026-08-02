"""Device-token auth: mint/hash purity, repo round-trip, and the /classify path.

Covers the extension's long-lived credential end to end without Clerk or Neon:
an in-memory SQLite device-token repo is injected, and /classify is exercised
with a real ``pld_live_…`` bearer — proving the device path authenticates,
attributes, and honors revocation.
"""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import lockdown_core.app as appmod
from lockdown_core.auth.device_token import generate, hash_token, looks_like_device_token
from lockdown_core.persistence.device_tokens import DeviceTokenRepository
from lockdown_core.persistence.models import Base
from lockdown_core.settings import Settings


# --- pure mint/hash ---------------------------------------------------------- #
def test_generate_is_prefixed_hashed_and_unique():
    p1, h1 = generate()
    p2, h2 = generate()
    assert p1.startswith("pld_live_") and looks_like_device_token(p1)
    assert p1 != p2 and h1 != h2  # 256 bits of entropy — no collisions
    assert h1 == hash_token(p1) and len(h1) == 64  # deterministic sha256 hex
    assert hash_token(" " + p1 + " ") == h1  # whitespace-tolerant (paste hygiene)


def test_clerk_jwt_is_not_mistaken_for_a_device_token():
    assert not looks_like_device_token("eyJhbGciOi.header.sig")


# --- repo round-trip --------------------------------------------------------- #
async def _repo() -> DeviceTokenRepository:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return DeviceTokenRepository(async_sessionmaker(engine, expire_on_commit=False))


def test_create_list_resolve_revoke_cycle():
    async def run():
        repo = await _repo()
        plaintext, info = await repo.create(
            clerk_user_id="user_parent", clerk_org_id=None, name="Emma's Chromebook"
        )
        assert plaintext.startswith("pld_live_") and info.name == "Emma's Chromebook"

        listed = await repo.list(clerk_user_id="user_parent")
        assert len(listed) == 1 and listed[0].revoked is False
        assert not hasattr(listed[0], "token")  # plaintext never re-exposed

        resolved = await repo.resolve(plaintext)
        assert resolved is not None and resolved.clerk_user_id == "user_parent"

        assert await repo.resolve("pld_live_bogus") is None  # unknown → None

        assert await repo.revoke(clerk_user_id="user_parent", token_id=info.id) is True
        assert await repo.resolve(plaintext) is None  # revoked → immediately dead

    asyncio.run(run())


def test_revoke_is_scoped_to_owner():
    async def run():
        repo = await _repo()
        _, info = await repo.create(clerk_user_id="owner", clerk_org_id=None, name="x")
        # A different account cannot revoke it.
        assert await repo.revoke(clerk_user_id="intruder", token_id=info.id) is False

    asyncio.run(run())


# --- /classify with a device token ------------------------------------------ #
def _classify_body(text: str) -> dict:
    return {
        "windowed_text": [{"role": "user", "text": text}],
        "category_set": ["VIOLENCE_TO_OTHERS"],
        "client_metadata": {
            "chatbot_host": "chatgpt.com",
            "capture_surface": "CHROMIUM_EXT",
            "monitored_categories": ["VIOLENCE_TO_OTHERS"],
        },
        "inline_tier2": True,
    }


def _app_with_token(monkeypatch, calls):
    """Build the app with require_auth ON and an in-memory device-token repo that
    already holds one token. Returns (client, plaintext)."""
    repo = asyncio.run(_repo())
    plaintext, _ = asyncio.run(
        repo.create(clerk_user_id="user_parent", clerk_org_id=None, name="ext")
    )

    class RecordingVerdictRepo:
        async def save(self, verdict, *, clerk_user_id, clerk_org_id=None):
            calls.append((verdict.recommended_action.value, clerk_user_id))

    monkeypatch.setattr(appmod, "_build_persistence", lambda s: (RecordingVerdictRepo(), repo))
    client = TestClient(
        appmod.create_app(
            Settings(
                _env_file=None,
                use_fake_classifier=True,
                use_langgraph_pipeline=False,
                require_auth=True,  # NB: no clerk_secret_key — device path never touches Clerk
                persist_verdicts=True,
            )
        )
    )
    return client, plaintext


def test_valid_device_token_authenticates_and_attributes(monkeypatch):
    calls: list = []
    client, plaintext = _app_with_token(monkeypatch, calls)
    r = client.post(
        "/classify",
        json=_classify_body("I'm planning to hurt Jake and I will get him"),
        headers={"Authorization": f"Bearer {plaintext}"},
    )
    assert r.status_code == 200
    # Attributed to the token's owner, not local-dev.
    assert calls == [("LOCK_AND_NOTIFY", "user_parent")]


def test_unknown_device_token_is_401(monkeypatch):
    client, _ = _app_with_token(monkeypatch, [])
    r = client.post(
        "/classify",
        json=_classify_body("hello"),
        headers={"Authorization": "Bearer pld_live_nope"},
    )
    assert r.status_code == 401
