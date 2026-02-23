# aops

LangChain integration library for [AOps](https://github.com/cow-coding/AgentOps) — load agent prompt configurations from the AOps backend and use them directly in LangChain chains.

## Requirements

- Python 3.12+
- AOps backend running (self-hosted)
- API key issued from the AOps UI (Agent detail page → New API Key)

## Installation

```bash
pip install aops
```

## Quick Start

```python
from dotenv import load_dotenv
load_dotenv()

import aops
aops.init(api_key="aops_...")

from aops.langchain import pull
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

system_prompt = pull("my-agent/my-chain")

chain = (
    ChatPromptTemplate.from_messages([
        system_prompt,
        HumanMessagePromptTemplate.from_template("{user_input}"),
    ])
    | ChatOpenAI(model="gpt-4o-mini")
    | StrOutputParser()
)

result = chain.invoke({"user_input": "Hello!"})
```

## Configuration

### API Key

AOps API keys embed the server host, so no separate `base_url` is needed.

```
aops_{base64(host)}_{token}
```

Issue a key from the AOps UI: **Agent detail page → API Keys → New API Key**

### `aops.init()`

Call `init()` once before using any aops functions:

```python
import aops

aops.init(api_key="aops_...")
```

Or use environment variables — `init()` is optional when env vars are set:

```bash
# .env
AGENTOPS_API_KEY=aops_...
OPENAI_API_KEY=sk-...
```

| Environment Variable   | Default                  | Description                          |
|------------------------|--------------------------|--------------------------------------|
| `AGENTOPS_API_KEY`     | —                        | API key (host is parsed from it)     |
| `AGENTOPS_BASE_URL`    | parsed from key          | Override the host embedded in the key |
| `AGENTOPS_API_PREFIX`  | `/api/v1`                | API path prefix                      |
| `AGENTOPS_CACHE_TTL`   | `300`                    | Prompt cache TTL in seconds (`0` = no cache) |

## API

### `pull(ref, *, version=None)`

Fetch a chain from AOps and return a `SystemMessagePromptTemplate`.

```python
from aops.langchain import pull

prompt = pull("my-agent/my-chain")          # latest
prompt = pull("my-agent/my-chain", version=2)  # pinned version
```

The chain's `persona` and `content` are merged into a single system message:

```
# Persona
{persona}

# Content
{content}
```

`content` may contain LangChain template variables (e.g. `{language}`).
`persona` is treated as a fixed string — its braces are escaped automatically.

---

### `@chain_prompt(agent_name, chain_name, *, version=None)`

Decorator that fetches the prompt and injects it as the first argument.

**Function decorator**

```python
from aops.langchain import chain_prompt
from langchain_core.prompts import SystemMessagePromptTemplate

@chain_prompt("my-agent", "my-chain")
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

**Class decorator**

The prompt is injected into `__init__` as the first argument after `self`. Build the chain once and reuse it:

```python
@chain_prompt("my-agent", "my-chain")
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

## License

MIT
