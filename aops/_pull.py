import json
import uuid
from datetime import datetime, timezone

from aops._client import AopsClient
from aops._config import get_config


def format_prompt(persona: str | None, content: str) -> str:
    """Merge persona and content into a raw prompt string.

    Args:
        persona: Agent persona text. May be empty or None.
        content: Chain content text.

    Returns:
        Combined prompt string. If persona is non-empty:
        ``f"{persona}\\n\\n{content}"``. Otherwise just ``content``.
    """
    if persona:
        return f"{persona}\n\n{content}"
    return content


def _fetch_chain(
    chain_name: str,
    version: int | None,
    client: AopsClient,
) -> tuple[uuid.UUID, str, str | None, str]:
    """Resolve ref, fetch from backend, and return (agent_id, resolved_chain_name, persona, content).

    Shared by both the raw ``pull()`` and ``aops.langchain.pull()``.
    """
    agent_name, resolved_chain = _resolve_ref(chain_name)

    agent = client.get_agent_by_name(agent_name)
    chain = client.get_chain_by_name(agent.id, resolved_chain)

    if version is not None:
        v = client.get_chain_version(agent.id, chain.id, version)
        return agent.id, resolved_chain, v.persona, v.content

    return agent.id, resolved_chain, chain.persona, chain.content


def pull(
    chain_name: str,
    *,
    version: int | None = None,
    client: AopsClient | None = None,
    **variables: str,
) -> str:
    """Fetch a chain from AgentOps and return it as a raw string.

    The agent name is resolved in the following order:

    1. Explicit ``"agent-name/chain-name"`` ref passed as ``chain_name``
    2. Agent declared via ``aops.init(agent="my-agent")``
    3. ``AGENTOPS_AGENT`` environment variable

    Args:
        chain_name: Chain name (e.g. ``"my-chain"``) or a full ref
                    (``"agent-name/chain-name"``).
        version:    Specific version number to load. ``None`` loads the
                    current (latest saved) chain content.
        client:     Optional pre-configured :class:`~aops._client.AopsClient`.
                    When omitted the global configuration is used.
        **variables: Template variables to substitute into the prompt.
                     Keys must match ``{variable}`` placeholders in the chain
                     content. Passed as keyword arguments::

                         pull("classify", inquiry=user_input)
                         pull("escalate", inquiry=user_input, response=llm_output)

    Returns:
        A raw ``str`` combining the chain's ``persona`` and ``content``,
        with any ``{variable}`` placeholders substituted.

    Example::

        import aops
        aops.init(api_key="aops_...", agent="my-agent")

        from aops import pull

        # No variables
        system_prompt = pull("system")

        # With variables — substituted and recorded as input in the trace
        prompt = pull("classify", inquiry=user_input)
        prompt = pull("escalate", inquiry=user_input, response=llm_output)
    """
    from aops._run import _active_chain, get_current_run

    c = client or AopsClient()
    called_at = datetime.now(timezone.utc)
    agent_id, resolved_chain, persona, content = _fetch_chain(chain_name, version, c)
    latency_ms = int((datetime.now(timezone.utc) - called_at).total_seconds() * 1000)

    prompt = format_prompt(persona, content)
    if variables:
        prompt = prompt.format(**variables)

    input_str: str | None = None
    if variables:
        if len(variables) == 1:
            input_str = str(next(iter(variables.values())))
        else:
            input_str = json.dumps(variables, ensure_ascii=False)

    ctx = get_current_run()
    if ctx is not None:
        if ctx.agent_id is None:
            ctx.agent_id = agent_id
        ctx.record_call(
            chain_name=resolved_chain,
            called_at=called_at,
            latency_ms=latency_ms,
            input=input_str,
        )

    _active_chain.set(resolved_chain)

    return prompt


def _resolve_ref(chain_name: str) -> tuple[str, str]:
    """Return (agent_name, chain_name) from a chain_name or full ref."""
    if "/" in chain_name:
        agent, chain = chain_name.split("/", 1)
        return agent, chain

    config = get_config()
    if not config.agent:
        raise ValueError(
            "Agent name is required. Either pass a full ref (\"agent/chain\"), "
            "set it in init(): aops.init(agent=\"my-agent\"), "
            "or set the AGENTOPS_AGENT environment variable."
        )
    return config.agent, chain_name
