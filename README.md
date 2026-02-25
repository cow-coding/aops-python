# aops

[![PyPI](https://img.shields.io/pypi/v/aops)](https://pypi.org/project/aops/)
[![Python](https://img.shields.io/pypi/pyversions/aops)](https://pypi.org/project/aops/)

Python SDK for [AOps](https://github.com/cow-coding/aops) — prompt version management platform.

Provides a framework-agnostic raw `pull()` that works with any LLM SDK, as well as a LangChain integration.

## Installation

```bash
pip install aops
```

LangChain 통합이 필요한 경우:

```bash
pip install "aops[langchain]"
```

## Quick Start

### OpenAI SDK

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

### Anthropic SDK

```python
import aops
from aops import pull
from anthropic import Anthropic

aops.init(api_key="aops_...", agent="my-agent")

system_prompt = pull("my-chain")  # agent resolved from init()

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

prompt = pull("my-chain")  # agent resolved from init()

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
  live_updates.py       백그라운드 polling / 라이브 업데이트 감지
```

## Docs

- [Configuration](docs/configuration.md) — API key, `aops.init()`, environment variables
- [API Reference](docs/api.md) — `pull()`, `aops.langchain.pull()`, `@chain_prompt`
- [Live Updates](docs/live-updates.md) — polling, pattern selection guide

## License

MIT
