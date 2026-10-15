"""Versioned scrypt hashes; plaintext passwords never enter durable storage."""

import hashlib
import hmac
import secrets
from threading import BoundedSemaphore


_HASH_SLOTS = BoundedSemaphore(2)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"scrypt$131072$8$1${salt}${_derive(password, salt)}"


def verify_password(password: str, encoded: str) -> bool:
    algorithm, n, r, p, salt, digest = encoded.split("$")
    if (algorithm, n, r, p) != ("scrypt", "131072", "8", "1"):
        raise ValueError("Unsupported password hash parameters.")
    return hmac.compare_digest(_derive(password, salt), digest)


def _derive(password: str, salt: str) -> str:
    with _HASH_SLOTS:
        return hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt),
            n=131072,
            r=8,
            p=1,
            maxmem=256 * 1024 * 1024,
            dklen=32,
        ).hex()
