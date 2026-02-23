class AopsError(Exception):
    """Base exception for aops."""


class AgentNotFoundError(AopsError):
    """Agent with the given name does not exist."""


class ChainNotFoundError(AopsError):
    """Chain with the given name does not exist."""


class VersionNotFoundError(AopsError):
    """The requested chain version does not exist."""


class AopsConnectionError(AopsError):
    """Failed to connect to the AgentOps backend."""
