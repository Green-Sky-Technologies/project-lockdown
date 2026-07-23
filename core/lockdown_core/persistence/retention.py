"""Retention purge hook (design doc §8 / §11).

Engineering ships the mechanism; **policy (counsel) sets the values.** Verdict
records carry a nullable ``retention_expires_at`` — this deletes rows whose time
has passed. It does NOT encode a retention policy (nothing here decides how long
to keep data); a deployment schedules it (cron) once the non-profit + counsel
have set retention on write.

Run manually / from a scheduler:
    python -m lockdown_core.persistence.retention
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import delete

from lockdown_core.persistence.engine import make_engine, make_sessionmaker
from lockdown_core.persistence.models import VerdictRecord
from lockdown_core.settings import get_settings

logger = logging.getLogger("lockdown.retention")


async def purge_expired() -> int:
    """Delete verdict records whose retention_expires_at is in the past. Returns
    the number deleted. No-op when the column is null (no policy set)."""
    settings = get_settings()
    if not settings.database_url:
        logger.warning("retention purge skipped: DATABASE_URL not set")
        return 0

    engine = make_engine(settings.database_url)
    sessionmaker = make_sessionmaker(engine)
    now = datetime.now(timezone.utc)
    async with sessionmaker() as session:
        result = await session.execute(
            delete(VerdictRecord).where(
                VerdictRecord.retention_expires_at.is_not(None),
                VerdictRecord.retention_expires_at < now,
            )
        )
        await session.commit()
    await engine.dispose()
    count = result.rowcount or 0
    logger.info("retention purge removed %d expired verdict records", count)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(purge_expired())
