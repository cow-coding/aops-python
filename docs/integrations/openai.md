# OpenAI Integration

Use `aops.wrap()` to automatically capture LLM inputs/outputs when using the OpenAI Python SDK.

## Quick Start

```python
import openai
import aops
from aops import wrap

aops.init(api_key="aops_...", agent="my-agent")

client = wrap(openai.OpenAI())

with aops.run():
    prompt = aops.pull("my-chain")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Hello!"},
        ],
    )
```

## Installation

```bash
pip install aops openai
```

## Usage

### wrap()

`aops.wrap(client)` returns a proxy that intercepts `chat.completions.create()`:

```python
from aops import wrap
import openai

client = wrap(openai.OpenAI())
```

The proxy captures:
- `input`: serialized `messages` list (`[role] content` format)
- `output`: `choices[0].message.content`

These are stored on the most recent `pull()` call within the active `aops.run()` block.

### Sync Example

```python
with aops.run():
    prompt = aops.pull("classifier")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_text},
        ],
    )
    print(response.choices[0].message.content)
```

### Async Example

```python
import openai
import aops
from aops import wrap

async_client = wrap(openai.AsyncOpenAI())

async def classify(text: str) -> str:
    with aops.run():
        prompt = aops.pull("classifier")
        response = await async_client.chat.completions.acreate(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content
```

## Notes

- Only `chat.completions.create()` (and `acreate()`) are intercepted. Other OpenAI endpoints pass through unchanged.
- If no `aops.run()` block is active, the proxy behaves identically to the unwrapped client.
- The wrapped client delegates all other attributes (e.g., `client.models`, `client.files`) to the original client.
