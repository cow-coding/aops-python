# LangChain Integration

Capture LLM output automatically in LangChain chains using `AopsCallbackHandler`.

## Quick Start

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
    result = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=user_input)])
```

## Installation

```bash
pip install "aops[langchain]" langchain-openai
```

## How It Works

### Input

`input` is recorded at `pull()` time when `variables` are passed — the rendered prompt
(chain instructions with placeholders substituted):

```python
prompt = aops.pull("classify", variables={"inquiry": user_input})
# → input recorded: full rendered prompt including user_input
```

Without `variables`, `input` stays `None`.

### Output

`AopsCallbackHandler` hooks into LangChain's callback system via `on_llm_end` and records
`generations[0][0].text` as `output` on the active chain call.

```python
handler = AopsCallbackHandler()
llm = ChatOpenAI(callbacks=[handler])
# output captured automatically after every llm.invoke()
```

## LCEL Example

```python
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from aops.langchain import pull, AopsCallbackHandler

handler = AopsCallbackHandler()
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])

with aops.run():
    system_prompt = pull("classifier")  # returns SystemMessagePromptTemplate

    chain = (
        ChatPromptTemplate.from_messages([
            system_prompt,
            HumanMessagePromptTemplate.from_template("{user_input}"),
        ])
        | llm
        | StrOutputParser()
    )

    result = chain.invoke({"user_input": "Is this a question?"})
    # output recorded by handler
```

> Note: `aops.langchain.pull()` returns a `SystemMessagePromptTemplate`. Template variables
> in `content` are handled natively by LangChain at `invoke()` time — no `variables=` needed.

## `@chain_prompt` Decorator

Combine with `AopsCallbackHandler` for full output logging:

```python
from aops.langchain import chain_prompt, AopsCallbackHandler
from langchain_core.prompts import SystemMessagePromptTemplate

handler = AopsCallbackHandler()
llm = ChatOpenAI(callbacks=[handler])

@chain_prompt("summariser")
def summarise(prompt: SystemMessagePromptTemplate, text: str) -> str:
    return (prompt | llm | StrOutputParser()).invoke({"text": text})

with aops.run():
    result = summarise(text="Long article...")
```

## Notes

- `AopsCallbackHandler` only records output when inside an `aops.run()` block.
- If multiple chains are called in sequence, each `pull()` updates `_active_chain`; the handler writes output to the most recent one.
- Thread/async safe — uses Python `ContextVar` internally.
