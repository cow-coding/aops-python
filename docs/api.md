# API Reference

## `pull(ref, *, version=None)` — `from aops import pull`

AOps에서 chain을 fetch하여 **raw `str`**로 반환합니다.
어떤 LLM SDK(OpenAI, Anthropic 등)에도 바로 사용할 수 있습니다.

```python
from aops import pull

system_prompt = pull("my-agent/my-chain")           # 최신 버전
system_prompt = pull("my-agent/my-chain", version=2)  # 버전 고정
```

chain의 `persona`와 `content`가 하나의 문자열로 합쳐집니다:

```
{persona}

{content}
```

persona가 비어 있으면 `content`만 반환됩니다.

### OpenAI SDK 예시

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

### Anthropic SDK 예시

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

AOps에서 chain을 fetch하여 **`SystemMessagePromptTemplate`**로 반환합니다.
LangChain chain 구성에 직접 사용할 수 있습니다.

```python
from aops.langchain import pull

prompt = pull("my-agent/my-chain")           # 최신 버전
prompt = pull("my-agent/my-chain", version=2)  # 버전 고정
```

> `aops[langchain]` extra 설치 필요: `pip install "aops[langchain]"`

- `content`는 LangChain 템플릿 변수를 포함할 수 있습니다 (예: `{language}`)
- `persona`의 중괄호는 자동으로 이스케이프됩니다

---

## `@chain_prompt(agent_name, chain_name, *, version=None)`

프롬프트를 fetch하여 첫 번째 인자로 주입하는 데코레이터.

> `aops[langchain]` extra 설치 필요: `pip install "aops[langchain]"`

### 함수 데코레이터

매 호출마다 캐시에서 프롬프트를 읽어 chain을 새로 구성합니다.
라이브 업데이트가 자동으로 반영됩니다.

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

### 클래스 데코레이터

`__init__` 시점에 프롬프트를 한 번 fetch하여 chain에 고정합니다.
성능이 중요하고 프롬프트 변경이 드문 에이전트에 적합합니다.

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

> **Note:** 클래스 데코레이터는 인스턴스화 시점에 프롬프트를 고정합니다.
> 라이브 업데이트를 반영하려면 `pull()`이나 함수 데코레이터를 사용하세요.
> 자세한 내용은 [Live Updates](./live-updates.md)를 참고하세요.
