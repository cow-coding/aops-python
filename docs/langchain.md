# LangChain Integration

The `aops.langchain` module provides LangChain-native helpers for fetching
AgentOps chains. When used inside an `aops.run()` block, chain calls are
automatically traced.

> Requires the `langchain` extra: `pip install "aops[langchain]"`

## `pull()` vs `aops.langchain.pull()`

| | `from aops import pull` | `from aops.langchain import pull` |
|---|---|---|
| **Returns** | `str` | `SystemMessagePromptTemplate` |
| **Works with** | Any LLM SDK | LangChain chains / LCEL |
| **Tracing** | ✅ inside `aops.run()` | ✅ inside `aops.run()` |
| **Template variables** | Raw string — handle yourself | LangChain `{variable}` syntax in `content` |
| **Persona braces** | Raw | Auto-escaped (`{` → `{{`) |

Both functions resolve the agent name identically (via `aops.init()` or the
`AGENTOPS_AGENT` environment variable) and both record the call in the active
`RunContext` when used inside `aops.run()`.

Use `aops.langchain.pull()` when you want a `SystemMessagePromptTemplate` that
slots directly into a `ChatPromptTemplate`. Use the raw `pull()` when you pass
the prompt as a plain string (OpenAI, Anthropic, etc.).

---

## Class-based Chain (`langchain.chains.Chain`)

In a custom `Chain` subclass, call `pull()` inside `_call()` so that every
invocation fetches the current prompt and the call is traced:

```python
import aops
from aops.langchain import pull

from langchain.chains.base import Chain
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from typing import Any

aops.init(api_key="aops_...", agent="cs-agent")

class ClassifyChain(Chain):
    llm: ChatOpenAI = ChatOpenAI(model="gpt-4o-mini")

    @property
    def input_keys(self) -> list[str]:
        return ["inquiry"]

    @property
    def output_keys(self) -> list[str]:
        return ["category"]

    def _call(self, inputs: dict[str, Any]) -> dict[str, Any]:
        # pull() is called at invoke time → traced when inside aops.run()
        system_prompt = pull("classify")

        chain = (
            ChatPromptTemplate.from_messages([
                system_prompt,
                HumanMessagePromptTemplate.from_template("{inquiry}"),
            ])
            | self.llm
            | StrOutputParser()
        )
        category = chain.invoke({"inquiry": inputs["inquiry"]})
        return {"category": category.strip().lower()}

classify_chain = ClassifyChain()

# Trace the invocation
with aops.run():
    result = classify_chain.invoke({"inquiry": "I want a refund."})
    print(result["category"])  # e.g. "refund"
```

The key point: `pull()` is called **inside `_call()`** (i.e. at invocation time,
not at class definition time), so it runs within the `aops.run()` block and is
recorded in the trace.

---

## LCEL — Lazy Pull with `RunnableLambda`

In LCEL pipelines, wrap `pull()` in a `RunnableLambda` so the fetch happens
at invocation time rather than at chain-definition time:

```python
import aops
from aops import pull  # raw pull() — returns str

from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

aops.init(api_key="aops_...", agent="cs-agent")

llm = ChatOpenAI(model="gpt-4o-mini")

# ── Classify step ─────────────────────────────────────────────────────────────
# RunnableLambda runs at invoke() time → pull() is traced inside aops.run()
classify_step = RunnableLambda(
    lambda x: [
        {"role": "system", "content": pull("classify")},
        {"role": "user",   "content": x["inquiry"]},
    ]
)

classify_chain = classify_step | llm | StrOutputParser()

# ── Response step ──────────────────────────────────────────────────────────────
def build_response_messages(x: dict) -> list[dict]:
    chain_name = f"response-{x['category']}"
    return [
        {"role": "system", "content": pull(chain_name)},
        {"role": "user",   "content": x["inquiry"]},
    ]

response_step = RunnableLambda(build_response_messages)
response_chain = response_step | llm | StrOutputParser()

# ── Full pipeline ──────────────────────────────────────────────────────────────
def handle(inquiry: str) -> str:
    with aops.run():
        category = classify_chain.invoke({"inquiry": inquiry}).strip().lower()
        return response_chain.invoke({"inquiry": inquiry, "category": category})

print(handle("How do I reset my password?"))
```

