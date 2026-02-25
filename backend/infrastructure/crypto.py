"""Backward-compatibility shim — re-exports infrastructure.external.crypto.

Consumers using ``from infrastructure.crypto import X`` continue to work unchanged.
"""

from infrastructure.external.crypto import (  # noqa: F401
    decrypt_token,
    encrypt_token,
    get_fernet_key,
    is_encrypted,
)
