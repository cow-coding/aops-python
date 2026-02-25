import functools
import inspect
from typing import Callable

from langchain_core.prompts import SystemMessagePromptTemplate

from aops._client import AopsClient
from aops._pull import _fetch_chain


def _to_system_prompt(persona: str | None, content: str) -> SystemMessagePromptTemplate:
    """Convert AgentOps chain fields into a SystemMessagePromptTemplate.

    Both ``persona`` and ``content`` are agent-authored system-level instructions,
    merged into a single SystemMessage:

        # Persona
        <persona text>

        # Content
        <content text — may contain {template_variables}>

    ``persona`` is treated as a fixed string (its braces are escaped).
    ``content`` may contain LangChain template variables in single braces,
    e.g. ``"Answer in {language}"``.
    To include a literal brace in content use double braces: ``{{`` or ``}}``.
    """
    if persona:
        persona_escaped = persona.replace("{", "{{").replace("}", "}}")
        system_text = f"# Persona\n{persona_escaped}\n\n# Content\n{content}"
    else:
        system_text = content
    return SystemMessagePromptTemplate.from_template(system_text)


def pull(
    chain_name: str,
    *,
    version: int | None = None,
    client: AopsClient | None = None,
) -> SystemMessagePromptTemplate:
    """Fetch a chain from AgentOps and return it as a SystemMessagePromptTemplate.

    The agent name is resolved in the following order:

    1. Explicit ``"agent-name/chain-name"`` ref passed as ``chain_name``
    2. Agent declared via ``aops.init(agent="my-agent")``
    3. ``AGENTOPS_AGENT`` environment variable

    Args:
        chain_name: Chain name (e.g. ``"my-chain"``) or a full ref
                    (``"agent-name/chain-name"``).
        version:    Specific version number to load. ``None`` loads the current
                    (latest saved) chain content.
        client:     Optional pre-configured :class:`~aops._client.AopsClient`.
                    When omitted the global configuration is used.

    Returns:
        A :class:`langchain_core.prompts.SystemMessagePromptTemplate` combining
        the chain's ``persona`` and ``content`` into a single system message.

    Example::

        import aops
        aops.init(api_key="aops_...", agent="customer-support")

        from aops.langchain import pull
        prompt = pull("greeter")
        prompt_v2 = pull("greeter", version=2)

        chain = prompt | ChatOpenAI() | StrOutputParser()
        chain.invoke({"topic": "billing"})
    """
    c = client or AopsClient()
    persona, content = _fetch_chain(chain_name, version, c)
    return _to_system_prompt(persona, content)


def chain_prompt(
    chain_name: str,
    *,
    version: int | None = None,
    client: AopsClient | None = None,
):
    """Decorator that injects a ``SystemMessagePromptTemplate`` from AgentOps.

    The agent name is resolved from ``aops.init(agent="my-agent")`` or the
    ``AGENTOPS_AGENT`` environment variable. A full ``"agent/chain"`` ref is
    also accepted as ``chain_name`` for explicit cross-agent access.

    The prompt is fetched once on the first call and then served from the
    client-level cache on subsequent calls.

    **Function decorator** — the resolved prompt is passed as the first
    positional argument::

        aops.init(api_key="aops_...", agent="my-agent")

        @chain_prompt("summariser")
        def summarise(prompt: SystemMessagePromptTemplate, text: str) -> str:
            return (prompt | ChatOpenAI()).invoke({"text": text})

        result = summarise(text="Long article...")

    **Class decorator** — the resolved prompt is passed as the second
    positional argument to ``__init__`` (after ``self``)::

        @chain_prompt("summariser")
        class Summariser:
            def __init__(self, prompt: SystemMessagePromptTemplate) -> None:
                self.chain = prompt | ChatOpenAI()

            def run(self, text: str) -> str:
                return self.chain.invoke({"text": text})

        summariser = Summariser()
        result = summariser.run(text="Long article...")

    Args:
        chain_name: Chain name or full ``"agent/chain"`` ref.
        version:    Version number to pin. ``None`` = latest.
        client:     Optional custom :class:`~aops._client.AopsClient`.
    """

    def decorator(target: type | Callable) -> type | Callable:
        if inspect.isclass(target):
            return _wrap_class(target, chain_name, version, client)
        return _wrap_function(target, chain_name, version, client)

    return decorator


# ------------------------------------------------------------------
# Internal wrappers
# ------------------------------------------------------------------

def _wrap_function(
    func: Callable,
    chain_name: str,
    version: int | None,
    client: AopsClient | None,
) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        prompt = pull(chain_name, version=version, client=client)
        return func(prompt, *args, **kwargs)

    return wrapper


def _wrap_class(
    cls: type,
    chain_name: str,
    version: int | None,
    client: AopsClient | None,
) -> type:
    original_init = cls.__init__

    @functools.wraps(original_init)
    def new_init(self, *args, **kwargs):
        prompt = pull(chain_name, version=version, client=client)
        original_init(self, prompt, *args, **kwargs)

    cls.__init__ = new_init
    return cls
