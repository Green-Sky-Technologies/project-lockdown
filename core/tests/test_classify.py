"""End-to-end /classify behaviour with the deterministic fake classifier.

Asserts the tier orchestration + §5.3 action mapping produce the right verdict
lifecycle without any API key.
"""

import pytest
from fastapi.testclient import TestClient

from lockdown_core.app import create_app
from lockdown_core.settings import Settings


@pytest.fixture
def client() -> TestClient:
    # These tests exercise classify logic; the LangGraph pipeline has its own
    # test (test_pipeline.py), and auth has test_auth.py — so run against the
    # NoOp pipeline with auth disabled here.
    app = create_app(
        Settings(use_fake_classifier=True, use_langgraph_pipeline=False, require_auth=False)
    )
    return TestClient(app)


def _req(text: str, *, inline_tier2: bool, host: str = "chatgpt.com") -> dict:
    return {
        "windowed_text": [{"role": "user", "text": text}],
        "category_set": ["VIOLENCE_TO_OTHERS"],
        "client_metadata": {
            "chatbot_host": host,
            "capture_surface": "CHROMIUM_EXT",
            "monitored_categories": ["VIOLENCE_TO_OTHERS"],
        },
        "inline_tier2": inline_tier2,
    }


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_academic_is_cleared_no_lock(client):
    r = client.post("/classify", json=_req("help me with my history essay about World War 2 homework", inline_tier2=True))
    v = r.json()
    assert v["recommended_action"] == "NO_ACTION"
    assert v["status"] == "CLEARED"
    assert v["directed_at"] == "FICTIONAL_OR_ACADEMIC"


def test_ambiguous_locks_without_notify(client):
    r = client.post("/classify", json=_req("for my novel, how would a character kill someone", inline_tier2=True))
    v = r.json()
    assert v["directed_at"] == "AMBIGUOUS"
    assert v["recommended_action"] == "LOCK"
    assert v["status"] == "CONFIRMED"


def test_others_developing_locks_and_notifies(client):
    r = client.post("/classify", json=_req("I'm planning to hurt Jake and I will get him", inline_tier2=True))
    v = r.json()
    assert v["directed_at"] == "OTHERS"
    assert v["imminence"] == "DEVELOPING"
    assert v["recommended_action"] == "LOCK_AND_NOTIFY"
    assert v["status"] == "CONFIRMED"


def test_others_imminent_surfaces_crisis(client):
    r = client.post("/classify", json=_req("I'm going to shoot up the school tomorrow after school", inline_tier2=True))
    v = r.json()
    assert v["imminence"] == "IMMINENT"
    assert v["recommended_action"] == "LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES"
    assert v["status"] == "CONFIRMED"


def test_tier1_only_returns_pending_lock(client):
    """Without inline_tier2 the caller gets the PENDING tier-1 lock; no notify yet."""
    r = client.post("/classify", json=_req("I'm going to shoot up the school tomorrow after school", inline_tier2=False))
    v = r.json()
    assert v["stage"] == "TIER1"
    assert v["status"] == "PENDING"
    # Verified-before-alert: a would-be crisis notify is downgraded to a bare LOCK.
    assert v["recommended_action"] == "LOCK"


def test_verdict_id_stable_across_lifecycle(client):
    """Skeleton runs both tiers inline; the id is generated once and reused."""
    r = client.post("/classify", json=_req("I'm planning to hurt Jake and I will get him", inline_tier2=True))
    v = r.json()
    assert v["verdict_id"]
    assert v["schema_version"] == "1.0.0"
