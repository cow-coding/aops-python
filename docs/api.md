# API Reference

## `pull(ref, *, version=None)` — `from aops import pull`

Fetches a chain from AOps and returns it as a raw **`str`**.
Works with any LLM SDK (OpenAI, Anthropic, etc.) out of the box.

```python
from aops import pull

system_prompt = pull("my-agent/my-chain")           # latest version
system_prompt = pull("my-agent/my-chain", version=2)  # pinned version
```

The chain's `persona` and `content` are merged into a single string:

```
{persona}

{content}
```

If `persona` is empty, only `content` is returned.

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

## `pull(ref, *, version=None)` — `from aops.langchain import pull`

Fetches a chain from AOps and returns it as a **`SystemMessagePromptTemplate`**.
Can be used directly in LangChain chain composition.

```python
from aops.langchain import pull

prompt = pull("my-agent/my-chain")           # latest version
prompt = pull("my-agent/my-chain", version=2)  # pinned version
```

> Requires `aops[langchain]` extra: `pip install "aops[langchain]"`

- `content` may contain LangChain template variables (e.g. `{language}`)
- Braces in `persona` are escaped automatically

---

## `@chain_prompt(agent_name, chain_name, *, version=None)`

Decorator that fetches the prompt and injects it as the first argument.

> Requires `aops[langchain]` extra: `pip install "aops[langchain]"`

### Function decorator

Reads the prompt from cache on every call and builds the chain fresh.
Live updates are reflected automatically.

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

### Class decorator

Fetches the prompt once at `__init__` and bakes it into the chain.
Best for performance-sensitive agents where the prompt changes infrequently.

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

> **Note:** The class decorator bakes the prompt at instantiation time.
> To reflect live updates, use `pull()` or the function decorator instead.
> See [Live Updates](./live-updates.md).
