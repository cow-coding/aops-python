# Live Updates (Polling)

AOps SDK는 백그라운드에서 60초마다 backend를 polling하여 프롬프트 캐시를 갱신합니다.
AOps 웹 UI에서 프롬프트를 수정하면 다음 poll cycle 이내에 실행 중인 에이전트에 반영됩니다.

## How It Works

1. 첫 `pull()` 또는 데코레이터 호출 시 chain을 fetch하여 캐시에 저장
2. 백그라운드 daemon thread가 `poll_interval`초마다 `GET /agents/{id}/chains/{id}` 호출
3. `updated_at`이 변경된 경우 캐시를 즉시 갱신
4. 다음 `pull()` 호출에서 업데이트된 프롬프트가 반환됨

## Pattern Selection

| Pattern | 라이브 업데이트 | 적합한 상황 |
|---|---|---|
| `pull()` 직접 호출 | ✅ | 매 호출마다 최신 프롬프트를 fetch |
| `@chain_prompt` 함수 데코레이터 | ✅ | 항상 현재 프롬프트를 사용해야 하는 함수 |
| `@chain_prompt` 클래스 데코레이터 | ❌ (init 시 고정) | 프롬프트 변경이 드문 성능 중심 에이전트 |

## Configuration

```python
import aops

# 30초마다 polling
aops.init(api_key="aops_...", poll_interval=30)

# polling 비활성화
aops.init(api_key="aops_...", poll_interval=0)
```

환경 변수로도 설정 가능:

```bash
AGENTOPS_POLL_INTERVAL=30  # seconds; 0 = disable
```

## Examples

### `pull()` — 항상 최신 프롬프트

```python
from aops import pull

# 캐시에서 읽고, 백그라운드 poller가 변경 시 캐시를 갱신
system_prompt = pull("my-agent/my-chain")  # str 반환
```

### 라이브 변경 감지 루프

```python
import time
from aops import pull

last = None
while True:
    current = pull("my-agent/my-chain")
    if last is None:
        print(f"[INIT]    {current[:60]}...")
    elif current != last:
        print(f"[UPDATED] {current[:60]}...")
    else:
        print(f"[OK]      (no change)")
    last = current
    time.sleep(5)
```

### LangChain — 함수 데코레이터 (라이브 업데이트 반영)

```python
from aops.langchain import chain_prompt
from langchain_core.prompts import SystemMessagePromptTemplate

@chain_prompt("my-agent", "my-chain")
def answer(prompt: SystemMessagePromptTemplate, user_input: str) -> str:
    # prompt는 항상 최신 (캐시에서 매 호출마다 읽음)
    chain = ChatPromptTemplate.from_messages([
        prompt,
        HumanMessagePromptTemplate.from_template("{user_input}"),
    ]) | ChatOpenAI() | StrOutputParser()
    return chain.invoke({"user_input": user_input})
```

### LangChain — 클래스 데코레이터 (고정 프롬프트)

```python
@chain_prompt("my-agent", "my-chain")
class MyAgent:
    def __init__(self, prompt: SystemMessagePromptTemplate) -> None:
        # 인스턴스화 시점에 프롬프트 고정
        self.chain = ChatPromptTemplate.from_messages([...]) | ChatOpenAI()

    def run(self, user_input: str) -> str:
        return self.chain.invoke({"user_input": user_input})

agent = MyAgent()  # 프롬프트가 여기서 고정됨
```

프롬프트 업데이트를 반영하려면 재인스턴스화:

```python
agent = MyAgent()
```
