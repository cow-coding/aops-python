# Live Updates (Polling)

AOps SDK automatically polls the backend every 60 seconds and refreshes the
prompt cache when the chain's content changes. This means prompt updates made
in the AOps web UI are reflected in your running agent within one poll cycle.

## How It Works

1. On the first `pull()` or decorator call, the chain is fetched and cached
2. A background daemon thread polls `GET /agents/{id}/chains/{id}` every `poll_interval` seconds
3. If `updated_at` has changed, the cache is refreshed immediately
4. The next `pull()` call returns the updated prompt

## Pattern Selection

Choose the right pattern based on your needs:

| Pattern | Live updates | Best for |
|---|---|---|
| `pull()` direct call | ✅ | Fetching latest prompt on every invocation |
| `@chain_prompt` function decorator | ✅ | Functions that should always use the current prompt |
| `@chain_prompt` class decorator | ❌ (fixed at init) | Performance-sensitive agents with infrequent prompt changes |

## Configuration

```python
import aops

# Polling every 30 seconds
aops.init(api_key="aops_...", poll_interval=30)

# Disable polling
aops.init(api_key="aops_...", poll_interval=0)
```

Or via environment variable:

```bash
AGENTOPS_POLL_INTERVAL=30  # seconds; 0 = disable
```

## Examples

### `pull()` — always reflects latest prompt

```python
from aops.langchain import pull

# Each call reads from cache; cache is refreshed by the background poller
prompt = pull("my-agent/my-chain")
```

### Function decorator — live updates per call

```python
from aops.langchain import chain_prompt
from langchain_core.prompts import SystemMessagePromptTemplate

@chain_prompt("my-agent", "my-chain")
def answer(prompt: SystemMessagePromptTemplate, user_input: str) -> str:
    # prompt is always up-to-date (fetched from cache on each call)
    chain = ChatPromptTemplate.from_messages([
        prompt,
        HumanMessagePromptTemplate.from_template("{user_input}"),
    ]) | ChatOpenAI() | StrOutputParser()
    return chain.invoke({"user_input": user_input})
```

### Class decorator — fixed prompt (by design)

```python
@chain_prompt("my-agent", "my-chain")
class MyAgent:
    def __init__(self, prompt: SystemMessagePromptTemplate) -> None:
        # prompt is fixed at construction time
        self.chain = ChatPromptTemplate.from_messages([...]) | ChatOpenAI()

    def run(self, user_input: str) -> str:
        return self.chain.invoke({"user_input": user_input})

agent = MyAgent()  # prompt baked in here
```

To apply a prompt update with the class decorator, re-instantiate:

```python
agent = MyAgent()  # re-instantiate to pick up the latest prompt
```
