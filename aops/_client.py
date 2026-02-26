import logging
import threading
import uuid

import httpx

from aops._cache import TTLCache
from aops._config import get_config

_logger = logging.getLogger(__name__)
from aops._exceptions import (
    AgentNotFoundError,
    AopsConnectionError,
    ChainNotFoundError,
    VersionNotFoundError,
)
from aops._keys import InvalidApiKeyError, parse_key
from aops._models import AgentModel, ChainModel, ChainVersionModel


class AopsClient:
    """HTTP client for the AgentOps backend API."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        api_prefix: str | None = None,
        cache_ttl: int | None = None,
        poll_interval: int | None = None,
    ) -> None:
        if api_key is not None or base_url is not None:
            # Explicit construction — resolve host from key, then allow override
            resolved_url = base_url or _host_from_key(api_key)
            self._api_base = f"{resolved_url.rstrip('/')}{api_prefix or '/api/v1'}"
            self._api_key = api_key
            ttl = cache_ttl if cache_ttl is not None else 300
            interval = poll_interval if poll_interval is not None else 60
        else:
            config = get_config()
            self._api_base = config.api_base
            self._api_key = config.api_key
            ttl = cache_ttl if cache_ttl is not None else config.cache_ttl
            interval = poll_interval if poll_interval is not None else config.poll_interval

        self._cache = TTLCache(ttl)
        self._poll_interval = interval
        self._poll_targets: dict[str, tuple[uuid.UUID, uuid.UUID]] = {}  # cache_key → (agent_id, chain_id)
        self._poll_lock = threading.Lock()
        self._http = httpx.Client()
        self._stop_event = threading.Event()

        if self._poll_interval > 0:
            t = threading.Thread(target=self._poll_loop, daemon=True, name="aops-poller")
            t.start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        if self._api_key:
            return {"X-API-Key": self._api_key}
        return {}

    def close(self) -> None:
        """Shut down the background poller and close the HTTP connection pool."""
        self._stop_event.set()
        self._http.close()

    def __enter__(self) -> "AopsClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _get(self, path: str) -> list | dict:
        url = f"{self._api_base}{path}"
        try:
            response = self._http.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as exc:
            raise AopsConnectionError(
                f"Cannot reach AgentOps at '{self._api_base}'. "
                "Check that the backend is running and your API key is correct."
            ) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                raise AopsConnectionError(
                    "AgentOps rejected the API key (401 Unauthorized). "
                    "Check that AGENTOPS_API_KEY is valid."
                ) from exc
            if status == 403:
                raise AopsConnectionError(
                    "Access denied (403 Forbidden). "
                    "This API key may not have access to the requested agent."
                ) from exc
            raise AopsConnectionError(
                f"AgentOps returned {status} for {url}"
            ) from exc

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        while not self._stop_event.wait(timeout=self._poll_interval):
            self._refresh_chains()

    def _refresh_chains(self) -> None:
        with self._poll_lock:
            targets = dict(self._poll_targets)

        for cache_key, (agent_id, chain_id) in targets.items():
            try:
                data = self._get(f"/agents/{agent_id}/chains/{chain_id}")
                fresh = ChainModel(**data)
                cached: ChainModel | None = self._cache.get(cache_key)
                if cached is None or cached.updated_at != fresh.updated_at:
                    self._cache.set(cache_key, fresh)
                    if cached is not None:
                        _logger.info("aops: chain '%s' updated (v%s)", fresh.name, fresh.updated_at)
            except Exception as exc:
                _logger.debug("aops: poll failed for %s: %s", cache_key, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_agent_by_name(self, agent_name: str) -> AgentModel:
        cache_key = f"agent:{agent_name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        agents = [AgentModel(**a) for a in self._get("/agents/")]
        for agent in agents:
            if agent.name == agent_name:
                self._cache.set(cache_key, agent)
                return agent

        raise AgentNotFoundError(
            f"Agent '{agent_name}' not found. "
            f"Available agents: {[a.name for a in agents] or '(none)'}"
        )

    def get_chain_by_name(self, agent_id: uuid.UUID, chain_name: str) -> ChainModel:
        cache_key = f"chain:{agent_id}:{chain_name}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        chains = [ChainModel(**c) for c in self._get(f"/agents/{agent_id}/chains/")]
        for chain in chains:
            if chain.name == chain_name:
                self._cache.set(cache_key, chain)
                with self._poll_lock:
                    self._poll_targets[cache_key] = (agent_id, chain.id)
                return chain

        raise ChainNotFoundError(
            f"Chain '{chain_name}' not found. "
            f"Available chains: {[c.name for c in chains] or '(none)'}"
        )

    def post_run(self, agent_id: uuid.UUID, ctx: "RunContext") -> None:  # noqa: F821
        """POST a completed run to the backend for tracing.

        Args:
            agent_id: UUID of the agent this run belongs to.
            ctx:      Completed :class:`~aops._run.RunContext`.
        """
        payload = {
            "started_at": ctx.started_at.isoformat(),
            "ended_at": ctx.ended_at.isoformat() if ctx.ended_at else None,
            "chain_calls": [
                {
                    "chain_name": c.chain_name,
                    "called_at": c.called_at.isoformat(),
                    "latency_ms": c.latency_ms,
                }
                for c in ctx.chain_calls
            ],
        }
        url = f"{self._api_base}/agents/{agent_id}/runs"
        try:
            response = self._http.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise AopsConnectionError(
                f"Cannot reach AgentOps at '{self._api_base}'."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise AopsConnectionError(
                f"AgentOps returned {exc.response.status_code} when posting run."
            ) from exc

    def get_chain_version(
        self, agent_id: uuid.UUID, chain_id: uuid.UUID, version_number: int
    ) -> ChainVersionModel:
        cache_key = f"version:{chain_id}:{version_number}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        versions = [
            ChainVersionModel(**v)
            for v in self._get(f"/agents/{agent_id}/chains/{chain_id}/versions/")
        ]
        for version in versions:
            if version.version_number == version_number:
                self._cache.set(cache_key, version)
                return version

        available = sorted(v.version_number for v in versions)
        raise VersionNotFoundError(
            f"Version {version_number} not found. Available versions: {available or '(none)'}"
        )


def _host_from_key(api_key: str | None) -> str:
    if api_key is None:
        return "http://localhost:8000"
    try:
        host, _ = parse_key(api_key)
        return host
    except InvalidApiKeyError:
        return "http://localhost:8000"
