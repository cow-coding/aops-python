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
import threading
import traceback as tb_module
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from aops._client import AopsClient

_logger = logging.getLogger(__name__)


@dataclass
class _ChainCall:
    chain_name: str
    called_at: datetime
    latency_ms: int | None = None
    input: str | None = None
    output: str | None = None
    model_name: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    status: str = "success"
    error_message: str | None = None


@dataclass
class RunContext:
    """Holds trace data for a single agent run."""

    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    agent_id: uuid.UUID | None = None
    chain_calls: list[_ChainCall] = field(default_factory=list)
    status: str = "success"
    error_type: str | None = None
    error_message: str | None = None
    error_traceback: str | None = None

    def record_call(
        self,
        chain_name: str,
        called_at: datetime,
        latency_ms: int | None = None,
        input: str | None = None,
    ) -> None:
        self.chain_calls.append(
            _ChainCall(chain_name=chain_name, called_at=called_at, latency_ms=latency_ms, input=input)
        )

    def update_output(self, chain_name: str, output: str | None) -> None:
        """Update output and latency on the most recent call for the given chain_name.

        latency_ms is computed as the elapsed time from ``called_at`` (set at
        ``pull()`` time) to now, measuring the full input→output duration
        including the LLM call.
        """
        now = datetime.now(timezone.utc)
        for call in reversed(self.chain_calls):
            if call.chain_name == chain_name:
                call.output = output
                call.latency_ms = int((now - call.called_at).total_seconds() * 1000)
                return

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

    def update_model_name(self, chain_name: str, model_name: str | None) -> None:
        """Update model_name on the most recent call for the given chain_name."""
        for call in reversed(self.chain_calls):
            if call.chain_name == chain_name:
                call.model_name = model_name
                return

    def update_tokens(self, chain_name: str, prompt_tokens: int | None, completion_tokens: int | None, total_tokens: int | None) -> None:
        """Update token usage on the most recent call for the given chain_name."""
        for call in reversed(self.chain_calls):
            if call.chain_name == chain_name:
                call.prompt_tokens = prompt_tokens
                call.completion_tokens = completion_tokens
                call.total_tokens = total_tokens
                return

    def record_chain_error(self, chain_name: str, error_message: str) -> None:
        """Mark the most recent call for chain_name as errored."""
        for call in reversed(self.chain_calls):
            if call.chain_name == chain_name:
                call.status = "error"
                call.error_message = error_message
                return


_current_run: ContextVar[RunContext | None] = ContextVar("_current_run", default=None)
_active_chain: ContextVar[str | None] = ContextVar("_active_chain", default=None)


def _safe_post_run(client: "AopsClient", agent_id: uuid.UUID, ctx: RunContext) -> None:
    """Post run data with retry (max 3 attempts, exponential backoff).

    Retries handle transient network issues. Final failure is logged
    with enough detail for debugging without blocking the user's agent.
    """
    import time

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            client.post_run(agent_id, ctx)
            return  # success
        except Exception as exc:
            if attempt < max_retries:
                delay = 2 ** (attempt - 1)  # 1s, 2s
                _logger.debug("aops: post_run attempt %d failed, retrying in %ds: %s", attempt, delay, exc)
                time.sleep(delay)
            else:
                _logger.warning(
                    "aops: failed to post run after %d attempts (agent=%s, chains=%d, status=%s): %s",
                    max_retries, agent_id, len(ctx.chain_calls), ctx.status, exc,
                )


def _classify_error(e: Exception) -> str:
    name = type(e).__module__ + "." + type(e).__name__
    if any(x in name for x in ["openai", "anthropic", "APIError", "RateLimit"]):
        return "llm_api_error"
    if any(x in name for x in ["Timeout", "timeout"]):
        return "timeout"
    if any(x in name for x in ["ValidationError", "JSONDecodeError", "ValueError"]):
        return "validation_error"
    return "exception"


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
    ctx = RunContext()
    token = _current_run.set(ctx)
    chain_token = _active_chain.set(None)
    try:
        yield ctx
    except Exception as e:
        ctx.status = "error"
        ctx.error_type = _classify_error(e)
        ctx.error_message = str(e)
        ctx.error_traceback = tb_module.format_exc()
        raise
    finally:
        ctx.ended_at = datetime.now(timezone.utc)
        _active_chain.reset(chain_token)
        _current_run.reset(token)

        if ctx.agent_id is None or not ctx.chain_calls:
            return

        from aops._config import get_client
        c = client or get_client()
        threading.Thread(
            target=_safe_post_run,
            args=(c, ctx.agent_id, ctx),
            daemon=True,
        ).start()
