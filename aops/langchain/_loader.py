import functools
import inspect
from typing import Callable

from langchain_core.prompts import SystemMessagePromptTemplate

from aops._client import AopsClient


def _to_system_prompt(persona: str, content: str) -> SystemMessagePromptTemplate:
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
    persona_escaped = persona.replace("{", "{{").replace("}", "}}")
    system_text = f"# Persona\n{persona_escaped}\n\n# Content\n{content}"
    return SystemMessagePromptTemplate.from_template(system_text)


def pull(
    ref: str,
    *,
    version: int | None = None,
    client: AopsClient | None = None,
) -> SystemMessagePromptTemplate:
    """Fetch a chain from AgentOps and return it as a SystemMessagePromptTemplate.

    Args:
        ref:     ``"agent-name/chain-name"`` reference string.
        version: Specific version number to load.  ``None`` loads the current
                 (latest saved) chain content.
        client:  Optional pre-configured :class:`~aops._client.AopsClient`.
                 When omitted the global configuration is used.

    Returns:
        A :class:`langchain_core.prompts.SystemMessagePromptTemplate` combining
        the chain's ``persona`` and ``content`` into a single system message.

    Example::

        from aops.langchain import pull

        prompt = pull("customer-support/greeter")
        prompt_v2 = pull("customer-support/greeter", version=2)

        chain = prompt | ChatOpenAI() | StrOutputParser()
        chain.invoke({"topic": "billing"})
    """
    if "/" not in ref:
        raise ValueError(
            f"Invalid ref '{ref}'. Expected format: 'agent-name/chain-name'."
        )

    agent_name, chain_name = ref.split("/", 1)
    c = client or AopsClient()

    agent = c.get_agent_by_name(agent_name)
    chain = c.get_chain_by_name(agent.id, chain_name)

    if version is not None:
        v = c.get_chain_version(agent.id, chain.id, version)
        return _to_system_prompt(v.persona, v.content)

    return _to_system_prompt(chain.persona, chain.content)


def chain_prompt(
    agent_name: str,
    chain_name: str,
    *,
    version: int | None = None,
    client: AopsClient | None = None,
):
    """Decorator that injects a ``SystemMessagePromptTemplate`` from AgentOps.

    The prompt is fetched once on the first call and then served from the
    client-level cache on subsequent calls.

    **Function decorator** — the resolved prompt is passed as the first
    positional argument::

        @chain_prompt("my-agent", "summariser")
        def summarise(prompt: SystemMessagePromptTemplate, text: str) -> str:
            return (prompt | ChatOpenAI()).invoke({"text": text})

        result = summarise(text="Long article...")

    **Class decorator** — the resolved prompt is passed as the second
    positional argument to ``__init__`` (after ``self``)::

        @chain_prompt("my-agent", "summariser")
        class Summariser:
            def __init__(self, prompt: SystemMessagePromptTemplate) -> None:
                self.chain = prompt | ChatOpenAI()

            def run(self, text: str) -> str:
                return self.chain.invoke({"text": text})

        summariser = Summariser()
        result = summariser.run(text="Long article...")

    Args:
        agent_name: Name of the agent registered in AgentOps.
        chain_name: Name of the chain within that agent.
        version:    Version number to pin.  ``None`` = latest.
        client:     Optional custom :class:`~aops._client.AopsClient`.
    """

    def decorator(target: type | Callable) -> type | Callable:
        if inspect.isclass(target):
            return _wrap_class(target, agent_name, chain_name, version, client)
        return _wrap_function(target, agent_name, chain_name, version, client)

    return decorator


# ------------------------------------------------------------------
# Internal wrappers
# ------------------------------------------------------------------

def _wrap_function(
    func: Callable,
    agent_name: str,
    chain_name: str,
    version: int | None,
    client: AopsClient | None,
) -> Callable:
    ref = f"{agent_name}/{chain_name}"

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        prompt = pull(ref, version=version, client=client)
        return func(prompt, *args, **kwargs)

    return wrapper


def _wrap_class(
    cls: type,
    agent_name: str,
    chain_name: str,
    version: int | None,
    client: AopsClient | None,
) -> type:
    ref = f"{agent_name}/{chain_name}"
    original_init = cls.__init__

    @functools.wraps(original_init)
    def new_init(self, *args, **kwargs):
        prompt = pull(ref, version=version, client=client)
        original_init(self, prompt, *args, **kwargs)

    cls.__init__ = new_init
    return cls
