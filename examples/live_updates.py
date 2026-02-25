"""
Live update examples — aops polling
======================================
백그라운드 polling으로 프롬프트 변경을 자동 감지하는 예시.
AOps 웹 UI에서 프롬프트를 수정하면 POLL_INTERVAL 이내에 반영됨.

Before running:
    pip install aops python-dotenv
    AGENTOPS_API_KEY=aops_...
"""

import os
import time
import textwrap
from dotenv import load_dotenv

load_dotenv()

import aops
from aops import pull

aops.init(api_key=os.getenv("AGENTOPS_API_KEY"), poll_interval=10)  # 10s for demo

AGENT_NAME = "test-agent"
CHAIN_NAME = "user-input"


# ── Example 1: pull() loop — raw str 비교 ─────────────────────────────────────
# pull()은 캐시에서 읽고, 백그라운드 poller가 변경 시 캐시를 갱신.

def example_live_update_pull():
    interval = aops._config._config.poll_interval
    print(f"=== Example 1: Live update (pull) — polling every {interval}s ===")
    print("AOps 웹 UI에서 프롬프트를 수정하면 [UPDATED]가 표시됩니다.\n")

    last = None
    while True:
        try:
            current = pull(f"{AGENT_NAME}/{CHAIN_NAME}")
            preview = textwrap.shorten(current, width=80, placeholder="...")
            if last is None:
                print(f"[INIT]    {preview}")
            elif current != last:
                print(f"[UPDATED] {preview}")
            else:
                print(f"[OK]      (no change)")
            last = current
        except Exception as e:
            print(f"[ERROR]   {e}")
        time.sleep(5)


# ── Example 2: @chain_prompt 함수 데코레이터 loop ─────────────────────────────
# 데코레이터는 매 호출마다 캐시를 읽으므로 polling 업데이트가 자동 반영됨.

def example_live_update_decorator():
    from aops.langchain import chain_prompt
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini")

    @chain_prompt(AGENT_NAME, CHAIN_NAME)
    def answer(prompt, user_input: str) -> str:
        return (
            ChatPromptTemplate.from_messages([
                prompt,
                HumanMessagePromptTemplate.from_template("{user_input}"),
            ])
            | llm
            | StrOutputParser()
        ).invoke({"user_input": user_input})

    interval = aops._config._config.poll_interval
    print(f"\n=== Example 2: Live update (@chain_prompt) — polling every {interval}s ===")
    print("AOps 웹 UI에서 프롬프트를 수정하면 [UPDATED]가 표시됩니다.\n")

    last = None
    while True:
        try:
            current = pull(f"{AGENT_NAME}/{CHAIN_NAME}")
            if last is None:
                print(f"[INIT]    {textwrap.shorten(current, width=60, placeholder='...')}")
            elif current != last:
                print(f"[UPDATED] {textwrap.shorten(current, width=60, placeholder='...')}")
                result = answer(user_input="Test question.")
                print(f"          → {textwrap.shorten(result, width=60, placeholder='...')}")
            else:
                print(f"[OK]      (no change)")
            last = current
        except Exception as e:
            print(f"[ERROR]   {e}")
        time.sleep(5)


# ── Run ───────────────────────────────────────────────────────────────────────
# 실행할 예시의 주석을 해제하세요.

if __name__ == "__main__":
    example_live_update_pull()
    # example_live_update_decorator()  # LangChain 설치 필요: pip install "aops[langchain]" langchain-openai
