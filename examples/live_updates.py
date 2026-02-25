"""
Live update examples — aops polling
======================================
Demonstrates automatic prompt change detection via background polling.
Edit a prompt in the AOps web UI and the change will be reflected
within POLL_INTERVAL seconds.

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

aops.init(api_key=os.getenv("AGENTOPS_API_KEY"), agent="test-agent", poll_interval=10)  # 10s for demo

CHAIN_NAME = "user-input"


# ── Example 1: pull() loop — raw str comparison ───────────────────────────────
# pull() reads from cache; the background poller refreshes the cache on change.

def example_live_update_pull():
    interval = aops._config._config.poll_interval
    print(f"=== Example 1: Live update (pull) — polling every {interval}s ===")
    print("Edit the prompt in the AOps web UI. [UPDATED] will appear when a change is detected.\n")

    last = None
    while True:
        try:
            current = pull(CHAIN_NAME)
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


# ── Example 2: @chain_prompt function decorator loop ──────────────────────────
# The decorator reads from cache on every call, so polling updates are
# reflected automatically.

def example_live_update_decorator():
    from aops.langchain import chain_prompt
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini")

    @chain_prompt(CHAIN_NAME)
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
    print("Edit the prompt in the AOps web UI. [UPDATED] will appear when a change is detected.\n")

    last = None
    while True:
        try:
            current = pull(CHAIN_NAME)
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
# Uncomment the example you want to run.

if __name__ == "__main__":
    example_live_update_pull()
    # example_live_update_decorator()  # requires: pip install "aops[langchain]" langchain-openai
