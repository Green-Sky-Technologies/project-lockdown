"""Async engine/session factory for Neon (Postgres).

Accepts a plain Neon **pooled** connection string; normalizes it to the asyncpg
driver and applies the pooling-safe settings (``statement_cache_size=0`` avoids
``DuplicatePreparedStatementError`` through PgBouncer).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine


def _normalize(url: str) -> tuple[str, dict]:
    async_url = url
    for prefix in ("postgresql://", "postgres://"):
        if async_url.startswith(prefix):
            async_url = "postgresql+asyncpg://" + async_url[len(prefix) :]
            break
    # asyncpg doesn't take libpq query params (sslmode, channel_binding, ...).
    async_url = async_url.partition("?")[0]

    connect_args: dict = {"statement_cache_size": 0}  # PgBouncer-safe
    if not ("localhost" in async_url or "127.0.0.1" in async_url):
        connect_args["ssl"] = True  # Neon requires TLS
    return async_url, connect_args


def make_engine(database_url: str) -> AsyncEngine:
    async_url, connect_args = _normalize(database_url)
    return create_async_engine(async_url, connect_args=connect_args, pool_pre_ping=True)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)
