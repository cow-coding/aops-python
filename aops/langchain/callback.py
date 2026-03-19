"""LangChain callback handler that logs LLM output to AgentOps."""
from typing import Any

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
except ImportError:
    raise ImportError(
        "aops[langchain] extra required: pip install 'aops[langchain]'"
    )

from aops._run import _active_chain, get_current_run


class AopsCallbackHandler(BaseCallbackHandler):
    """LangChain callback that logs LLM output to AgentOps.

    Input is captured at ``pull()`` time via template variables.
    This handler only records the LLM output for the active chain call.

    Usage::

        from aops.langchain import AopsCallbackHandler

        handler = AopsCallbackHandler()
        llm = ChatOpenAI(callbacks=[handler])

        with aops.run():
            prompt = aops.pull("classify", inquiry=user_input)
            result = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=user_input)])
    """

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

        ctx.update_output(chain_name, output)

        model_name: str | None = None
        try:
            meta = response.generations[0][0].message.response_metadata  # type: ignore[union-attr]
            model_name = meta.get("model_name") or meta.get("model") or None
        except (IndexError, AttributeError, TypeError):
            pass
        if model_name is None and response.llm_output:
            model_name = (
                response.llm_output.get("model_name")
                or response.llm_output.get("model")
                or None
            )
        ctx.update_model_name(chain_name, model_name)
