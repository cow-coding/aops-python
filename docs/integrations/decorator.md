# @aops.trace Decorator

Use `@aops.trace` to capture a function's first argument as `input` and its return value as `output`.

## Quick Start

```python
import aops

aops.init(api_key="aops_...", agent="my-agent")

@aops.trace("my-chain")
def classify(text: str) -> str:
    prompt = aops.pull("my-chain")
    # ... call LLM ...
    return result

with aops.run():
    answer = classify("Is this a question?")
```

## Installation

```bash
pip install aops
```

## Usage

### Basic Decorator

```python
@aops.trace("chain-name")
def my_func(user_input: str) -> str:
    prompt = aops.pull("chain-name")
    # use prompt with any LLM
    return llm_response
```

`@aops.trace(chain_name)`:
- Captures the first non-`self`/non-`cls` argument as `input` (converted to `str`)
- Captures the return value as `output` (converted to `str`)
- Calls `RunContext.update_last_io()` to write I/O on the last recorded call for `chain_name`

### Async Functions

Works transparently with `async def`:

```python
@aops.trace("summariser")
async def summarise(text: str) -> str:
    prompt = aops.pull("summariser")
    response = await async_llm.invoke(prompt, text)
    return response
```

### Class Methods

```python
class MyAgent:
    @aops.trace("classifier")
    def classify(self, text: str) -> str:
        prompt = aops.pull("classifier")
        return self._call_llm(prompt, text)
```

`self` is automatically skipped when determining `input` — the first meaningful argument (`text`) is used.

### Multiple Chains

Each decorator targets a specific chain by name:

```python
@aops.trace("router")
def route(query: str) -> str:
    prompt = aops.pull("router")
    return router_llm(prompt, query)

@aops.trace("responder")
def respond(context: str) -> str:
    prompt = aops.pull("responder")
    return responder_llm(prompt, context)

with aops.run():
    chain = route(query)
    answer = respond(context=chain)
```

## Notes

- `@aops.trace` only writes I/O when inside an `aops.run()` block; outside, it's a no-op wrapper.
- The decorator does **not** call `pull()` — your function must call `aops.pull(chain_name)` internally. The decorator only captures I/O around the function boundary.
- If the function raises an exception, `update_last_io` is not called (input/output remain `None`).
