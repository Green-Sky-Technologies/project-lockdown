"""Auth behavior on /classify: escape hatch, anonymous rejection, rate limiting.

No Clerk network is needed: the escape-hatch path skips verification, and the
anonymous path 401s before any JWKS call (no session token present).
"""

import pytest
from fastapi.testclient import TestClient

from lockdown_core.app import create_app
from lockdown_core.settings import Settings


def _req() -> dict:
    return {
        "windowed_text": [{"role": "user", "text": "help with my history essay"}],
        "category_set": ["VIOLENCE_TO_OTHERS"],
        "client_metadata": {
            "chatbot_host": "chatgpt.com",
            "capture_surface": "CHROMIUM_EXT",
            "monitored_categories": ["VIOLENCE_TO_OTHERS"],
        },
        "inline_tier2": True,
    }


def _client(**overrides) -> TestClient:
    base = dict(
        _env_file=None,  # hermetic: ignore the developer's core/.env
        use_fake_classifier=True,
        use_langgraph_pipeline=False,
        persist_verdicts=False,
    )
    base.update(overrides)
    return TestClient(create_app(Settings(**base)))


def test_auth_off_allows_anonymous():
    """require_auth=false is the local-dev escape hatch."""
    r = _client(require_auth=False).post("/classify", json=_req())
    assert r.status_code == 200
    assert r.json()["schema_version"] == "1.0.0"


def test_auth_on_rejects_anonymous():
    """No bearer token / __session cookie → 401, before any Clerk call."""
    r = _client(require_auth=True, clerk_secret_key="sk_test_x").post("/classify", json=_req())
    assert r.status_code == 401
    assert r.json()["detail"] == "authentication required"


def test_auth_on_rejects_bogus_bearer_without_key():
    """A bearer token but no configured secret key → still 401 (misconfig-safe)."""
    r = _client(require_auth=True, clerk_secret_key=None).post(
        "/classify", json=_req(), headers={"Authorization": "Bearer not.a.real.jwt"}
    )
    assert r.status_code == 401


def test_healthz_is_open():
    r = _client(require_auth=True, clerk_secret_key="sk_test_x").get("/healthz")
    assert r.status_code == 200


def test_authorized_parties_parse_from_comma_string():
    """Regression: pydantic-settings must accept a comma-separated env string for
    the list[str] fields (NoDecode), not just a JSON array."""
    s = Settings(
        _env_file=None,
        clerk_authorized_parties="chrome-extension://abc,http://localhost:3000",
        cors_allow_origins="http://a.com, http://b.com",
    )
    assert s.clerk_authorized_parties == ["chrome-extension://abc", "http://localhost:3000"]
    assert s.cors_allow_origins == ["http://a.com", "http://b.com"]
    # JSON form still works
    assert Settings(_env_file=None, clerk_authorized_parties='["x","y"]').clerk_authorized_parties == ["x", "y"]


def test_rate_limit_returns_429():
    """A tiny bucket (burst=2, ~0 refill) trips 429 after the burst is spent."""
    client = _client(require_auth=False, rate_limit_per_minute=1, rate_limit_burst=2)
    codes = [client.post("/classify", json=_req()).status_code for _ in range(5)]
    assert codes[0] == 200 and codes[1] == 200
    assert 429 in codes[2:], f"expected a 429 after burst, got {codes}"
