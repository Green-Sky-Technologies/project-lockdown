"""Real tier-1/tier-2 classifier — a thin, stateless structured SDK call.

Design doc §4.3: "a minimal, legible critical path (text in → verdict out) is a
feature ... fewer layers between input and 'lock a kid out'." So this is a plain
``client.messages.parse(...)`` with a Pydantic ``output_format`` — no graph, no
agent loop. LangSmith tracing wraps the SDK client and is toggled entirely by the
``LANGSMITH_TRACING`` env var (see ``tracing.py``); there are no code branches for it.
"""

from __future__ import annotations

from lockdown_core.classify.prompts import render_window, system_prompt
from lockdown_core.classify.tracing import build_async_client
from lockdown_core.classify.types import ClassifierJudgment
from lockdown_core.contract.verdict import Category, Stage, Turn
from lockdown_core.settings import Settings


class AnthropicClassifier:
    """Implements the ``Classifier`` protocol against the Anthropic API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # wrap_anthropic() is applied inside build_async_client; tracing is a
        # no-op unless LANGSMITH_TRACING is set.
        self._client = build_async_client(api_key=settings.anthropic_api_key)

    def _model_for(self, tier: Stage) -> str:
        return self._settings.tier1_model if tier is Stage.TIER1 else self._settings.tier2_model

    async def judge(
        self,
        *,
        tier: Stage,
        window: list[Turn],
        category: Category,
    ) -> ClassifierJudgment:
        response = await self._client.messages.parse(
            model=self._model_for(tier),
            max_tokens=self._settings.max_tokens,
            system=system_prompt(tier=tier, category=category),
            messages=[{"role": "user", "content": render_window(window)}],
            output_format=ClassifierJudgment,
        )
        return response.parsed_output
