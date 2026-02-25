from aops._client import AopsClient


def format_prompt(persona: str, content: str) -> str:
    """Merge persona and content into a raw prompt string.

    Args:
        persona: Agent persona text. May be empty.
        content: Chain content text.

    Returns:
        Combined prompt string. If persona is non-empty:
        ``f"{persona}\\n\\n{content}"``. Otherwise just ``content``.
    """
    if persona:
        return f"{persona}\n\n{content}"
    return content


def pull(
    ref: str,
    *,
    version: int | None = None,
    client: AopsClient | None = None,
) -> str:
    """Fetch a chain from AgentOps and return it as a raw string.

    Framework-agnostic alternative to ``aops.langchain.pull()``.
    Works with any LLM SDK (OpenAI, Anthropic, etc.).

    Args:
        ref:     ``"agent-name/chain-name"`` reference string.
        version: Specific version number to load. ``None`` loads the current
                 (latest saved) chain content.
        client:  Optional pre-configured :class:`~aops._client.AopsClient`.
                 When omitted the global configuration is used.

    Returns:
        A raw ``str`` combining the chain's ``persona`` and ``content``.

    Example::

        from aops import pull

        system_prompt = pull("customer-support/greeter")

        # Use with any LLM SDK:
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Hello!"},
            ],
        )
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
        return format_prompt(v.persona, v.content)

    return format_prompt(chain.persona, chain.content)
