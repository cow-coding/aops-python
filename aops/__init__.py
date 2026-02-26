"""aops — Python SDK for AgentOps prompt version management.

Quick start::

    import aops
    aops.init(api_key="aops_aHR0cDovL2xvY2FsaG9zdDo4MDAw_...")

    from aops import pull  # framework-agnostic raw string
    from aops.langchain import pull, chain_prompt  # LangChain integration
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
from aops._pull import pull
from aops._run import run

__all__ = [
    "init",
    "pull",
    "run",
    "AopsClient",
    "generate_key",
    "parse_key",
    "AopsError",
    "AgentNotFoundError",
    "ChainNotFoundError",
    "VersionNotFoundError",
    "AopsConnectionError",
]
