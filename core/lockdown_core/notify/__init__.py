"""Notification delivery (design doc §6).

One ``Notifier`` interface; the skeleton ships a logging stub. Resend (email)
and Twilio (SMS) implement the same protocol later with no call-site changes.
Notifications only ever render a *confirmed* verdict (principle §1: verified
before alert) and describe an *observation*, never a conclusion.
"""

from lockdown_core.notify.base import NotificationResult, Notifier, render_notification
from lockdown_core.notify.stub import LoggingNotifier

__all__ = ["NotificationResult", "Notifier", "render_notification", "LoggingNotifier"]