> **Why `RunnableLambda`?**
>
> If you call `pull()` directly at chain-definition time (e.g. `system_prompt = pull("classify")`
> at module level), the fetch happens once on startup and is never traced.
> `RunnableLambda` defers the call to `invoke()` time, which is when `aops.run()`
> is active and can record the call.

---

## Using `aops.langchain.pull()` in LCEL

When you need a `SystemMessagePromptTemplate` (for `ChatPromptTemplate`), use
`aops.langchain.pull()` inside a `RunnableLambda`:

```python
import aops
from aops.langchain import pull  # returns SystemMessagePromptTemplate

from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

aops.init(api_key="aops_...", agent="cs-agent")

llm = ChatOpenAI(model="gpt-4o-mini")

def make_chain(x: dict) -> str:
    # pull() inside the lambda → called at invoke() time → traced
    system_prompt = pull("classify")
    chain = (
        ChatPromptTemplate.from_messages([
            system_prompt,
            HumanMessagePromptTemplate.from_template("{inquiry}"),
        ])
        | llm
        | StrOutputParser()
    )
    return chain.invoke({"inquiry": x["inquiry"]})

pipeline = RunnableLambda(make_chain)

with aops.run():
    result = pipeline.invoke({"inquiry": "Where is my order?"})
    print(result)
```

---

## Capturing LLM Output with `AopsCallbackHandler`

`AopsCallbackHandler` is a LangChain `BaseCallbackHandler` that automatically
records the LLM output for each chain call inside an `aops.run()` block.

**Input** is captured at `pull()` time via `variables`. The handler only handles **output**.

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
    # ↑ input = rendered prompt recorded here
    result = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=user_input)])
    # ↑ output recorded by handler on llm_end
```

### How It Works

1. `aops.pull("classify", variables={"inquiry": user_input})` renders the prompt,
   records it as `input`, and sets `_active_chain = "classify"` in a `ContextVar`.
2. `on_llm_end` fires after the LLM call → writes `generations[0][0].text` as
   `output` to the most recent `"classify"` call in the active `RunContext`.

### LCEL Example

```python
import aops
from aops.langchain import AopsCallbackHandler
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

aops.init(api_key="aops_...", agent="cs-agent")

handler = AopsCallbackHandler()
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])

def build_classify_messages(x: dict) -> list:
    from aops import pull
    prompt = pull("classify", variables={"inquiry": x["inquiry"]})
    return [SystemMessage(content=prompt), HumanMessage(content=x["inquiry"])]

classify_chain = RunnableLambda(build_classify_messages) | llm | StrOutputParser()

with aops.run():
    category = classify_chain.invoke({"inquiry": "My payment failed."})
    # input recorded at pull() time, output recorded by handler
```

### Hooks

| Hook | Captures |
|------|----------|
| `on_llm_end` | `generations[0][0].text` as `output` |

- Only records output when inside an `aops.run()` block and after a `pull()` call.
- Thread and `asyncio`-safe via `ContextVar`.

> Requires `pip install "aops[langchain]"`. See also [docs/integrations/langchain.md](integrations/langchain.md).

---

## Summary: When Is `pull()` Traced?

| Pattern | Traced? | Notes |
|---|---|---|
| `pull()` at module level | ❌ | Runs before any `aops.run()` block |
| `pull()` inside `_call()` | ✅ | Runs at invoke time — inside `aops.run()` |
| `pull()` inside `RunnableLambda` | ✅ | Deferred to invoke time — inside `aops.run()` |
| `@chain_prompt` class decorator | ❌ | Fetches at `__init__` time, not invoke time |
| `@chain_prompt` function decorator | ✅ | Fetches at call time — inside `aops.run()` |

The rule of thumb: **`pull()` is traced only when it runs inside an active
`aops.run()` block.** Structure your code so that `pull()` calls happen at
invocation time, not at definition or startup time.

See [Run Tracing](./tracing.md) for more on how `aops.run()` works.
