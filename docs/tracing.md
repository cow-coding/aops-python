# Run Tracing

`aops.run()` is a context manager that automatically records every `pull()` call
made inside the block and posts the trace to the AgentOps backend when the block
exits.

## Basic Usage

```python
import aops

aops.init(api_key="aops_...", agent="cs-agent")

with aops.run():
    prompt = aops.pull("greeting")       # recorded
    response = llm.invoke(prompt)
# ↑ run ends here — chain calls are posted to the backend
```

On exit, the SDK posts to `POST /agents/{agent_id}/runs` with:

- `started_at` / `ended_at` — wall-clock timestamps of the run block
- `chain_calls` — list of `{ chain_name, called_at, latency_ms }` for every
  successful `pull()` inside the block

The data is then available through `GET /agents/{agent_id}/flow`, which
aggregates call counts and average latency per chain — used by the **Flow** tab
in the AgentOps UI.

## How It Works

```
with aops.run():          ← RunContext created, stored in ContextVar
    pull("greeting")      ← called_at recorded; on success → RunContext.record_call()
    pull("classify")      ← same
                          ← block exits: ended_at set, POST /runs sent (best-effort)
```

1. `aops.run()` creates a `RunContext` and stores it in a `ContextVar`.
2. Every `pull()` inside the block checks `get_current_run()` and, on success,
   appends `chain_name`, `called_at`, and `latency_ms` to the context.
3. On block exit the context manager sets `ended_at`, resets the `ContextVar`,
   and fires `POST /agents/{agent_id}/runs`.
4. If the backend call fails (network error, invalid key), a **warning is
   logged** and the exception is suppressed — your agent code is never interrupted
   by a tracing failure.

## Concurrency

`ContextVar` is natively aware of Python threads and `asyncio` tasks. Each
concurrent request gets its own isolated `RunContext`:

```python
import asyncio
import aops

aops.init(api_key="aops_...", agent="cs-agent")

async def handle_request(inquiry: str) -> str:
    with aops.run():                          # isolated per coroutine
        prompt = aops.pull("classify")
        category = await classify_llm(prompt, inquiry)

        prompt2 = aops.pull(f"response-{category}")
        return await respond_llm(prompt2, inquiry)

# Two requests run concurrently — their traces are independent
await asyncio.gather(
    handle_request("How do I reset my password?"),
    handle_request("I want a refund."),
)
```

> **Note:** `aops.run()` uses `contextvars.ContextVar`, which is automatically
> inherited by `asyncio` tasks created inside the block (via `asyncio.create_task`).
> For threads, each thread has its own `ContextVar` copy, so there is no
> cross-thread leakage.

## Excluding Common Chains from Tracing

Some chains — like a shared `system` or `safety-rules` chain — are pulled once
at startup and reused across all requests. Pulling them **outside** of any
`run()` block means they are never recorded in per-request traces, which keeps
the Flow graph focused on request-level chains.

```python
import aops

aops.init(api_key="aops_...", agent="cs-agent")

# Pulled once at startup — NOT inside run(), so never traced
SYSTEM_PROMPT = aops.pull("system")
SAFETY_RULES  = aops.pull("safety-rules")

def handle(inquiry: str) -> str:
    with aops.run():
        # Only request-specific chains appear in the trace
        classify_prompt = aops.pull("classify")
        category = classify(classify_prompt, inquiry)

        response_prompt = aops.pull(f"response-{category}")
        return respond(SYSTEM_PROMPT, SAFETY_RULES, response_prompt, inquiry)
```

## cs-agent Example

A customer-service agent that classifies incoming inquiries and routes them to
the appropriate response chain:

```python
import aops
from anthropic import Anthropic

aops.init(api_key="aops_...", agent="cs-agent")
client = Anthropic()

# Common chains — pulled once, excluded from per-request traces
SYSTEM_PROMPT = aops.pull("system")

CATEGORY_CHAINS = {
    "refund":    "response-refund",
    "password":  "response-password",
    "shipping":  "response-shipping",
    "other":     "response-general",
}

def classify(inquiry: str) -> str:
    prompt = aops.pull("classify")   # inside run() → traced
    result = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        system=prompt,
        messages=[{"role": "user", "content": inquiry}],
    )
    return result.content[0].text.strip().lower()

def respond(category: str, inquiry: str) -> str:
    chain_name = CATEGORY_CHAINS.get(category, "response-general")
    prompt = aops.pull(chain_name)   # inside run() → traced
    result = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT + "\n\n" + prompt,
        messages=[{"role": "user", "content": inquiry}],
    )
    return result.content[0].text

def handle_inquiry(inquiry: str) -> str:
    with aops.run():
        category = classify(inquiry)
        return respond(category, inquiry)

# Example
if __name__ == "__main__":
    print(handle_inquiry("I'd like a refund for order #12345."))
    print(handle_inquiry("How do I reset my password?"))
```

