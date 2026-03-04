# API Reference

## `aops.init()`

Configure the AgentOps connection. Call once at startup.

```python
import aops

aops.init(api_key="aops_...", agent="my-agent")
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_key` | `str` | `AGENTOPS_API_KEY` env | API key (host is parsed from it) |
| `agent` | `str` | `AGENTOPS_AGENT` env | Default agent name for `pull()` calls |
| `base_url` | `str` | parsed from key | Override the host embedded in the key |
| `cache_ttl` | `int` | `300` | Prompt cache TTL in seconds (`0` = no cache) |
| `poll_interval` | `int` | `60` | Polling interval in seconds (`0` = disable) |

---

## `pull(chain_name, *, version=None, variables=None)` — `from aops import pull`

Fetches a chain and returns it as a raw **`str`**.
Works with any LLM SDK (OpenAI, Anthropic, etc.) out of the box.

The agent name is resolved in this order:
1. Explicit `"agent-name/chain-name"` ref passed as `chain_name`
2. Agent set in `aops.init(agent="my-agent")`
3. `AGENTOPS_AGENT` environment variable

```python
import aops
from aops import pull

aops.init(api_key="aops_...", agent="my-agent")

system_prompt = pull("my-chain")                        # no variables
system_prompt = pull("my-chain", version=2)             # pinned version
system_prompt = pull("other-agent/my-chain")            # cross-agent ref
prompt = pull("classify", variables={"inquiry": text})  # with variables
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `chain_name` | `str` | — | Chain name or `"agent/chain"` ref |
| `version` | `int \| None` | `None` | Pin a specific version. `None` = latest |
| `client` | `AopsClient \| None` | `None` | Custom client instead of global |
| `variables` | `dict[str, str] \| None` | `None` | Template variables to substitute into `{placeholders}` |

The chain's `persona` and `content` are merged, then `variables` are substituted:

```
{persona}

{content with {variable} placeholders filled in}
```

If `persona` is empty, only `content` is returned.

### Template Variables

Pass a `variables` dict to substitute `{placeholder}` tokens in the chain content.
This matches the OpenAI Responses API `variables={}` and LangChain `invoke({})` patterns:

```python
# Single variable
prompt = pull("classify", variables={"inquiry": user_input})

# Multiple variables
prompt = pull("escalate", variables={"inquiry": user_input, "response": llm_output})
```

When `variables` is provided and the call is inside `aops.run()`, the **rendered prompt**
(chain instructions + substituted values) is recorded as `input` in the trace log.

### OpenAI SDK example

```python
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello!"},
    ],
)
```

### Anthropic SDK example

```python
from anthropic import Anthropic

client = Anthropic()
message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    system=system_prompt,
    messages=[{"role": "user", "content": "Hello!"}],
)
```

---

## `pull(chain_name, *, version=None)` — `from aops.langchain import pull`

Fetches a chain and returns it as a **`SystemMessagePromptTemplate`**.
Agent name resolution is identical to the top-level `pull()`.

```python
import aops
from aops.langchain import pull

aops.init(api_key="aops_...", agent="my-agent")

prompt = pull("my-chain")            # latest version
prompt = pull("my-chain", version=2) # pinned version
```

> Requires `aops[langchain]` extra: `pip install "aops[langchain]"`

- `content` may contain LangChain template variables (e.g. `{language}`)
- Braces in `persona` are escaped automatically

---

## `@chain_prompt(chain_name, *, version=None)`

Decorator that fetches the prompt and injects it as the first argument.
Agent name resolution is identical to `pull()`.

> Requires `aops[langchain]` extra: `pip install "aops[langchain]"`

### Function decorator

Reads the prompt from cache on every call and builds the chain fresh.
Live updates are reflected automatically.

```python
import aops
from aops.langchain import chain_prompt
from langchain_core.prompts import SystemMessagePromptTemplate

aops.init(api_key="aops_...", agent="my-agent")

@chain_prompt("my-chain")
def answer(prompt: SystemMessagePromptTemplate, user_input: str) -> str:
    return (
        ChatPromptTemplate.from_messages([
            prompt,
            HumanMessagePromptTemplate.from_template("{user_input}"),
        ])
        | ChatOpenAI(model="gpt-4o-mini")
        | StrOutputParser()
    ).invoke({"user_input": user_input})

