import os
from dataclasses import dataclass

from aops._keys import InvalidApiKeyError, parse_key


@dataclass
class Config:
    base_url: str = "http://localhost:8000"
    api_prefix: str = "/api/v1"
    api_key: str | None = None
    agent: str | None = None
    cache_ttl: int = 300  # seconds; 0 = no cache
    poll_interval: int = 60  # seconds; 0 = no polling

    @property
    def api_base(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.api_prefix}"


_config: Config | None = None


def init(
    api_key: str | None = None,
    *,
    agent: str | None = None,
    base_url: str | None = None,
    api_prefix: str | None = None,
    cache_ttl: int | None = None,
    poll_interval: int | None = None,
) -> None:
    """Configure the AgentOps connection.

    Preferred usage::

        aops.init(api_key="aops_...", agent="my-agent")

    After this, ``pull("chain-name")`` resolves to ``my-agent/chain-name``
    without requiring the agent name on every call.

    Manual URL override (e.g. for testing or reverse-proxy setups)::

        aops.init(api_key="aops_...", agent="my-agent", base_url="http://my-proxy:9000")

    Environment variables (when ``init()`` is not called explicitly):
        AGENTOPS_API_KEY       — the API key (host is parsed from it)
        AGENTOPS_AGENT         — default agent name
        AGENTOPS_BASE_URL      — overrides the host embedded in the key
        AGENTOPS_API_PREFIX    — default: /api/v1
        AGENTOPS_CACHE_TTL     — default: 300 (seconds)
        AGENTOPS_POLL_INTERVAL — default: 60 (seconds); 0 = disable polling
    """
    global _config

    resolved_key = api_key or os.getenv("AGENTOPS_API_KEY")
    explicit_url = base_url or os.getenv("AGENTOPS_BASE_URL")

    resolved_url = _resolve_base_url(resolved_key, explicit_url)

    _config = Config(
        base_url=resolved_url,
        api_prefix=api_prefix or os.getenv("AGENTOPS_API_PREFIX", "/api/v1"),
        api_key=resolved_key,
        agent=agent or os.getenv("AGENTOPS_AGENT"),
        cache_ttl=cache_ttl if cache_ttl is not None else int(os.getenv("AGENTOPS_CACHE_TTL", "300")),
        poll_interval=poll_interval if poll_interval is not None else int(os.getenv("AGENTOPS_POLL_INTERVAL", "60")),
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
            agent=os.getenv("AGENTOPS_AGENT"),
            cache_ttl=int(os.getenv("AGENTOPS_CACHE_TTL", "300")),
            poll_interval=int(os.getenv("AGENTOPS_POLL_INTERVAL", "60")),
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
