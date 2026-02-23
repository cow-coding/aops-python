"""API key utilities for aops.

Key format:
    aops_{base64url(host)}_{secret_token}

Example:
    host  = "http://localhost:8000"
    key   = "aops_aHR0cDovL2xvY2FsaG9zdDo4MDAw_xK9mP2abcXYZ..."

The host is base64url-encoded (no padding) inside the key, so the library
can resolve the AgentOps server without a separate base_url setting.
"""

import base64
import secrets

_PREFIX = "aops"
_SEP = "_"


class InvalidApiKeyError(ValueError):
    """Raised when an API key cannot be parsed."""


def generate_key(host: str) -> str:
    """Generate a new API key that embeds *host*.

    This helper is intended for the AgentOps backend when issuing keys.
    The returned key must be stored (hashed) and should be shown to the
    user only once.

    Args:
        host: Full base URL of the AgentOps server,
              e.g. ``"http://localhost:8000"``.

    Returns:
        A key string of the form ``"aops_{encoded_host}_{token}"``.
    """
    encoded_host = _encode_host(host)
    token = secrets.token_urlsafe(32)
    return f"{_PREFIX}{_SEP}{encoded_host}{_SEP}{token}"


def parse_key(api_key: str) -> tuple[str, str]:
    """Parse an API key and return ``(host, token)``.

    Args:
        api_key: A key produced by :func:`generate_key`.

    Returns:
        ``(host, token)`` tuple where *host* is the raw base URL string.

    Raises:
        :class:`InvalidApiKeyError` if the key format is invalid.
    """
    parts = api_key.split(_SEP, 2)
    if len(parts) != 3 or parts[0] != _PREFIX:
        raise InvalidApiKeyError(
            f"Invalid API key format. Expected 'aops_<host>_<token>', got: '{api_key[:12]}...'"
        )
    _, encoded_host, token = parts
    try:
        host = _decode_host(encoded_host)
    except Exception as exc:
        raise InvalidApiKeyError(
            f"Cannot decode host from API key: {exc}"
        ) from exc
    return host, token


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _encode_host(host: str) -> str:
    """base64url-encode *host* without padding."""
    return base64.urlsafe_b64encode(host.encode()).decode().rstrip("=")


def _decode_host(encoded: str) -> str:
    """Decode a base64url *encoded* host (handles missing padding)."""
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded).decode()
