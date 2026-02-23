# aops

[![PyPI](https://img.shields.io/pypi/v/aops)](https://pypi.org/project/aops/)
[![Python](https://img.shields.io/pypi/pyversions/aops)](https://pypi.org/project/aops/)

LangChain integration library for [AOps](https://github.com/cow-coding/aops) — load and version-control your agent prompts from the AOps backend.

## Installation

```bash
pip install aops
```

## Quick Start

```python
import aops
from aops.langchain import pull
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

aops.init(api_key="aops_...")

prompt = pull("my-agent/my-chain")

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

## Docs

- [Configuration](docs/configuration.md) — API key, `aops.init()`, environment variables
- [API Reference](docs/api.md) — `pull()`, `@chain_prompt` function & class decorators
- [Live Updates](docs/live-updates.md) — polling, pattern selection guide

## License

MIT
