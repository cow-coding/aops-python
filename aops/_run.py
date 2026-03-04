"""Run context management for AgentOps tracing.

Usage::

    import aops
    aops.init(api_key="aops_...", agent="my-agent")

    with aops.run():
        prompt = aops.pull("my-chain")
        # ... use prompt ...
    # Chain calls are automatically recorded to the backend.
"""
import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generator

_logger = logging.getLogger(__name__)


@dataclass
class _ChainCall:
    chain_name: str
    called_at: datetime
    latency_ms: int | None = None
    input: str | None = None
    output: str | None = None


@dataclass
class RunContext:
    """Holds trace data for a single agent run."""

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    agent_id: uuid.UUID | None = None
    chain_calls: list[_ChainCall] = field(default_factory=list)

    def record_call(
        self,
        chain_name: str,
        called_at: datetime,
        latency_ms: int | None = None,
    ) -> None:
        self.chain_calls.append(
            _ChainCall(chain_name=chain_name, called_at=called_at, latency_ms=latency_ms)
        )

    def update_last_io(
        self,
        chain_name: str,
        input: str | None,
        output: str | None,
    ) -> None:
        """Update input/output on the most recent call for the given chain_name."""
        for call in reversed(self.chain_calls):
            if call.chain_name == chain_name:
                call.input = input
                call.output = output
                return


_current_run: ContextVar[RunContext | None] = ContextVar("_current_run", default=None)
_active_chain: ContextVar[str | None] = ContextVar("_active_chain", default=None)


def get_current_run() -> RunContext | None:
    """Return the active RunContext, or None if not inside a run() block."""
    return _current_run.get()


@contextmanager
def run(*, client=None) -> Generator[RunContext, None, None]:
    """Context manager that traces all pull() calls within the block.

    On exit, posts the recorded run data to the AgentOps backend.
    If the backend is unreachable the error is logged as a warning only —
    it does not propagate.

    Args:
        client: Optional pre-configured :class:`~aops._client.AopsClient`.
                When omitted the global configuration is used.

    Example::

        with aops.run():
            prompt = aops.pull("my-chain")
            response = llm.invoke(prompt)
    """
    from aops._client import AopsClient

    ctx = RunContext()
    token = _current_run.set(ctx)
    try:
        yield ctx
    finally:
        ctx.ended_at = datetime.now(timezone.utc)
        _current_run.reset(token)

        if ctx.agent_id is None or not ctx.chain_calls:
            return

        c = client or AopsClient()
        try:
            c.post_run(ctx.agent_id, ctx)
        except Exception as exc:
            _logger.warning("aops: failed to post run: %s", exc)
