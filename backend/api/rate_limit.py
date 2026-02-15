"""
Rate limiter instance — shared across all routes to avoid circular imports.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance used by main.py and route decorators
limiter = Limiter(key_func=get_remote_address)
