"""OpenAI SDK proxy that auto-logs inputs/outputs to AgentOps.

Supports sync ``openai.OpenAI`` only. ``AsyncOpenAI`` is not supported.
"""
from typing import Any

from aops._run import _active_chain, get_current_run


def _messages_to_str(messages: list[dict]) -> str:
    parts = []
    for msg in messages:
        role = msg.get("role", "message")
        content = msg.get("content", "")
        parts.append(f"[{role}] {content}")
    return "\n".join(parts)


class _CompletionsProxy:
    def __init__(self, completions: Any) -> None:
        self._completions = completions

    def create(self, **kwargs: Any) -> Any:
        chain_name = _active_chain.get()
        ctx = get_current_run()

        messages = kwargs.get("messages", [])
        input_str = _messages_to_str(messages) if messages else None

        response = self._completions.create(**kwargs)

        if chain_name and ctx is not None:
            try:
                output = response.choices[0].message.content
            except (IndexError, AttributeError):
                output = None
            ctx.update_last_io(chain_name, input_str, output)

        return response


class _ChatProxy:
    def __init__(self, chat: Any) -> None:
        self._chat = chat
        self.completions = _CompletionsProxy(chat.completions)


class _AopsOpenAIProxy:
    """Wraps an OpenAI client to intercept chat.completions.create()."""

    def __init__(self, client: Any) -> None:
        self._client = client
        self.chat = _ChatProxy(client.chat)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


def wrap(client: Any) -> _AopsOpenAIProxy:
    """Wrap a sync OpenAI client to auto-log inputs/outputs to AgentOps.

    Supports sync ``openai.OpenAI`` only. ``AsyncOpenAI`` is not supported —
    use ``AopsCallbackHandler`` with LangChain for async workflows instead.

    Args:
        client: A sync ``openai.OpenAI`` instance.

    Returns:
        A proxy client with the same interface, intercepting
        ``chat.completions.create()`` to capture I/O.

    Raises:
        TypeError: If ``client`` is an ``openai.AsyncOpenAI`` instance.

    Example::

        import openai
        from aops import wrap

        client = wrap(openai.OpenAI())

        with aops.run():
            prompt = aops.pull("my-chain")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": prompt}, ...],
            )
    """
    try:
        import openai
        if isinstance(client, openai.AsyncOpenAI):
            raise TypeError(
                "aops.wrap() does not support AsyncOpenAI. "
                "Use openai.OpenAI() for sync or AopsCallbackHandler for LangChain async."
            )
    except ImportError:
        pass
    return _AopsOpenAIProxy(client)
