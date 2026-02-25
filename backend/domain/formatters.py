"""Backward-compatibility shim — re-exports domain.core.formatters.

Consumers using ``from domain.formatters import X`` continue to work unchanged.
"""

from domain.core.formatters import build_moat_details, build_signal_status  # noqa: F401
