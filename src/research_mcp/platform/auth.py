"""The daemon token: mint, compare, the cursor key and the shim's bearer header.

LLD-platform-v2 4.5 and LLD-security-v2 5.2. This module, ``http.py`` and ``mcp_client.py``
are the only places that call ``Secret.reveal`` (PLAT-FR-11). The UI one-time tokens that
LLD-security-v2 E6 also puts here arrive with the UI component.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from research_mcp.platform.secrets import Secret

DAEMON_TOKEN = "DAEMON_TOKEN"  # noqa: S105 - the Keychain item name, not a value
CURSOR_INFO = b"research-mcp cursor v1"
TOKEN_BYTES = 32
KEY_BYTES = 32


def mint_token() -> str:
    """32 random bytes as URL-safe base64 without padding: 43 characters (E45)."""
    return base64.urlsafe_b64encode(secrets.token_bytes(TOKEN_BYTES)).rstrip(b"=").decode()


# @spec SEC-11
def token_matches(presented: str, secret: Secret | None) -> bool:
    """Compare a presented bearer token with the daemon token in constant time.

    No daemon token (missing from the Keychain) or an empty presented token never matches.
    """
    if secret is None or not presented:
        return False
    return hmac.compare_digest(presented.encode(), secret.reveal().encode())


def bearer_header(secret: Secret) -> dict[str, str]:
    """The ``Authorization`` header the shim sends; the only way it reveals the token."""
    return {"Authorization": f"Bearer {secret.reveal()}"}


def cursor_key(secret: Secret) -> bytes:
    """HKDF-SHA256 (RFC 5869, no salt) over the daemon token, info ``research-mcp cursor v1``."""
    prk = hmac.new(b"\x00" * hashlib.sha256().digest_size, secret.reveal().encode(), "sha256")
    return hmac.new(prk.digest(), CURSOR_INFO + b"\x01", "sha256").digest()[:KEY_BYTES]
