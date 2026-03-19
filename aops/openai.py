"""OpenAI SDK proxy that auto-logs LLM output to AgentOps.

Input is captured at ``pull()`` time via template variables.
This proxy only records the LLM output for the active chain call.

Supports sync ``openai.OpenAI`` only. ``AsyncOpenAI`` is not supported.
"""
from typing import Any

from aops._run import _active_chain, get_current_run


class _CompletionsProxy:
    def __init__(self, completions: Any) -> None:
        self._completions = completions

    def create(self, **kwargs: Any) -> Any:
        response = self._completions.create(**kwargs)

        chain_name = _active_chain.get()
        ctx = get_current_run()
        if chain_name and ctx is not None:
            try:
                output = response.choices[0].message.content
            except (IndexError, AttributeError):
                output = None
            ctx.update_output(chain_name, output)
            try:
                model_name = response.model or None
            except AttributeError:
                model_name = None
            ctx.update_model_name(chain_name, model_name)
            try:
                usage = response.usage
                if usage is not None:
                    ctx.update_tokens(
                        chain_name,
                        getattr(usage, 'prompt_tokens', None),
                        getattr(usage, 'completion_tokens', None),
                        getattr(usage, 'total_tokens', None),
                    )
            except AttributeError:
                pass

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
    """Wrap a sync OpenAI client to auto-log LLM output to AgentOps.

    Template variable inputs are captured at ``pull()`` time.
    This wrapper only records the LLM output after each completion call.

    Supports sync ``openai.OpenAI`` only. ``AsyncOpenAI`` is not supported —
    use ``AopsCallbackHandler`` with LangChain for async workflows instead.

    Args:
        client: A sync ``openai.OpenAI`` instance.

    Returns:
        A proxy client with the same interface, intercepting
        ``chat.completions.create()`` to capture output.

    Raises:
        TypeError: If ``client`` is an ``openai.AsyncOpenAI`` instance.

    Example::

        import openai
        from aops import wrap

        client = wrap(openai.OpenAI())

        with aops.run():
            prompt = aops.pull("classify", inquiry=user_input)
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
