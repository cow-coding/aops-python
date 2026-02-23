"""aops — LangChain integration for AgentOps.

Quick start::

    import aops
    aops.init(api_key="aops_aHR0cDovL2xvY2FsaG9zdDo4MDAw_...")

    from aops.langchain import pull, chain_prompt
"""

from aops._client import AopsClient
from aops._config import init
from aops._exceptions import (
    AgentNotFoundError,
    AopsConnectionError,
    AopsError,
    ChainNotFoundError,
    VersionNotFoundError,
)
from aops._keys import generate_key, parse_key

__all__ = [
    "init",
    "AopsClient",
    "generate_key",
    "parse_key",
    "AopsError",
    "AgentNotFoundError",
    "ChainNotFoundError",
    "VersionNotFoundError",
    "AopsConnectionError",
]