After a few requests, `GET /agents/{agent_id}/flow` returns data like:

```json
[
  {"chain_name": "classify",         "call_count": 100, "avg_latency_ms": 42.3},
  {"chain_name": "response-refund",  "call_count": 38,  "avg_latency_ms": 61.0},
  {"chain_name": "response-password","call_count": 27,  "avg_latency_ms": 55.5},
  {"chain_name": "response-shipping","call_count": 21,  "avg_latency_ms": 58.2},
  {"chain_name": "response-general", "call_count": 14,  "avg_latency_ms": 60.1}
]
```

This is rendered as a flow graph in the AgentOps UI, showing which chains are
called and how often.

## Capturing LLM Input / Output

By default, `aops.run()` records **which chains were called** and their latency.
To also capture `input` and `output` per chain call:

- **`input`** — recorded at `pull()` time when `variables` are passed: the rendered prompt (chain instructions + substituted values).
- **`output`** — recorded after the LLM responds, via `AopsCallbackHandler`, `wrap()`, or `@aops.trace`.

### Step 1 — Pass `variables` to `pull()`

```python
with aops.run():
    prompt = aops.pull("classify", variables={"inquiry": user_input})
    # ↑ input recorded here: rendered prompt = chain instructions + user_input substituted
```

Without `variables`, `input` stays `None` — useful for static chains (e.g. a fixed system persona).

### Step 2 — Capture output

Pick one method based on your LLM library.

#### Option A — LangChain `AopsCallbackHandler`

```python
import aops
from aops.langchain import AopsCallbackHandler
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

aops.init(api_key="aops_...", agent="my-agent")
handler = AopsCallbackHandler()
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])

with aops.run():
    prompt = aops.pull("classify", variables={"inquiry": user_input})
    result = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=user_input)])
    # output recorded by handler on llm_end
```

> Requires `pip install "aops[langchain]"`. See [docs/integrations/langchain.md](integrations/langchain.md).

#### Option B — OpenAI SDK `wrap()`

```python
import openai, aops
from aops import wrap

aops.init(api_key="aops_...", agent="my-agent")
client = wrap(openai.OpenAI())

with aops.run():
    prompt = aops.pull("classify", variables={"inquiry": user_input})
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_input}],
    )
    # output recorded by proxy on create()
```

> Supports `openai.OpenAI` (sync) only. See [docs/integrations/openai.md](integrations/openai.md).

#### Option C — `@aops.trace` decorator

Captures the function's first argument as `input` and return value as `output`.
Works with any LLM library, regardless of `variables`.

```python
@aops.trace("classify")
def classify(user_input: str) -> str:
    prompt = aops.pull("classify", variables={"inquiry": user_input})
    return call_any_llm(prompt, user_input)

with aops.run():
    result = classify(user_input)
```

> See [docs/integrations/decorator.md](integrations/decorator.md).

### How Input/Output Flows to the Backend

When a run exits, each chain call in the payload includes optional `input` and
`output` fields:

```json
{
  "chain_name": "classify",
  "called_at": "2025-01-15T10:23:01.456Z",
  "latency_ms": 38,
  "input": "You are a classifier...\n\nCustomer inquiry: My payment failed.",
  "output": "{\"category\": \"billing\", \"confidence\": 0.97}"
}
```

The data is visible in the **Logs** tab of the chain detail page in the AOps UI.

---

## `run()` API

```python
aops.run(*, client=None)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `client` | `AopsClient \| None` | `None` | Use a custom client instead of the global one |

Returns a context manager that yields a `RunContext`. You can inspect the
context if needed:

```python
with aops.run() as ctx:
    aops.pull("classify")
    print(ctx.chain_calls)   # list of recorded calls so far
```

If no `pull()` call succeeds inside the block (e.g. all calls are outside the
block or all fail), nothing is posted to the backend.
