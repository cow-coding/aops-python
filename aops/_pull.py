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
) -> tuple[str | None, str]:
    """Resolve ref, fetch from backend, and return (persona, content).

    Shared by both the raw ``pull()`` and ``aops.langchain.pull()``.
    """
    agent_name, resolved_chain = _resolve_ref(chain_name)

    agent = client.get_agent_by_name(agent_name)
    chain = client.get_chain_by_name(agent.id, resolved_chain)

    if version is not None:
        v = client.get_chain_version(agent.id, chain.id, version)
        return v.persona, v.content

    return chain.persona, chain.content


def pull(
    chain_name: str,
    *,
    version: int | None = None,
    client: AopsClient | None = None,
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

    Returns:
        A raw ``str`` combining the chain's ``persona`` and ``content``.

    Example::

        # Recommended — declare agent once at startup:
        import aops
        aops.init(api_key="aops_...", agent="my-agent")

        from aops import pull
        system_prompt = pull("my-chain")

        # Full ref also accepted (e.g. for cross-agent access):
        system_prompt = pull("other-agent/my-chain")
    """
    c = client or AopsClient()
    persona, content = _fetch_chain(chain_name, version, c)
    return format_prompt(persona, content)


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
