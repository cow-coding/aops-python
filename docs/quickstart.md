# Quickstart

This guide walks through setting up an agent from scratch — creating the agent, defining chains, issuing an API key, and integrating the SDK into your code.

> **For AI agents**: This document is designed to be followed step by step. Each section includes the exact API calls and code needed to complete the setup autonomously.

---

## Prerequisites

- AOps backend running at a known URL (default: `http://localhost:8000`)
- An AOps account (email + password)
- Python 3.12+
- `pip install aops`

---

## Step 1: Authenticate

All management operations require a JWT token. Obtain one from the login endpoint:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'
```

Response:
```json
{"access_token": "eyJ...", "token_type": "bearer"}
```

Use `Authorization: Bearer <access_token>` on all subsequent requests.

---

## Step 2: Create an Agent

```bash
curl -s -X POST http://localhost:8000/api/v1/agents/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-agent",
    "description": "Brief description of what this agent does."
  }'
```

- **Name rules**: lowercase letters, digits, hyphens only (e.g. `cs-agent`, `hr-bot`)
- Returns `{"id": "<agent_id>", ...}` — save `agent_id` for next steps
- Returns `409` if the name already exists

---

## Step 3: Create Chains

A chain holds a versioned prompt. Create one chain per logical step in your agent.

```bash
curl -s -X POST http://localhost:8000/api/v1/agents/<agent_id>/chains/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "classify",
    "description": "Classifies the user inquiry into a category.",
    "persona": null,
    "content": "Classify the following inquiry into one of: technical, billing, general.\n\nReturn JSON only: {\"category\": \"...\", \"confidence\": 0.0}\n\nInquiry: {inquiry}",
    "message": "Initial version"
  }'
```

**Field reference**:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Unique per agent. Pattern: `^[a-z0-9][a-z0-9_-]*$` |
| `content` | ✅ | Prompt text. Use `{variable}` for template placeholders |
| `persona` | — | Role description prepended to `content` (e.g. "You are Alex, a support specialist") |
| `description` | — | Human-readable note shown in the UI |
| `message` | — | Commit message for this version (default: "Initial version") |

Repeat for each chain in your agent (e.g. `system`, `classify`, `respond-technical`, `escalate`).

---

## Step 4: Issue an API Key

API keys are scoped to a single agent and are used by the SDK at runtime.

```bash
curl -s -X POST http://localhost:8000/api/v1/agents/<agent_id>/api-keys/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "production"}'
```

Response:
```json
{
  "id": "...",
  "key": "aops_aHR0cDovL..._abc123",
  "name": "production"
}
```

> **Important**: The full `key` is returned only once. Save it securely — only the prefix is stored.

The key embeds the backend host, so no separate `base_url` is needed in the SDK.

---

## Step 5: Install the SDK

```bash
pip install aops
```

For LangChain:
```bash
pip install "aops[langchain]" langchain-openai
```

---

## Step 6: Initialize and Pull

```python
import aops

aops.init(api_key="aops_...", agent="my-agent")

# Fetch a chain prompt — returns a plain str
prompt = aops.pull("classify")
print(prompt)
```

Or via environment variables (no `init()` call needed):

```bash
export AGENTOPS_API_KEY="aops_..."
export AGENTOPS_AGENT="my-agent"
```

```python
from aops import pull
prompt = pull("classify")
```

---

## Step 7: Add Tracing

Wrap agent logic in `aops.run()` to record execution traces visible in the Flow tab:

```python
import aops

aops.init(api_key="aops_...", agent="my-agent")

def handle(user_input: str) -> str:
    with aops.run():
        classify_prompt = aops.pull("classify").replace("{inquiry}", user_input)
        category = call_llm(classify_prompt)

        respond_prompt = aops.pull(f"respond-{category}").replace("{inquiry}", user_input)
        return call_llm(respond_prompt)
```

---

## Step 8: Capture LLM Input / Output (optional)

Pick one method based on your LLM library.

### LangChain — `AopsCallbackHandler`

```python
from aops.langchain import AopsCallbackHandler
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

handler = AopsCallbackHandler()
llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[handler])

with aops.run():
    prompt = aops.pull("classify")
    result = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=user_input)])
```

### OpenAI SDK — `wrap()`

```python
import openai
from aops import wrap

client = wrap(openai.OpenAI())

with aops.run():
    prompt = aops.pull("classify")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_input}],
    )
```

### Any framework — `@aops.trace`

```python
@aops.trace("classify")
def classify(user_input: str) -> str:
    prompt = aops.pull("classify")
    return call_any_llm(prompt, user_input)

with aops.run():
    result = classify(user_input)
```

---

## Full Example: Customer Support Agent

```python
import json
import aops
from aops import wrap
from openai import OpenAI

aops.init(api_key="aops_...", agent="cs-agent")
client = wrap(OpenAI())

def call_llm(system: str, user: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return response.choices[0].message.content.strip()

def handle(inquiry: str) -> str:
    system_prompt = aops.pull("system")   # outside run() → not traced

    with aops.run():
        # Classify
        classify_prompt = aops.pull("classify").replace("{inquiry}", inquiry)
        raw = call_llm(system_prompt, classify_prompt)
        category = json.loads(raw).get("category", "general")

        # Respond
        respond_prompt = aops.pull(f"respond-{category}").replace("{inquiry}", inquiry)
        return call_llm(system_prompt, respond_prompt)

print(handle("My payment failed twice."))
```

---

## Verify Setup

After running your agent, verify data is being recorded:

```bash
# Check stats for a specific chain
curl -s http://localhost:8000/api/v1/agents/<agent_id>/chains/<chain_id>/stats \
  -H "X-API-Key: aops_..."

# Expected:
# {"total_calls": 3, "avg_latency_ms": 14.5, "last_called_at": "..."}
```

Or open the AOps UI → Agent → **Flow** tab to see the execution graph.

---

## Next Steps

- [Configuration](configuration.md) — environment variables, cache TTL, polling
- [API Reference](api.md) — full API surface
- [Run Tracing](tracing.md) — concurrency, excluding shared chains
- [LangChain](langchain.md) — LCEL patterns, class-based chains
