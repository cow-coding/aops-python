"""
LangChain integration example — aops.langchain
=================================================
aops.langchain.pull()  →  SystemMessagePromptTemplate  →  LangChain chain

Before running:
    pip install "aops[langchain]" langchain-openai python-dotenv
    AGENTOPS_API_KEY=aops_...  OPENAI_API_KEY=sk-...
"""

import os
from dotenv import load_dotenv

load_dotenv()

import aops
from aops.langchain import pull, chain_prompt
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_openai import ChatOpenAI

aops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

AGENT_NAME = "test-agent"
CHAIN_NAME = "user-input"
MODEL = "gpt-4o-mini"

llm = ChatOpenAI(model=MODEL)


# ── Example 1: pull() — LangChain chain 직접 구성 ─────────────────────────────

def example_pull():
    print("=== Example 1: aops.langchain.pull() → LangChain chain ===")
    prompt = pull(f"{AGENT_NAME}/{CHAIN_NAME}")

    chain = (
        ChatPromptTemplate.from_messages([
            prompt,
            HumanMessagePromptTemplate.from_template("{user_input}"),
        ])
        | llm
        | StrOutputParser()
    )

    result = chain.invoke({"user_input": "Hello, how's the weather today?"})
    print(result)


# ── Example 2: @chain_prompt 함수 데코레이터 ──────────────────────────────────
# 매 호출마다 캐시에서 프롬프트를 읽어 chain을 새로 구성.
# 라이브 업데이트가 자동으로 반영됨.

@chain_prompt(AGENT_NAME, CHAIN_NAME)
def answer(prompt: SystemMessagePromptTemplate, user_input: str) -> str:
    return (
        ChatPromptTemplate.from_messages([
            prompt,
            HumanMessagePromptTemplate.from_template("{user_input}"),
        ])
        | llm
        | StrOutputParser()
    ).invoke({"user_input": user_input})

def example_function_decorator():
    print("\n=== Example 2: @chain_prompt 함수 데코레이터 ===")
    result = answer(user_input="What's the weather like tomorrow?")
    print(result)


# ── Example 3: @chain_prompt 클래스 데코레이터 ────────────────────────────────
# __init__에서 프롬프트를 한 번만 fetch하여 chain에 고정.
# 성능이 중요하고 프롬프트 변경이 드문 에이전트에 적합.
# 프롬프트 변경을 반영하려면 클래스를 재인스턴스화할 것.

@chain_prompt(AGENT_NAME, CHAIN_NAME)
class WeatherAgent:
    def __init__(self, prompt: SystemMessagePromptTemplate) -> None:
        self.chain = (
            ChatPromptTemplate.from_messages([
                prompt,
                HumanMessagePromptTemplate.from_template("{user_input}"),
            ])
            | llm
            | StrOutputParser()
        )

    def run(self, user_input: str) -> str:
        return self.chain.invoke({"user_input": user_input})

def example_class_decorator():
    print("\n=== Example 3: @chain_prompt 클래스 데코레이터 ===")
    agent = WeatherAgent()
    result = agent.run(user_input="How's the weather in Busan this weekend?")
    print(result)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    example_pull()
    example_function_decorator()
    example_class_decorator()
