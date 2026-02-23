import os
from dataclasses import dataclass

from aops._keys import InvalidApiKeyError, parse_key


@dataclass
class Config:
    base_url: str = "http://localhost:8000"
    api_prefix: str = "/api/v1"
    api_key: str | None = None
    cache_ttl: int = 300  # seconds; 0 = no cache

    @property
    def api_base(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.api_prefix}"


_config: Config | None = None


def init(
    api_key: str | None = None,
    *,
    base_url: str | None = None,
    api_prefix: str | None = None,
    cache_ttl: int | None = None,
) -> None:
    """Configure the AgentOps connection.

    Preferred usage — key only (host is parsed from the key automatically)::

        aops.init(api_key="aops_aHR0cDovL2xvY2FsaG9zdDo4MDAw_...")

    Manual URL override (e.g. for testing or reverse-proxy setups)::

        aops.init(api_key="aops_...", base_url="http://my-proxy:9000")

    Environment variables (when ``init()`` is not called explicitly):
        AGENTOPS_API_KEY    — the API key (host is parsed from it)
        AGENTOPS_BASE_URL   — overrides the host embedded in the key
        AGENTOPS_API_PREFIX — default: /api/v1
        AGENTOPS_CACHE_TTL  — default: 300 (seconds)
    """
    global _config

    resolved_key = api_key or os.getenv("AGENTOPS_API_KEY")
    explicit_url = base_url or os.getenv("AGENTOPS_BASE_URL")

    resolved_url = _resolve_base_url(resolved_key, explicit_url)

    _config = Config(
        base_url=resolved_url,
        api_prefix=api_prefix or os.getenv("AGENTOPS_API_PREFIX", "/api/v1"),
        api_key=resolved_key,
        cache_ttl=cache_ttl if cache_ttl is not None else int(os.getenv("AGENTOPS_CACHE_TTL", "300")),
    )


def get_config() -> Config:
    global _config
    if _config is None:
        resolved_key = os.getenv("AGENTOPS_API_KEY")
        explicit_url = os.getenv("AGENTOPS_BASE_URL")
        _config = Config(
            base_url=_resolve_base_url(resolved_key, explicit_url),
            api_prefix=os.getenv("AGENTOPS_API_PREFIX", "/api/v1"),
            api_key=resolved_key,
            cache_ttl=int(os.getenv("AGENTOPS_CACHE_TTL", "300")),
        )
    return _config


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _resolve_base_url(api_key: str | None, explicit_url: str | None) -> str:
    """Determine the base URL from the key and/or an explicit override."""
    if explicit_url:
        return explicit_url

    if api_key:
        try:
            host, _ = parse_key(api_key)
            return host
        except InvalidApiKeyError:
            pass  # fall through to default

    return "http://localhost:8000"
