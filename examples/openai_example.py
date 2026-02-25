"""
OpenAI SDK example — aops raw pull()
======================================
from aops import pull  →  str  →  OpenAI SDK에 직접 전달

Before running:
    pip install aops openai python-dotenv
    AGENTOPS_API_KEY=aops_...  OPENAI_API_KEY=sk-...
"""

import os
from dotenv import load_dotenv

load_dotenv()

import aops
from aops import pull

aops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

from openai import OpenAI

AGENT_NAME = "test-agent"
CHAIN_NAME = "user-input"
MODEL = "gpt-4o-mini"

client = OpenAI()


# ── Example 1: 기본 사용 ───────────────────────────────────────────────────────

def example_basic():
    print("=== Example 1: raw pull() + OpenAI ===")
    system_prompt = pull(f"{AGENT_NAME}/{CHAIN_NAME}")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Hello, how's the weather today?"},
        ],
    )
    print(response.choices[0].message.content)


# ── Example 2: 특정 버전 고정 ──────────────────────────────────────────────────

def example_pinned_version():
    print("\n=== Example 2: pull(version=1) + OpenAI ===")
    system_prompt = pull(f"{AGENT_NAME}/{CHAIN_NAME}", version=1)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "What's the weather like tomorrow?"},
        ],
    )
    print(response.choices[0].message.content)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    example_basic()
    example_pinned_version()
