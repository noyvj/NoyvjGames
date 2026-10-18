"""Password hashing (salted PBKDF2-HMAC-SHA256, standard library only). Layer 1."""

import hashlib
import logging
import os
import secrets


logger = logging.getLogger(__name__)


PBKDF2_ITERATIONS = 600_000  # OWASP's 2023 minimum recommendation for PBKDF2-HMAC-SHA256
PBKDF2_ALGORITHM = "sha256"
PASSWORD_SALT_BYTES = 16


def _hash_password(password: str) -> str:
    salt = os.urandom(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(PBKDF2_ALGORITHM, password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        # A malformed stored_hash (bad migration, hand-edited row) is a
        # server-side data problem, not a user typing the wrong password —
        # worth its own log line so the two failure modes don't get
        # conflated when someone's login reports keep failing.
        logger.warning("_verify_password: stored_hash is malformed, treating as a failed login", exc_info=True)
        return False
    actual = hashlib.pbkdf2_hmac(PBKDF2_ALGORITHM, password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return secrets.compare_digest(actual, expected)
