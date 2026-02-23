"""
aops — 프롬프트 로딩 패턴 및 polling 테스트
============================================

패턴 선택 가이드
----------------
aops는 세 가지 사용 패턴을 제공합니다. 목적에 맞게 선택하세요.

┌─────────────────────────────┬──────────────┬──────────────────────────────────┐
│ 패턴                        │ 프롬프트 갱신 │ 적합한 상황                       │
├─────────────────────────────┼──────────────┼──────────────────────────────────┤
│ pull() 직접 호출            │ O (실시간)   │ 매번 최신 프롬프트가 필요한 경우   │
│ @chain_prompt 함수 데코레이터│ O (실시간)   │ 호출마다 프롬프트를 갱신하고 싶을 때│
│ @chain_prompt 클래스 데코레이터│ X (고정)   │ 성능 중시, 프롬프트 변경 빈도 낮음 │
└─────────────────────────────┴──────────────┴──────────────────────────────────┘

클래스 데코레이터는 __init__ 시점에 프롬프트를 1회 fetch하여 고정합니다.
프롬프트를 실시간으로 반영해야 한다면 pull() 또는 함수 데코레이터를 사용하세요.

실행 방법:
    python example.py

polling 테스트 방법:
    1. 이 스크립트를 실행합니다.
    2. 웹 UI (http://localhost:3000) 에서 test-agent > user-input 프롬프트를 수정하고 커밋합니다.
    3. 최대 POLL_INTERVAL 초 안에 "[UPDATED]" 메시지와 함께 새 프롬프트가 출력됩니다.
"""

import time
import textwrap
from dotenv import load_dotenv

load_dotenv()

import aops
from aops.langchain import chain_prompt, pull
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

# ── 설정 ──────────────────────────────────────────────────────────────────────
API_KEY = "aops_aHR0cDovL2xvY2FsaG9zdDo4MDAw_9WGQ-SGP2J2WpFeXBmQ5u50b34ZvhwlhaGaQXJoZJzU"
AGENT_NAME = "test-agent"
CHAIN_NAME = "user-input"
POLL_INTERVAL = 10   # 테스트용 10초 (기본값 60초)
CHECK_EVERY = 5      # 5초마다 출력

aops.init(api_key=API_KEY, poll_interval=POLL_INTERVAL)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────
def summarize(prompt) -> str:
    return textwrap.shorten(prompt.prompt.template, width=80, placeholder="...")


# ── Case 1: pull() — polling 반영 O ──────────────────────────────────────────
# 매 루프마다 캐시에서 읽기 때문에 polling으로 갱신된 내용이 바로 반영됩니다.

def test_pull():
    print(f"\n[pull()] Watching '{AGENT_NAME}/{CHAIN_NAME}' — polling every {POLL_INTERVAL}s")
    print("웹 UI에서 프롬프트를 수정하면 반영됩니다.\n")
    last_content = None
    while True:
        try:
            prompt = pull(f"{AGENT_NAME}/{CHAIN_NAME}")
            current = prompt.prompt.template
            if last_content is None:
                print(f"[INIT]    {summarize(prompt)}")
            elif current != last_content:
                print(f"[UPDATED] {summarize(prompt)}")
            else:
                print(f"[OK]      {summarize(prompt)}")
            last_content = current
        except Exception as e:
            print(f"[ERROR]   {e}")
        time.sleep(CHECK_EVERY)


# ── Case 2: @chain_prompt 함수 데코레이터 — polling 반영 O ───────────────────
# 함수 호출마다 pull()을 실행하므로 polling으로 갱신된 캐시가 반영됩니다.

@chain_prompt(AGENT_NAME, CHAIN_NAME)
def get_prompt(prompt: SystemMessagePromptTemplate) -> SystemMessagePromptTemplate:
    return prompt

def test_function_decorator():
    print(f"\n[@chain_prompt 함수] Watching '{AGENT_NAME}/{CHAIN_NAME}'\n")
    last_content = None
    while True:
        try:
            prompt = get_prompt()
            current = prompt.prompt.template
            if last_content is None:
                print(f"[INIT]    {summarize(prompt)}")
            elif current != last_content:
                print(f"[UPDATED] {summarize(prompt)}")
            else:
                print(f"[OK]      {summarize(prompt)}")
            last_content = current
        except Exception as e:
            print(f"[ERROR]   {e}")
        time.sleep(CHECK_EVERY)


# ── Case 3: @chain_prompt 클래스 데코레이터 — polling 반영 X ─────────────────
# __init__ 시 한 번만 fetch하여 self.chain에 고정됩니다.
# 프롬프트 변경을 반영하려면 인스턴스를 다시 생성해야 합니다.

@chain_prompt(AGENT_NAME, CHAIN_NAME)
class PromptAgent:
    def __init__(self, prompt: SystemMessagePromptTemplate) -> None:
        self._template = prompt.prompt.template  # 생성 시점에 고정됨

    def current_template(self) -> str:
        return self._template

def test_class_decorator():
    print(f"\n[@chain_prompt 클래스] Watching '{AGENT_NAME}/{CHAIN_NAME}'")
    print("※ 클래스 데코레이터는 인스턴스 생성 시점의 프롬프트를 사용합니다.")
    print("  변경 반영이 필요하면 인스턴스를 재생성해야 합니다.\n")
    agent = PromptAgent()
    last_content = agent.current_template()
    print(f"[INIT]    {textwrap.shorten(last_content, width=80, placeholder='...')}")
    while True:
        time.sleep(CHECK_EVERY)
        current = agent.current_template()
        # 인스턴스를 재생성하면 갱신된 프롬프트를 사용할 수 있습니다:
        # agent = PromptAgent()
        # current = agent.current_template()
        if current != last_content:
            print(f"[UPDATED] {textwrap.shorten(current, width=80, placeholder='...')}")
            last_content = current
        else:
            print(f"[NO CHANGE] (재생성 없이는 변경 안 됨)")


# ── 실행 ──────────────────────────────────────────────────────────────────────
# 테스트할 케이스를 선택하세요.
test_pull()
# test_function_decorator()
# test_class_decorator()
