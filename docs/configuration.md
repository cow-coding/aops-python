# Configuration

## API Key

AOps API keys embed the server host — no separate `base_url` needed.

```
aops_{base64(host)}_{token}
```

Issue a key from the AOps UI: **Agent detail page → API Keys → New API Key**

## `aops.init()`

Call `init()` once at startup before using any aops functions:

```python
import aops

aops.init(api_key="aops_...")
```

`init()` is optional when environment variables are set.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AGENTOPS_API_KEY` | — | API key (host is parsed from it) |
| `AGENTOPS_BASE_URL` | parsed from key | Override the host embedded in the key |
| `AGENTOPS_API_PREFIX` | `/api/v1` | API path prefix |
| `AGENTOPS_CACHE_TTL` | `300` | Prompt cache TTL in seconds (`0` = no cache) |
| `AGENTOPS_POLL_INTERVAL` | `60` | Polling interval in seconds (`0` = disable) |

### `.env` example

```bash
AGENTOPS_API_KEY=aops_...
OPENAI_API_KEY=sk-...
```

```python
from dotenv import load_dotenv
load_dotenv()

import aops
# init() not required — reads from env automatically
```
