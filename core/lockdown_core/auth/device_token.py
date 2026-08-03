"""Device-token minting + hashing (pure — no DB, no network).

A device token is a long-lived personal-access-token the parent generates in the
dashboard and pastes into the extension. It carries no session/cookie dependency,
so it works from any Chrome profile for as long as the parent wants — the exact
opposite of the sync-host flow's short-lived browser session.

Format: ``pld_live_<43 url-safe base64 chars>`` (256 bits of entropy). Only the
SHA-256 hash is ever persisted; the plaintext is shown once and then unrecoverable.
The ``pld_`` prefix lets the core cheaply tell a device token from a Clerk JWT
(which starts with ``eyJ``) without a DB round-trip.
"""

from __future__ import annotations

import hashlib
import secrets

PREFIX = "pld_live_"


def generate() -> tuple[str, str]:
    """Return ``(plaintext, token_hash)``. Show the plaintext to the user once;
    store only the hash."""
    plaintext = PREFIX + secrets.token_urlsafe(32)
    return plaintext, hash_token(plaintext)


def hash_token(plaintext: str) -> str:
    """SHA-256 hex of the token. A raw hash (not a slow KDF) is appropriate here:
    the token is 256 bits of uniform randomness, so there is no low-entropy
    preimage to brute-force."""
    return hashlib.sha256(plaintext.strip().encode("utf-8")).hexdigest()


def looks_like_device_token(token: str) -> bool:
    """True if ``token`` (a bearer value, already stripped of the ``Bearer `` scheme)
    is one of ours — used to route between the device-token and Clerk paths."""
    return token.startswith(PREFIX)
