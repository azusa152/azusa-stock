"""Backward-compatibility shim — re-exports domain.core.constants.

Consumers using ``from domain.constants import X`` continue to work unchanged.
"""

from domain.core.constants import *  # noqa: F401, F403
