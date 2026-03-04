"""@aops.trace decorator — capture function args/return as input/output."""
import asyncio
import functools
import inspect
from typing import Any, Callable


def trace(chain_name: str) -> Callable:
    """Decorator that captures function args as input and return value as output.

    The decorated function should call ``aops.pull()`` internally; the
    decorator only handles I/O capture.  ``chain_name`` must match the chain
    name used in ``pull()``.

    Args:
        chain_name: The chain name whose last call entry will be updated.

    Example::

        @aops.trace("classify")
        def classify(text: str) -> str:
            prompt = aops.pull("classify")
            response = openai_client.chat.completions.create(...)
            return response.choices[0].message.content

        # async version also supported:
        @aops.trace("classify")
        async def classify_async(text: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        def _get_input(args: tuple, kwargs: dict) -> str | None:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            # Skip 'self' / 'cls' for methods
            non_self = [p for p in params if p not in ("self", "cls")]
            if non_self and args:
                offset = len(params) - len(non_self)
                first_val = args[offset] if len(args) > offset else None
                if first_val is not None:
                    return str(first_val)
            if kwargs:
                return str(next(iter(kwargs.values())))
            return None

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from aops._run import get_current_run

            input_str = _get_input(args, kwargs)
            result = func(*args, **kwargs)
            output_str = str(result) if result is not None else None

            ctx = get_current_run()
            if ctx is not None:
                ctx.update_last_io(chain_name, input_str, output_str)

            return result

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            from aops._run import get_current_run

            input_str = _get_input(args, kwargs)
            result = await func(*args, **kwargs)
            output_str = str(result) if result is not None else None

            ctx = get_current_run()
            if ctx is not None:
                ctx.update_last_io(chain_name, input_str, output_str)

            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper

    return decorator
