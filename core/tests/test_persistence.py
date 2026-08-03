"""Persistence round-trip via async SQLite (dialect-agnostic models).

Validates the Verdict→VerdictRecord mapping, account resolution, the
(verdict_id, stage) upsert, and the should_persist rule — without needing Neon.
"""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from lockdown_core.contract.verdict import (
    CaptureSurface,
    Category,
    Context,
    DirectedAt,
    EvidenceSpan,
    Imminence,
    RecommendedAction,
    Severity,
    Stage,
    Status,
    Verdict,
)
from lockdown_core.persistence.models import Account, Base, VerdictRecord
from lockdown_core.persistence.repository import VerdictRepository, should_persist


def _verdict(**over) -> Verdict:
    base = dict(
        verdict_id="11111111-1111-4111-8111-111111111111",
        created_at="2026-07-01T12:00:00+00:00",
        stage=Stage.TIER2,
        status=Status.CONFIRMED,
        category=Category.VIOLENCE_TO_OTHERS,
        directed_at=DirectedAt.OTHERS,
        severity=Severity.HIGH,
        confidence=0.9,
        imminence=Imminence.DEVELOPING,
        recommended_action=RecommendedAction.LOCK_AND_NOTIFY,
        rationale="Targeting a named peer.",
        evidence_spans=[EvidenceSpan(start=0, end=10, turn_index=0)],
        context=Context(
            window_turn_count=3,
            chatbot_host="chatgpt.com",
            capture_surface=CaptureSurface.CHROMIUM_EXT,
            monitored_categories=[Category.VIOLENCE_TO_OTHERS],
        ),
    )
    base.update(over)
    return Verdict(**base)


async def _repo() -> tuple[VerdictRepository, async_sessionmaker]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    return VerdictRepository(sm), sm


def test_should_persist_skips_no_action():
    assert should_persist(_verdict(recommended_action=RecommendedAction.LOCK_AND_NOTIFY))
    assert not should_persist(_verdict(recommended_action=RecommendedAction.NO_ACTION))


def test_save_creates_account_and_record():
    async def run():
        repo, sm = await _repo()
        await repo.save(_verdict(), clerk_user_id="user_abc", clerk_org_id=None)
        async with sm() as s:
            from sqlalchemy import select

            accounts = (await s.execute(select(Account))).scalars().all()
            records = (await s.execute(select(VerdictRecord))).scalars().all()
        assert len(accounts) == 1 and accounts[0].clerk_user_id == "user_abc"
        assert accounts[0].tier == "family"
        assert len(records) == 1
        r = records[0]
        assert r.recommended_action == "LOCK_AND_NOTIFY"
        assert r.chatbot_host == "chatgpt.com"
        assert r.evidence_spans == [{"start": 0, "end": 10, "turn_index": 0}]
        assert r.raw_text_ref is None and r.retain_as_training is False

    asyncio.run(run())


def test_org_user_gets_school_tier():
    async def run():
        repo, sm = await _repo()
        await repo.save(_verdict(), clerk_user_id="user_x", clerk_org_id="org_school")
        async with sm() as s:
            from sqlalchemy import select

            acct = (await s.execute(select(Account))).scalar_one()
        assert acct.tier == "school" and acct.clerk_org_id == "org_school"

    asyncio.run(run())


def test_upsert_same_verdict_stage_updates_in_place():
    async def run():
        repo, sm = await _repo()
        await repo.save(_verdict(status=Status.PENDING), clerk_user_id="u", clerk_org_id=None)
        await repo.save(_verdict(status=Status.CONFIRMED), clerk_user_id="u", clerk_org_id=None)
        async with sm() as s:
            from sqlalchemy import select

            records = (await s.execute(select(VerdictRecord))).scalars().all()
        assert len(records) == 1  # same (verdict_id, stage) → updated, not duplicated
        assert records[0].status == "CONFIRMED"

    asyncio.run(run())


def test_different_stages_coexist():
    async def run():
        repo, sm = await _repo()
        await repo.save(_verdict(stage=Stage.TIER1, status=Status.PENDING), clerk_user_id="u")
        await repo.save(_verdict(stage=Stage.TIER2, status=Status.CONFIRMED), clerk_user_id="u")
        async with sm() as s:
            from sqlalchemy import select

            records = (await s.execute(select(VerdictRecord))).scalars().all()
        assert {r.stage for r in records} == {"TIER1", "TIER2"}  # audit trail preserved

    asyncio.run(run())


# --- app-level: /classify schedules persistence for lock/log, skips NO_ACTION --- #
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


def test_app_persists_locking_verdict_and_skips_no_action(monkeypatch):
    import lockdown_core.app as appmod
    from lockdown_core.settings import Settings

    calls: list[tuple[str, str]] = []

    class RecordingRepo:
        async def save(self, verdict, *, clerk_user_id, clerk_org_id=None):
            calls.append((verdict.recommended_action.value, clerk_user_id))

    monkeypatch.setattr(appmod, "_build_persistence", lambda s: (RecordingRepo(), None))
    client = TestClient(
        appmod.create_app(
            Settings(
                _env_file=None,  # hermetic: ignore the developer's core/.env
                use_fake_classifier=True,
                use_langgraph_pipeline=False,
                require_auth=False,
                persist_verdicts=True,
            )
        )
    )

    # Threat toward a named person → LOCK_AND_NOTIFY → persisted, attributed to local-dev.
    r = client.post("/classify", json=_classify_body("I'm planning to hurt Jake and I will get him"))
    assert r.status_code == 200
    assert calls == [("LOCK_AND_NOTIFY", "local-dev")]

    # Benign academic → NO_ACTION → NOT persisted (proportionate capture §4).
    calls.clear()
    client.post("/classify", json=_classify_body("help with my history essay about World War 2"))
    assert calls == []
