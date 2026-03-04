"""LangChain callback handler that logs LLM input/output to AgentOps."""
from typing import Any

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.messages import BaseMessage
    from langchain_core.outputs import LLMResult
except ImportError:
    raise ImportError(
        "aops[langchain] extra required: pip install 'aops[langchain]'"
    )

from aops._run import _active_chain, get_current_run


def _messages_to_str(messages: list[BaseMessage]) -> str:
    parts = []
    for msg in messages:
        role = getattr(msg, "type", "message")
        parts.append(f"[{role}] {msg.content}")
    return "\n".join(parts)


class AopsCallbackHandler(BaseCallbackHandler):
    """LangChain callback that logs LLM input/output to AgentOps.

    Usage::

        from aops.langchain import AopsCallbackHandler

        handler = AopsCallbackHandler()
        llm = ChatOpenAI(callbacks=[handler])

        with aops.run():
            prompt = aops.pull("my-chain")
            result = llm.invoke([HumanMessage(content="Hello")])
    """

    def __init__(self) -> None:
        super().__init__()
        self._pending_input: str | None = None

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        chain_name = _active_chain.get()
        if chain_name is None:
            return
        self._pending_input = prompts[0] if prompts else None

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        chain_name = _active_chain.get()
        if chain_name is None:
            return
        flat = messages[0] if messages else []
        self._pending_input = _messages_to_str(flat)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        chain_name = _active_chain.get()
        if chain_name is None:
            return
        ctx = get_current_run()
        if ctx is None:
            return

        try:
            output = response.generations[0][0].text
        except (IndexError, AttributeError):
            output = None

        ctx.update_last_io(chain_name, self._pending_input, output)
        self._pending_input = None
