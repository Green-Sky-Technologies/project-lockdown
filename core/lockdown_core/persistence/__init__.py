"""Verdict persistence (Neon/Postgres).

Stores account-attributed, privacy-minimal verdict records — the data foundation
for the dashboard (design doc §6). The ``Verdict`` contract carries NO raw text
(offset spans + a short rationale only), so persisting it is privacy-preserving
by construction (§8). Account identity lives in a separate row, not in the
verdict contract.

IMPORTANT: imports ``sqlalchemy`` and is wired only at the composition root
(``app.py``), never from the classifier hot path (design doc §4.3) — an
architecture test enforces it.
"""

from lockdown_core.persistence.engine import make_engine, make_sessionmaker
from lockdown_core.persistence.models import Account, Base, VerdictRecord
from lockdown_core.persistence.repository import VerdictRepository

__all__ = [
    "Account",
    "Base",
    "VerdictRecord",
    "VerdictRepository",
    "make_engine",
    "make_sessionmaker",
]
