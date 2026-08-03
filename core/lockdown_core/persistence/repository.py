"""Verdict persistence repository.

``save`` resolves (or creates) the account for the authenticated caller and
writes/updates the verdict record, upserting on ``(verdict_id, stage)`` so the
tier-2 row updates cleanly as the lifecycle advances. Mapping pulls only the
contract render fields — never raw text (none exists in the Verdict).
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lockdown_core.contract.verdict import RecommendedAction, Verdict
from lockdown_core.persistence.models import Account, VerdictRecord

logger = logging.getLogger("lockdown.persistence")


async def get_or_create_account(
    session: AsyncSession, *, clerk_user_id: str, clerk_org_id: str | None
) -> Account:
    """Resolve the account for a Clerk user, creating it on first sight. Shared by
    verdict persistence and device-token minting so both attribute to one row."""
    existing = (
        await session.execute(select(Account).where(Account.clerk_user_id == clerk_user_id))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    account = Account(
        clerk_user_id=clerk_user_id,
        clerk_org_id=clerk_org_id,
        tier="school" if clerk_org_id else "family",
    )
    session.add(account)
    await session.flush()  # assign account.id
    return account


def _parse_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def _record_fields(verdict: Verdict) -> dict:
    ctx = verdict.context
    return {
        "verdict_id": verdict.verdict_id,
        "schema_version": verdict.schema_version,
        "created_at": _parse_dt(verdict.created_at),
        "category": verdict.category.value,
        "directed_at": verdict.directed_at.value,
        "severity": verdict.severity.value,
        "confidence": verdict.confidence,
        "imminence": verdict.imminence.value,
        "stage": verdict.stage.value,
        "status": verdict.status.value,
        "recommended_action": verdict.recommended_action.value,
        "rationale": verdict.rationale,
        "evidence_spans": [s.model_dump() for s in verdict.evidence_spans],
        "chatbot_host": ctx.chatbot_host,
        "capture_surface": ctx.capture_surface.value,
        "deidentified": verdict.privacy.deidentified,
        "retain_as_training": verdict.privacy.retain_as_training,
        "raw_text_ref": verdict.privacy.raw_text_ref,
    }


def should_persist(verdict: Verdict) -> bool:
    """Persist only lock/log verdicts — never NO_ACTION (proportionate capture §4)."""
    return verdict.recommended_action is not RecommendedAction.NO_ACTION


class VerdictRepository:
    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        self._sessionmaker = sessionmaker

    async def save(
        self, verdict: Verdict, *, clerk_user_id: str, clerk_org_id: str | None = None
    ) -> None:
        """Write/update the verdict record. Never raises — a store outage must not
        affect the lock decision (this runs off the response path)."""
        try:
            async with self._sessionmaker() as session:
                account = await get_or_create_account(
                    session, clerk_user_id=clerk_user_id, clerk_org_id=clerk_org_id
                )
                fields = _record_fields(verdict)
                existing = (
                    await session.execute(
                        select(VerdictRecord).where(
                            VerdictRecord.verdict_id == verdict.verdict_id,
                            VerdictRecord.stage == verdict.stage.value,
                        )
                    )
                ).scalar_one_or_none()

                if existing is not None:
                    for k, v in fields.items():
                        setattr(existing, k, v)
                    existing.clerk_org_id = clerk_org_id
                else:
                    session.add(
                        VerdictRecord(account_id=account.id, clerk_org_id=clerk_org_id, **fields)
                    )
                await session.commit()
        except Exception:  # noqa: BLE001 — persistence must never break classify
            logger.exception("failed to persist verdict %s", verdict.verdict_id)
