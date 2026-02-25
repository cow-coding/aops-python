# Live Updates (Polling)

The AOps SDK automatically polls the backend every 60 seconds and refreshes the
prompt cache when a chain's content changes. Prompt updates made in the AOps web
UI are reflected in your running agent within one poll cycle.

## How It Works

1. On the first `pull()` or decorator call, the chain is fetched and cached
2. A background daemon thread polls `GET /agents/{id}/chains/{id}` every `poll_interval` seconds
3. If `updated_at` has changed, the cache is refreshed immediately
4. The next `pull()` call returns the updated prompt

## Pattern Selection

| Pattern | Live updates | Best for |
|---|---|---|
| `pull()` direct call | ✅ | Fetching the latest prompt on every invocation |
| `@chain_prompt` function decorator | ✅ | Functions that should always use the current prompt |
| `@chain_prompt` class decorator | ❌ (fixed at init) | Performance-sensitive agents with infrequent prompt changes |

## Configuration

```python
import aops

# Poll every 30 seconds
aops.init(api_key="aops_...", agent="my-agent", poll_interval=30)

# Disable polling
aops.init(api_key="aops_...", agent="my-agent", poll_interval=0)
```

Or via environment variable:

```bash
AGENTOPS_POLL_INTERVAL=30  # seconds; 0 = disable
```

## Examples

### `pull()` — always reflects the latest prompt

```python
import aops
from aops import pull

aops.init(api_key="aops_...", agent="my-agent")

# Reads from cache; the background poller refreshes the cache on change
system_prompt = pull("my-chain")  # returns str
```

### Live change detection loop

```python
import time
from aops import pull

last = None
while True:
    current = pull("my-chain")
    if last is None:
        print(f"[INIT]    {current[:60]}...")
    elif current != last:
        print(f"[UPDATED] {current[:60]}...")
    else:
        print(f"[OK]      (no change)")
    last = current
    time.sleep(5)
```

### LangChain — function decorator (live updates)

```python
from aops.langchain import chain_prompt
from langchain_core.prompts import SystemMessagePromptTemplate

@chain_prompt("my-chain")
def answer(prompt: SystemMessagePromptTemplate, user_input: str) -> str:
    # prompt is always up-to-date (read from cache on each call)
    chain = ChatPromptTemplate.from_messages([
        prompt,
        HumanMessagePromptTemplate.from_template("{user_input}"),
    ]) | ChatOpenAI() | StrOutputParser()
    return chain.invoke({"user_input": user_input})
```

### LangChain — class decorator (fixed prompt)

```python
@chain_prompt("my-chain")
class MyAgent:
    def __init__(self, prompt: SystemMessagePromptTemplate) -> None:
        # prompt is fixed at construction time
        self.chain = ChatPromptTemplate.from_messages([...]) | ChatOpenAI()

    def run(self, user_input: str) -> str:
        return self.chain.invoke({"user_input": user_input})

agent = MyAgent()  # prompt is baked in here
```

To apply a prompt update with the class decorator, re-instantiate:

```python
agent = MyAgent()
```

## Stopping the Poller

The polling thread is a daemon thread and exits automatically when the process ends.
For short-lived scripts or tests where you need to stop it explicitly, call `close()` on the client:

```python
from aops._client import AopsClient

with AopsClient(api_key="aops_...", agent="my-agent", poll_interval=30) as client:
    prompt = pull("my-chain", client=client)
    # ... do work ...
# poller stops and HTTP pool closes here

# Or manually:
client = AopsClient(api_key="aops_...", agent="my-agent")
try:
    prompt = pull("my-chain", client=client)
finally:
    client.close()
```

> **Note:** The global client created by `aops.init()` is a daemon thread and does not need explicit shutdown in normal application usage.
