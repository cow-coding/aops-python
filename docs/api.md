# API Reference

## `pull(ref, *, version=None)`

Fetches a chain from AOps and returns a `SystemMessagePromptTemplate`.

```python
from aops.langchain import pull

prompt = pull("my-agent/my-chain")           # latest version
prompt = pull("my-agent/my-chain", version=2)  # pinned version
```

The chain's `persona` and `content` are merged into a single system message:

```
# Persona
{persona}

# Content
{content}
```

- `content` may contain LangChain template variables (e.g. `{language}`)
- `persona` is treated as a fixed string — braces are escaped automatically

---

## `@chain_prompt(agent_name, chain_name, *, version=None)`

Decorator that fetches the prompt and injects it as the first argument.

### Function decorator

Prompt is fetched on every call (from cache). Use when you want the chain
built fresh each invocation.

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

Prompt is injected into `__init__` once at construction time. The chain is
built once and reused across calls — best for performance-sensitive agents
where the prompt changes infrequently.

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
> If you need the prompt to reflect live updates, use `pull()` or the
> function decorator instead. See [Live Updates](./live-updates.md).
