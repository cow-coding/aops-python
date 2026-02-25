"""
Anthropic SDK example — aops raw pull()
=========================================
from aops import pull  →  str  →  pass directly to Anthropic SDK

Before running:
    pip install aops anthropic python-dotenv
    AGENTOPS_API_KEY=aops_...  ANTHROPIC_API_KEY=sk-ant-...
"""

import os
from dotenv import load_dotenv

load_dotenv()

import aops
from aops import pull

aops.init(api_key=os.getenv("AGENTOPS_API_KEY"), agent="test-agent")

from anthropic import Anthropic

MODEL = "claude-haiku-4-5-20251001"

client = Anthropic()


# ── Example 1: basic usage ────────────────────────────────────────────────────

def example_basic():
    print("=== Example 1: raw pull() + Anthropic ===")
    system_prompt = pull("user-input")

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": "Hello, how's the weather today?"},
        ],
    )
    print(message.content[0].text)


# ── Example 2: pin a specific version ────────────────────────────────────────

def example_pinned_version():
    print("\n=== Example 2: pull(version=1) + Anthropic ===")
    system_prompt = pull("user-input", version=1)

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
