"""Notifier protocol + the shared render of a verdict into notification copy.

The copy rules are load-bearing (design doc §6, §11):

* Describe an **observation for review**, never a conclusion about a person
  ("flagged for review because it may involve X" — never "your child is
  planning X").
* Resolve the child-privacy vs. adult-need tension by **imminence**: a *maybe*
  shows less; a high-confidence imminent flag shows more.
* For imminent/high-confidence, surface **crisis-line + contact-authorities**
  guidance rather than implying the tool handled it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from lockdown_core.contract.verdict import Imminence, RecommendedAction, Verdict


@dataclass
class NotificationResult:
    delivered: bool
    channel: str
    detail: str


CRISIS_GUIDANCE = (
    "If you believe there is an immediate risk of harm, contact local emergency "
    "services (911 in the US) or the 988 Suicide & Crisis Lifeline. This tool is "
    "not an emergency-response system and cannot guarantee timely delivery."
)


def render_notification(verdict: Verdict, *, include_crisis: bool | None = None) -> str:
    """Render adult-facing copy from a verdict. Imminence gates how much detail."""
    surface_crisis = (
        include_crisis
        if include_crisis is not None
        else verdict.recommended_action
        == RecommendedAction.LOCK_NOTIFY_AND_SURFACE_CRISIS_RESOURCES
    )

    lines = [
        "Project Lockdown — a monitored conversation was flagged for your review.",
        f"Category: {verdict.category.value.replace('_', ' ').title()}",
        "",
        "This is an observation flagged for review, not a conclusion about the "
        "person being monitored.",
    ]

    # More detail only as imminence rises.
    if verdict.imminence in (Imminence.DEVELOPING, Imminence.IMMINENT):
        lines += ["", f"Why it was flagged: {verdict.rationale}"]
    else:
        lines += ["", "The conversation may involve concerning content; details are "
                  "limited pending review to protect the child's privacy."]

    lines += ["", "What to do next: talk with the person being monitored; review the "
              "conversation together where appropriate."]

    if surface_crisis:
        lines += ["", CRISIS_GUIDANCE]

    return "\n".join(lines)


class Notifier(Protocol):
    async def send(self, verdict: Verdict, *, recipient: str) -> NotificationResult: ...
