"""Backward-compatibility shim — re-exports infrastructure.external.notification.

Consumers using ``from infrastructure.notification import X`` continue to work unchanged.
"""

from infrastructure.external.notification import (  # noqa: F401
    is_notification_enabled,
    send_telegram_message,
    send_telegram_message_dual,
)
