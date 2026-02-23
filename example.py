"""
aops — usage examples
=====================
Step-by-step examples from basic usage to live updates.

Before running:
    1. Start the AOps backend (http://localhost:8000)
    2. Issue an API key from the AOps UI and paste it into API_KEY below
    3. pip install python-dotenv langchain-openai
"""

import time
import textwrap
from dotenv import load_dotenv

load_dotenv()

import aops
from aops.langchain import chain_prompt, pull
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY = "aops_aHR0cDovL2xvY2FsaG9zdDo4MDAw_9WGQ-SGP2J2WpFeXBmQ5u50b34ZvhwlhaGaQXJoZJzU"
AGENT_NAME = "test-agent"
CHAIN_NAME = "user-input"

aops.init(api_key=API_KEY, poll_interval=10)  # 10s for testing (default: 60s)


# ── Example 1: pull() — basic usage ───────────────────────────────────────────
# Fetch the prompt and build a LangChain chain directly.

def example_pull():
    print("=== Example 1: pull() ===")
    prompt = pull(f"{AGENT_NAME}/{CHAIN_NAME}")

    chain = (
        ChatPromptTemplate.from_messages([
            prompt,
            HumanMessagePromptTemplate.from_template("{user_input}"),
        ])
        | ChatOpenAI(model="gpt-4o-mini")
        | StrOutputParser()
    )

    result = chain.invoke({"user_input": "Hello, how's the weather today?"})
    print(result)


# ── Example 2: @chain_prompt function decorator ───────────────────────────────
# Reads the prompt from cache on every call and builds the chain fresh.

@chain_prompt(AGENT_NAME, CHAIN_NAME)
def answer(prompt: SystemMessagePromptTemplate, user_input: str) -> str:
    return (
        ChatPromptTemplate.from_messages([
            prompt,
            HumanMessagePromptTemplate.from_template("{user_input}"),
        ])
        | ChatOpenAI(model="gpt-4o-mini")
        | StrOutputParser()
    ).invoke({"user_input": user_input})

def example_function_decorator():
    print("\n=== Example 2: @chain_prompt function decorator ===")
    result = answer(user_input="What's the weather like tomorrow?")
    print(result)


# ── Example 3: @chain_prompt class decorator ──────────────────────────────────
# Fetches the prompt once at __init__ and bakes it into the chain.
# Best for performance-sensitive agents where the prompt changes infrequently.
# Note: to pick up a prompt update, re-instantiate the class.

@chain_prompt(AGENT_NAME, CHAIN_NAME)
class WeatherAgent:
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

def example_class_decorator():
    print("\n=== Example 3: @chain_prompt class decorator ===")
    agent = WeatherAgent()
    result = agent.run(user_input="How's the weather in Busan this weekend?")
    print(result)


# ── Example 4: Live Update — pull() loop ──────────────────────────────────────
# Verifies that background polling works.
# Edit the prompt in the web UI (http://localhost:3000) and the change will be
# reflected within POLL_INTERVAL seconds.

def summarize(prompt) -> str:
    return textwrap.shorten(prompt.prompt.template, width=80, placeholder="...")

def example_live_update_pull():
    print(f"\n=== Example 4: Live Update (pull) — polling every {aops._config._config.poll_interval}s ===")
    print("Edit the prompt in the web UI. [UPDATED] will appear when a change is detected.\n")
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
        time.sleep(5)


# ── Example 5: Live Update — function decorator loop ─────────────────────────
# The function decorator reads from cache on every call, so polling updates
# are reflected automatically. Here we use pull() to detect changes and
# answer() to execute with the updated prompt.

def example_live_update_decorator():
    print(f"\n=== Example 5: Live Update (@chain_prompt function) ===")
    print("Edit the prompt in the web UI.\n")
    last_content = None
    while True:
        try:
            # detect prompt change via pull()
            prompt = pull(f"{AGENT_NAME}/{CHAIN_NAME}")
            current = prompt.prompt.template
            if last_content is None:
                print(f"[INIT]    {summarize(prompt)}")
            elif current != last_content:
                print(f"[UPDATED] {summarize(prompt)}")
                # function decorator reads the new prompt from cache
                result = answer(user_input="Test question.")
                print(f"          → {textwrap.shorten(result, width=60, placeholder='...')}")
            else:
                print(f"[OK]      {summarize(prompt)}")
            last_content = current
        except Exception as e:
            print(f"[ERROR]   {e}")
        time.sleep(5)


# ── Run ───────────────────────────────────────────────────────────────────────
# Uncomment the example you want to run.

# example_pull()                  # basic pull() usage
# example_function_decorator()    # function decorator
# example_class_decorator()       # class decorator (fixed prompt)
example_live_update_pull()        # live update via pull() loop
# example_live_update_decorator() # live update via function decorator loop
