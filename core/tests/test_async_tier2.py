"""Async tier-2: /classify returns the PENDING lock immediately and finishes
verification (persist + notify) as a background task; /verdict-status is the
polling surface the extension unlocks/hardens from.

TestClient runs FastAPI background tasks before returning, so post-response
assertions see the finalized state.
"""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import lockdown_core.app as appmod
from lockdown_core.persistence.models import Base
from lockdown_core.persistence.repository import VerdictRepository
from lockdown_core.settings import Settings


def _body(text: str, *, inline_tier2: bool = False) -> dict:
    return {
        "windowed_text": [{"role": "user", "text": text}],
        "category_set": ["VIOLENCE_TO_OTHERS"],
        "client_metadata": {
            "chatbot_host": "chatgpt.com",
            "capture_surface": "CHROMIUM_EXT",
            "monitored_categories": ["VIOLENCE_TO_OTHERS"],
        },
        "inline_tier2": inline_tier2,
    }


class RecordingRepo:
    def __init__(self) -> None:
        self.saves: list[tuple[str, str]] = []  # (stage, status)

    async def save(self, verdict, *, clerk_user_id, clerk_org_id=None):
        self.saves.append((verdict.stage.value, verdict.status.value))

    async def get_status(self, verdict_id, *, clerk_user_id):
        return None


class RecordingDispatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []  # (action, status)

    async def dispatch(self, verdict, *, clerk_user_id, clerk_org_id=None):
        self.calls.append((verdict.recommended_action.value, verdict.status.value))


def _app(monkeypatch, repo):
    dispatcher = RecordingDispatcher()
    monkeypatch.setattr(appmod, "_build_persistence", lambda s: (repo, None, None))
    monkeypatch.setattr(appmod, "_build_dispatcher", lambda s, p: dispatcher)
    client = TestClient(
        appmod.create_app(
            Settings(
                _env_file=None,
                use_fake_classifier=True,
                use_langgraph_pipeline=False,
                require_auth=False,
            )
        )
    )
    return client, dispatcher


def test_async_lock_returns_pending_then_finalizes_in_background(monkeypatch):
    repo = RecordingRepo()
    client, dispatcher = _app(monkeypatch, repo)

    r = client.post("/classify", json=_body("I'm planning to hurt Jake and I will get him"))
    assert r.status_code == 200
    body = r.json()
    # The RESPONSE is the immediate tier-1 lock…
    assert (body["stage"], body["status"]) == ("TIER1", "PENDING")
    # …and the background task persisted both stages and notified on the
    # confirmed tier-2 verdict.
    assert repo.saves == [("TIER1", "PENDING"), ("TIER2", "CONFIRMED")]
    assert dispatcher.calls == [("LOCK_AND_NOTIFY", "CONFIRMED")]


def test_async_benign_never_runs_tier2(monkeypatch):
    repo = RecordingRepo()
    client, dispatcher = _app(monkeypatch, repo)

    r = client.post("/classify", json=_body("help me with my history essay about World War 2"))
    assert r.status_code == 200
    assert r.json()["status"] == "CLEARED"
    assert repo.saves == []  # NO_ACTION → not persisted, no tier-2 scheduled
    assert dispatcher.calls == []


def test_async_tier2_failure_leaves_pending_and_never_notifies(monkeypatch):
    from lockdown_core.classify.fake import FakeClassifier
    from lockdown_core.contract.verdict import Stage

    class Tier2Exploding(FakeClassifier):
        async def judge(self, *, tier, window, category):
            if tier is Stage.TIER2:
                raise ValueError("malformed structured output")
            return await super().judge(tier=tier, window=window, category=category)

    repo = RecordingRepo()
    monkeypatch.setattr(appmod, "_build_classifier", lambda s: Tier2Exploding())
    client, dispatcher = _app(monkeypatch, repo)

    r = client.post("/classify", json=_body("I'm planning to hurt Jake and I will get him"))
    assert r.status_code == 200
    assert r.json()["status"] == "PENDING"
    assert repo.saves == [("TIER1", "PENDING")]  # lock persisted; no TIER2 row
    assert dispatcher.calls == []  # §1: never notify without verification


def test_inline_tier2_still_confirms_in_response(monkeypatch):
    repo = RecordingRepo()
    client, dispatcher = _app(monkeypatch, repo)

    r = client.post(
        "/classify", json=_body("I'm planning to hurt Jake and I will get him", inline_tier2=True)
    )
    assert r.status_code == 200
    assert r.json()["status"] == "CONFIRMED"
    assert repo.saves == [("TIER2", "CONFIRMED")]
    assert dispatcher.calls == [("LOCK_AND_NOTIFY", "CONFIRMED")]


# --- /verdict-status over a real (sqlite) repository ------------------------- #
def test_verdict_status_endpoint_reports_latest_stage_and_scopes(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return VerdictRepository(async_sessionmaker(engine, expire_on_commit=False))

    repo = asyncio.run(setup())
    dispatcher = RecordingDispatcher()
    monkeypatch.setattr(appmod, "_build_persistence", lambda s: (repo, None, None))
    monkeypatch.setattr(appmod, "_build_dispatcher", lambda s, p: dispatcher)
    client = TestClient(
        appmod.create_app(
            Settings(
                _env_file=None,
                use_fake_classifier=True,
                use_langgraph_pipeline=False,
                require_auth=False,  # auth resolves to the local-dev account
            )
        )
    )

    # Async classify: TIER1 saved by the route, TIER2 by the background task.
    r = client.post("/classify", json=_body("I'm planning to hurt Jake and I will get him"))
    verdict_id = r.json()["verdict_id"]

    s = client.get(f"/verdict-status/{verdict_id}")
    assert s.status_code == 200
    assert s.json() == {
        "verdict_id": verdict_id,
        "stage": "TIER2",
        "status": "CONFIRMED",
        "recommended_action": "LOCK_AND_NOTIFY",
    }

    # Unknown id → 404 (indistinguishable from another account's verdict).
    assert client.get("/verdict-status/11111111-1111-4111-8111-111111111111").status_code == 404


def test_verdict_status_503_without_store(monkeypatch):
    repo = None
    dispatcher = RecordingDispatcher()
    monkeypatch.setattr(appmod, "_build_persistence", lambda s: (repo, None, None))
    monkeypatch.setattr(appmod, "_build_dispatcher", lambda s, p: dispatcher)
    client = TestClient(
        appmod.create_app(
            Settings(
                _env_file=None,
                use_fake_classifier=True,
                use_langgraph_pipeline=False,
                require_auth=False,
            )
        )
    )
    assert client.get("/verdict-status/x").status_code == 503
