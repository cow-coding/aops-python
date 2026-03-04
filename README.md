# aops

[![PyPI](https://img.shields.io/pypi/v/aops)](https://pypi.org/project/aops/)
[![Python](https://img.shields.io/pypi/pyversions/aops)](https://pypi.org/project/aops/)

Python SDK for [AOps](https://github.com/cow-coding/aops) — prompt version management and agent observability platform.

- **Pull prompts** from the AOps backend at runtime (any LLM SDK)
- **Trace runs** — record which chains were called, in what order, and with what latency
- **Capture LLM I/O** — log inputs and outputs per chain for full observability
- **Live updates** — background polling reflects prompt edits without redeployment

---

## Installation

```bash
pip install aops
```

With LangChain integration:

```bash
pip install "aops[langchain]" langchain-openai
```

---

## Quick Start

### 1. Get an API key

In the AOps UI: **Agent detail page → API Keys → New API Key**

The key embeds the server host — no separate `base_url` needed.

### 2. Initialize and pull a prompt

```python
import aops

aops.init(api_key="aops_...", agent="my-agent")

prompt = aops.pull("my-chain")   # returns str
```

### 3. Trace a run

Wrap your agent logic in `aops.run()` to record chain call order and latency:

```python
with aops.run():
    classify_prompt = aops.pull("classify")       # traced
    category = call_llm(classify_prompt, user_input)

    respond_prompt = aops.pull(f"respond-{category}")   # traced
    return call_llm(respond_prompt, user_input)
# → posted to backend on exit, visible in the Flow tab
```

---

## Capturing LLM Input / Output

Choose the integration that fits your stack. All three work with the same `aops.run()` context.

### Option A — LangChain / LCEL (`AopsCallbackHandler`)

Automatically captures every LLM call inside the run block. Works with any LangChain-compatible model.

```python
from aops.langchain import AopsCallbackHandler
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

handler = AopsCallbackHandler()
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])

with aops.run():
    prompt = aops.pull("classify")
    result = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=user_input),
    ])
    # input + output automatically recorded on the "classify" chain call
```

### Option B — OpenAI SDK (`wrap()`)

Wraps the sync OpenAI client to intercept `chat.completions.create()`.

```python
import openai
from aops import wrap

client = wrap(openai.OpenAI())

with aops.run():
    prompt = aops.pull("classify")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input},
        ],
    )
    # input + output automatically recorded
```

> `wrap()` supports `openai.OpenAI` (sync) only. For async, use `AopsCallbackHandler`.

### Option C — Any framework (`@aops.trace` decorator)

Captures the first argument as `input` and the return value as `output`. Works with any LLM library.

```python
@aops.trace("classify")
def classify(user_input: str) -> str:
    prompt = aops.pull("classify")
    return call_any_llm(prompt, user_input)

with aops.run():
    result = classify(user_input)   # input + output recorded
```

Supports `async def` and class methods transparently.

---

## Supported LLM SDKs

`aops.pull()` returns a plain `str` — works with any LLM SDK out of the box.

### OpenAI

```python
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": aops.pull("my-chain")}, ...],
)
```

### Anthropic

```python
from anthropic import Anthropic
client = Anthropic()
message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    system=aops.pull("my-chain"),
    messages=[{"role": "user", "content": "Hello!"}],
)
```

### LangChain (prompt as `SystemMessagePromptTemplate`)

```python
from aops.langchain import pull   # returns SystemMessagePromptTemplate
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI

prompt = pull("my-chain")
chain = (
    ChatPromptTemplate.from_messages([
        prompt,
        HumanMessagePromptTemplate.from_template("{user_input}"),
    ])
    | ChatOpenAI(model="gpt-4o-mini")
)
result = chain.invoke({"user_input": "Hello!"})
```

---

## Requirements

- Python 3.12+
- AOps backend running (self-hosted) — see [github.com/cow-coding/aops](https://github.com/cow-coding/aops)
- API key from the AOps UI

---

## Examples

```
examples/
  openai_example.py       pull() + wrap() + OpenAI SDK
  anthropic_example.py    pull() + Anthropic SDK
  langchain_example.py    AopsCallbackHandler + @chain_prompt
  live_updates.py         background polling / live update detection
```

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Quickstart](docs/quickstart.md) | Step-by-step: from zero to first trace |
| [Configuration](docs/configuration.md) | `aops.init()`, API keys, environment variables |
| [API Reference](docs/api.md) | All public APIs: `pull()`, `run()`, `wrap()`, `@trace`, `AopsCallbackHandler` |
| [Run Tracing](docs/tracing.md) | `aops.run()`, I/O capture, concurrency |
| [Live Updates](docs/live-updates.md) | Background polling, prompt refresh patterns |
| [LangChain](docs/langchain.md) | LCEL patterns, class-based chains, callback handler |

### Integration Quick References

| Integration | Guide |
|-------------|-------|
| LangChain / LCEL | [docs/integrations/langchain.md](docs/integrations/langchain.md) |
| OpenAI SDK | [docs/integrations/openai.md](docs/integrations/openai.md) |
| `@aops.trace` decorator | [docs/integrations/decorator.md](docs/integrations/decorator.md) |

---

## License

MIT
