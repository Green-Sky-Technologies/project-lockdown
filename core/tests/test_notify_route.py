"""Route-level notification gating: /classify schedules a dispatch ONLY for a
CONFIRMED verdict whose action notifies (§1: verified before alert).

The dispatcher is replaced through the ``_build_dispatcher`` composition-root
seam (same pattern as ``_build_persistence`` in test_persistence.py)."""

from fastapi.testclient import TestClient

import lockdown_core.app as appmod
from lockdown_core.settings import Settings


class RecordingDispatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []  # (action, status, clerk_user_id)

    async def dispatch(self, verdict, *, clerk_user_id, clerk_org_id=None):
        self.calls.append(
            (verdict.recommended_action.value, verdict.status.value, clerk_user_id)
        )


def _client(monkeypatch) -> tuple[TestClient, RecordingDispatcher]:
    recorder = RecordingDispatcher()
    monkeypatch.setattr(appmod, "_build_dispatcher", lambda s, p: recorder)
    client = TestClient(
        appmod.create_app(
            Settings(
                _env_file=None,  # hermetic: ignore the developer's core/.env
                use_fake_classifier=True,
                use_langgraph_pipeline=False,
                require_auth=False,
            )
        )
    )
    return client, recorder


def _body(text: str, *, inline_tier2: bool = True) -> dict:
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


def test_confirmed_notify_verdict_dispatches(monkeypatch):
    client, recorder = _client(monkeypatch)
    r = client.post("/classify", json=_body("I'm planning to hurt Jake and I will get him"))
    assert r.status_code == 200
    assert recorder.calls == [("LOCK_AND_NOTIFY", "CONFIRMED", "local-dev")]


def test_benign_verdict_does_not_dispatch(monkeypatch):
    client, recorder = _client(monkeypatch)
    r = client.post(
        "/classify", json=_body("help me with my history essay about World War 2 homework")
    )
    assert r.status_code == 200
    assert recorder.calls == []


def test_pending_response_only_dispatches_after_background_verification(monkeypatch):
    """Without inline_tier2 the RESPONSE is PENDING (unverified); notification
    happens only via the background tier-2 pass, and only with the verified
    CONFIRMED verdict — never the PENDING one (§1: verified before alert)."""
    client, recorder = _client(monkeypatch)
    r = client.post(
        "/classify",
        json=_body("I'm going to shoot up the school tomorrow after school", inline_tier2=False),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "PENDING"
    # TestClient ran the background finalize before returning: the dispatched
    # verdict is the CONFIRMED tier-2 one, never the PENDING response.
    assert recorder.calls == [
        ("LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES", "CONFIRMED", "local-dev")
    ]
