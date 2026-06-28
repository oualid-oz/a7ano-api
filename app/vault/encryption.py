import base64
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

_DEV_KEY = "dev-key-change-in-production!!!"


def _get_key(master_key: str | None) -> bytes:
    """Derive a 32-byte key from the master key string.

    If master_key is None/empty, a fixed dev key is used and a warning is logged.
    Uses the first 32 bytes of the UTF-8 encoded key, padded with zeros if shorter.
    """
    if not master_key:
        logger.warning(
            "vault_master_key is not set — using insecure dev key. "
            "Set VAULT_MASTER_KEY in production."
        )
    raw = (master_key or _DEV_KEY).encode()
    return raw[:32].ljust(32, b"\x00")


def encrypt_field(plaintext: str, master_key: str | None = None) -> str:
    """Encrypt a string field. Returns base64(nonce + ciphertext)."""
    key = _get_key(master_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_field(encrypted: str, master_key: str | None = None) -> str:
    """Decrypt a field encrypted by encrypt_field."""
    key = _get_key(master_key)
    aesgcm = AESGCM(key)
    data = base64.b64decode(encrypted)
    nonce, ct = data[:12], data[12:]
    return aesgcm.decrypt(nonce, ct, None).decode()