result = answer(user_input="What is AOps?")
```

### Class decorator

Fetches the prompt once at `__init__` and bakes it into the chain.
Best for performance-sensitive agents where the prompt changes infrequently.

```python
@chain_prompt("my-chain")
class MyAgent:
    def __init__(self, prompt: SystemMessagePromptTemplate) -> None:
        self.chain = (
            ChatPromptTemplate.from_messages([
                prompt,
                HumanMessagePromptTemplate.from_template("{user_input}"),
            ])
            | ChatOpenAI(model="gpt-4o-mini")
            | StrOutputParser()
        )

    def run(self, user_input: str) -> str:
        return self.chain.invoke({"user_input": user_input})

agent = MyAgent()
result = agent.run(user_input="Hello!")
```

> **Note:** The class decorator bakes the prompt at instantiation time.
> To reflect live updates, use `pull()` or the function decorator instead.
> See [Live Updates](./live-updates.md).

---

## `AopsClient`

Low-level HTTP client. Normally you don't need to instantiate it directly — `pull()` and decorators use the global client configured by `aops.init()`.

Useful when you need explicit lifecycle control (e.g. short-lived scripts, tests, or multiple isolated clients):

```python
from aops import AopsClient

# Context manager — closes the HTTP pool and stops the poller on exit
with AopsClient(api_key="aops_...", poll_interval=0) as client:
    from aops import pull
    prompt = pull("my-chain", client=client)

# Manual close
client = AopsClient(api_key="aops_...")
try:
    prompt = pull("my-chain", client=client)
finally:
    client.close()
```

### `client.close()`

Signals the background polling thread to stop and closes the underlying HTTP connection pool. Safe to call multiple times.

---

## `aops.run()`

Context manager that traces all `pull()` calls within the block and posts the run to the backend on exit.

```python
with aops.run():
    prompt = aops.pull("classify")
    result = call_llm(prompt, user_input)
# → POST /agents/{id}/runs on exit
```

See [Run Tracing](tracing.md) for full details.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `client` | `AopsClient \| None` | `None` | Use a custom client instead of the global one |

---

## `aops.wrap(client)`

Wraps a sync `openai.OpenAI` client to automatically record LLM **output** from `chat.completions.create()` to the active run context. **Input** is recorded at `pull()` time via `variables`.

```python
import openai
from aops import wrap

client = wrap(openai.OpenAI())

with aops.run():
    prompt = aops.pull("my-chain", variables={"inquiry": user_input})
    # ↑ input recorded here
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_input}],
    )
    # ↑ output (choices[0].message.content) recorded automatically
```

- Intercepts only `chat.completions.create()`. All other client attributes pass through unchanged.
- Raises `TypeError` if passed an `openai.AsyncOpenAI` instance.
- No-op when called outside an `aops.run()` block.

> Requires `pip install openai`. See [docs/integrations/openai.md](integrations/openai.md).

---

## `@aops.trace(chain_name)`

Decorator that captures a function's first meaningful argument as `input` and its return value as `output`, writing them to the most recent `pull(chain_name)` call in the active run.

```python
@aops.trace("classify")
def classify(user_input: str) -> str:
    prompt = aops.pull("classify")
    return call_llm(prompt, user_input)

with aops.run():
    result = classify("My payment failed.")
    # input = "My payment failed.", output = result
```

- Works with `async def` (detected automatically via `asyncio.iscoroutinefunction`)
- Skips `self` and `cls` when determining the input argument
- No-op (no I/O recorded) when called outside `aops.run()` or if the function raises

> See [docs/integrations/decorator.md](integrations/decorator.md) for class method and async examples.

---

## `AopsCallbackHandler` — `from aops.langchain import AopsCallbackHandler`

LangChain `BaseCallbackHandler` subclass that records LLM **output** to the active run context.
**Input** is recorded at `pull()` time via `variables` — the handler only handles output.

```python
from aops.langchain import AopsCallbackHandler
from langchain_openai import ChatOpenAI

handler = AopsCallbackHandler()
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])

with aops.run():
    prompt = aops.pull("my-chain", variables={"inquiry": user_input})  # input recorded here
    result = llm.invoke([...])                                          # output recorded here
```

Hooks implemented:

| Hook | Captures |
|------|----------|
| `on_llm_end` | `generations[0][0].text` as `output` |

- Only records when inside an `aops.run()` block and after a `pull()` call has set the active chain.
- Thread and async safe via `ContextVar`.

> Requires `pip install "aops[langchain]"`. See [docs/integrations/langchain.md](integrations/langchain.md).
