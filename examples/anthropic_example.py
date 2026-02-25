"""
Anthropic SDK example — aops raw pull()
=========================================
from aops import pull  →  str  →  Anthropic SDK에 직접 전달

Before running:
    pip install aops anthropic python-dotenv
    AGENTOPS_API_KEY=aops_...  ANTHROPIC_API_KEY=sk-ant-...
"""

import os
from dotenv import load_dotenv

load_dotenv()

import aops
from aops import pull

aops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

from anthropic import Anthropic

AGENT_NAME = "test-agent"
CHAIN_NAME = "user-input"
MODEL = "claude-haiku-4-5-20251001"

client = Anthropic()


# ── Example 1: 기본 사용 ───────────────────────────────────────────────────────

def example_basic():
    print("=== Example 1: raw pull() + Anthropic ===")
    system_prompt = pull(f"{AGENT_NAME}/{CHAIN_NAME}")

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": "Hello, how's the weather today?"},
        ],
    )
    print(message.content[0].text)


# ── Example 2: 특정 버전 고정 ──────────────────────────────────────────────────

def example_pinned_version():
    print("\n=== Example 2: pull(version=1) + Anthropic ===")
    system_prompt = pull(f"{AGENT_NAME}/{CHAIN_NAME}", version=1)

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": "What's the weather like tomorrow?"},
        ],
    )
    print(message.content[0].text)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    example_basic()
    example_pinned_version()
