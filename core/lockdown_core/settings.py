"""Runtime configuration (design doc §config).

All secrets and model ids come from the environment / a gitignored ``.env`` via
``pydantic-settings``. LangSmith reads its own ``LANGSMITH_*`` env vars directly
(see ``classify/tracing.py``); they are documented here but not required.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _as_str_list(v: object) -> object:
    """Accept a JSON list, a comma-separated string, or an actual list for list[str]
    settings. A bare comma-string is a common env footgun (e.g. Clerk's
    authorized_parties, which MUST be a real list) — normalize it here."""
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if s.startswith("["):
            return v  # let pydantic parse the JSON list
        return [p.strip() for p in s.split(",") if p.strip()]
    return v


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LOCKDOWN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Anthropic --------------------------------------------------------- #
    # Read the standard ANTHROPIC_API_KEY (no prefix) so the SDK and our config
    # agree on one variable.
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Tier-1 = cheap/recall (Haiku); tier-2 = precise/verifying (Opus).
    tier1_model: str = "claude-haiku-4-5"
    tier2_model: str = "claude-opus-4-8"

    # Structured outputs via client.messages.parse() is GA on these models — no
    # beta header required.
    max_tokens: int = 2048

    # --- Action thresholds (feed contract.actions.Thresholds) -------------- #
    high_confidence: float = 0.7
    log_confidence: float = 0.3

    # --- Capture / safety limits ------------------------------------------ #
    max_window_turns: int = 40  # defensive cap on inbound window size

    # If true and no ANTHROPIC_API_KEY is set, the app wires a deterministic
    # heuristic classifier instead of the real SDK (local dev / CI without keys).
    use_fake_classifier: bool = False

    # Wire the LangGraph async pipeline (design doc §7). Off in unit tests that
    # only exercise classify logic; on by default at the composition root.
    use_langgraph_pipeline: bool = True

    # --- Auth (Clerk) ------------------------------------------------------ #
    # Verified statelessly via JWKS by clerk-backend-api (no key stored client-side).
    clerk_secret_key: str | None = Field(default=None, alias="CLERK_SECRET_KEY")
    # The `azp` claim must match one of these: the extension origin + dashboard
    # origin, e.g. ["chrome-extension://<id>", "https://dash.example.com"].
    clerk_authorized_parties: list[str] = Field(default_factory=list)
    # ESCAPE HATCH: false lets the core run unauthenticated for LOCAL DEV only.
    # Production MUST set this true so every stored verdict is attributable (§8).
    require_auth: bool = True

    # --- Persistence (Neon) — wired in A2 ---------------------------------- #
    database_url: str | None = Field(default=None, alias="DATABASE_URL")  # pooled -pooler string
    persist_verdicts: bool = True

    # --- Per-account rate limiting (in-memory MVP) ------------------------- #
    rate_limit_per_minute: int = 30
    rate_limit_burst: int = 10

    # --- CORS -------------------------------------------------------------- #
    # Default "*" for local dev; in production set the extension + dashboard
    # origins explicitly. (We use Bearer tokens, not cookies, so credentials off.)
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("clerk_authorized_parties", "cors_allow_origins", mode="before")
    @classmethod
    def _split_lists(cls, v: object) -> object:
        return _as_str_list(v)


@lru_cache
def get_settings() -> Settings:
    return Settings()
