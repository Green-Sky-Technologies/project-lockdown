"""LangSmith tracing for the hot path (design doc §7).

LangSmith traces raw SDK calls via ``wrap_anthropic``, so we keep it even though
the hot path is not a LangChain graph. Tracing is controlled ENTIRELY by
environment variables read by the langsmith SDK itself (``LANGSMITH_TRACING``,
``LANGSMITH_API_KEY``, ``LANGSMITH_PROJECT``) — wrapping the client is a no-op when
tracing is disabled, so there are zero code branches and a no-third-party
deployment simply leaves the vars unset.

This module imports ``anthropic`` and ``langsmith`` but NEVER ``langgraph`` — an
architecture test asserts langgraph stays off this path.
"""

from __future__ import annotations

from anthropic import AsyncAnthropic
from langsmith.wrappers import wrap_anthropic


def build_async_client(*, api_key: str | None) -> AsyncAnthropic:
    """An AsyncAnthropic client wrapped for LangSmith tracing."""
    client = AsyncAnthropic(api_key=api_key) if api_key else AsyncAnthropic()
    return wrap_anthropic(client)
