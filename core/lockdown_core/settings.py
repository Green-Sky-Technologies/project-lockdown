"""Runtime configuration (design doc §config).

All secrets and model ids come from the environment / a gitignored ``.env`` via
``pydantic-settings``. LangSmith reads its own ``LANGSMITH_*`` env vars directly
(see ``classify/tracing.py``); they are documented here but not required.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
