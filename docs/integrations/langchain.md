# LangChain Integration

Capture LLM input/output automatically in LangChain chains using `AopsCallbackHandler`.

## Quick Start

```python
import aops
from aops.langchain import AopsCallbackHandler
from langchain_openai import ChatOpenAI

aops.init(api_key="aops_...", agent="my-agent")

handler = AopsCallbackHandler()
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])

with aops.run():
    prompt = aops.pull("my-chain")
    result = llm.invoke([HumanMessage(content="Hello")])
```

## Installation

```bash
pip install "aops[langchain]" langchain-openai
```

## Usage

### Callback Handler

`AopsCallbackHandler` hooks into LangChain's callback system to record LLM inputs and outputs.
Pass it to any LangChain LLM or chain:

```python
from aops.langchain import AopsCallbackHandler

handler = AopsCallbackHandler()
llm = ChatOpenAI(callbacks=[handler])
```

The handler:
- `on_chat_model_start`: captures the serialized message list as `input`
- `on_llm_start`: captures the raw prompt string as `input`
- `on_llm_end`: captures `generations[0][0].text` as `output`

Input/output is written to the most recent `pull()` call in the active `aops.run()` block.

### LCEL Example

```python
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from aops.langchain import pull, AopsCallbackHandler

handler = AopsCallbackHandler()
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])

with aops.run():
    system_prompt = pull("classifier")

    chain = (
        ChatPromptTemplate.from_messages([
            system_prompt,
            HumanMessagePromptTemplate.from_template("{user_input}"),
        ])
        | llm
        | StrOutputParser()
    )

    result = chain.invoke({"user_input": "Is this a question?"})
```

### @chain_prompt Decorator

Use the existing `@chain_prompt` decorator to inject prompts — combine with `AopsCallbackHandler` for full I/O logging:

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

- `AopsCallbackHandler` only records I/O when inside an `aops.run()` block.
- If multiple chains are called in sequence, each `pull()` sets `_active_chain`; the handler writes to the most recent one.
- Thread/async safe — uses Python `ContextVar` internally.
