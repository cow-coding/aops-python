# OpenAI Integration

Use `aops.wrap()` to automatically capture LLM output when using the OpenAI Python SDK.

> **Note**: `aops.wrap()` supports `openai.OpenAI` (sync) only. For async usage, use [`AopsCallbackHandler`](langchain.md) with LangChain.

## Quick Start

```python
import openai
import aops
from aops import wrap

aops.init(api_key="aops_...", agent="my-agent")

client = wrap(openai.OpenAI())

with aops.run():
    prompt = aops.pull("classify", variables={"inquiry": user_input})
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input},
        ],
    )
```

## Installation

```bash
pip install aops openai
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

`wrap()` returns a proxy that intercepts `chat.completions.create()` and records
`choices[0].message.content` as `output` on the active chain call.

```python
client = wrap(openai.OpenAI())

with aops.run():
    prompt = aops.pull("classify", variables={"inquiry": user_input})
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input},
        ],
    )
    # output: response.choices[0].message.content recorded automatically
```

## Notes

- Only `chat.completions.create()` is intercepted. Other endpoints pass through unchanged.
- Passing `openai.AsyncOpenAI()` to `wrap()` raises a `TypeError` — use `AopsCallbackHandler` for async workflows.
- If no `aops.run()` block is active, the proxy behaves identically to the unwrapped client.
- The wrapped client delegates all other attributes (e.g., `client.models`, `client.files`) to the original client.
