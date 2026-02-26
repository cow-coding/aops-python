# aops

[![PyPI](https://img.shields.io/pypi/v/aops)](https://pypi.org/project/aops/)
[![Python](https://img.shields.io/pypi/pyversions/aops)](https://pypi.org/project/aops/)

Python SDK for [AOps](https://github.com/cow-coding/aops) — prompt version management and agent tracing platform.

Provides a framework-agnostic `pull()` that works with any LLM SDK, a `run()` context manager for execution tracing, and a LangChain integration.

## Installation

```bash
pip install aops
```

With LangChain integration:

```bash
pip install "aops[langchain]"
```

## Quick Start

### Pull a prompt

```python
import aops
from aops import pull
from openai import OpenAI

aops.init(api_key="aops_...", agent="my-agent")

system_prompt = pull("my-chain")  # agent resolved from init()

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello!"},
    ],
)
print(response.choices[0].message.content)
```

### Record execution traces

Wrap your agent logic in `aops.run()` to automatically record which chains were called, in what order, and with what latency. The data is posted to the AOps backend and visualized in the **Flow** tab.

```python
import aops

aops.init(api_key="aops_...", agent="my-agent")

# Chains pulled outside run() are not traced (good for shared system prompts)
system_prompt = aops.pull("system")

def handle(inquiry: str) -> str:
    with aops.run():
        classify_prompt = aops.pull("classify")      # traced
        category = classify(classify_prompt, inquiry)

        response_prompt = aops.pull(f"respond-{category}")  # traced
        return respond(system_prompt, response_prompt, inquiry)
```

On block exit, the SDK posts `started_at`, `ended_at`, and the ordered list of chain calls to `POST /agents/:id/runs`. If the backend is unreachable, a warning is logged and the exception is suppressed — your agent is never interrupted by a tracing failure.

### Anthropic SDK

```python
import aops
from aops import pull
from anthropic import Anthropic

aops.init(api_key="aops_...", agent="my-agent")

system_prompt = pull("my-chain")

client = Anthropic()
message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    system=system_prompt,
    messages=[{"role": "user", "content": "Hello!"}],
)
print(message.content[0].text)
```

### LangChain

```python
import aops
from aops.langchain import pull
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

aops.init(api_key="aops_...", agent="my-agent")

prompt = pull("my-chain")

chain = (
    ChatPromptTemplate.from_messages([
        prompt,
        HumanMessagePromptTemplate.from_template("{user_input}"),
    ])
    | ChatOpenAI(model="gpt-4o-mini")
    | StrOutputParser()
)

result = chain.invoke({"user_input": "Hello!"})
```

## Requirements

- Python 3.12+
- AOps backend running (self-hosted)
- API key issued from the AOps UI: **Agent detail page → API Keys → New API Key**

## Examples

```
examples/
  openai_example.py     raw pull() + OpenAI SDK
  anthropic_example.py  raw pull() + Anthropic SDK
  langchain_example.py  aops.langchain — pull(), @chain_prompt
  live_updates.py       background polling / live update detection
```

## Docs

| Guide | Description |
|-------|-------------|
| [Configuration](docs/configuration.md) | API key, `aops.init()`, environment variables |
| [API Reference](docs/api.md) | `pull()`, `aops.langchain.pull()`, `@chain_prompt` |
| [Live Updates](docs/live-updates.md) | Polling, pattern selection guide |
| [Run Tracing](docs/tracing.md) | `aops.run()`, how traces are recorded and posted, async safety |
| [LangChain Compatibility](docs/langchain.md) | Class-based vs LCEL, `RunnableLambda` lazy-pull pattern |

## License

MIT
