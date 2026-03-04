"""
OpenAI SDK example — aops.wrap()
==================================
from aops import wrap  →  proxy client that auto-logs I/O to AgentOps

Before running:
    pip install aops openai python-dotenv
    AGENTOPS_API_KEY=aops_...  OPENAI_API_KEY=sk-...
"""

import os
from dotenv import load_dotenv

load_dotenv()

import aops
from aops import pull, wrap
import openai

aops.init(api_key=os.getenv("AGENTOPS_API_KEY"), agent="test-agent")

MODEL = "gpt-4o-mini"

client = wrap(openai.OpenAI())


# ── Example 1: wrap() — auto-log input/output ─────────────────────────────────

def example_wrap():
    print("=== Example 1: wrap() + aops.run() ===")
    with aops.run():
        system_prompt = pull("user-input")

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Hello, how's the weather today?"},
            ],
        )
        print(response.choices[0].message.content)


# ── Example 2: pin a specific version ────────────────────────────────────────

def example_pinned_version():
    print("\n=== Example 2: pull(version=1) + wrap() ===")
    with aops.run():
        system_prompt = pull("user-input", version=1)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "What's the weather like tomorrow?"},
            ],
        )
        print(response.choices[0].message.content)


# ── Example 3: @aops.trace decorator ─────────────────────────────────────────

@aops.trace("user-input")
def classify(text: str) -> str:
    system_prompt = pull("user-input")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content

def example_trace_decorator():
    print("\n=== Example 3: @aops.trace decorator ===")
    with aops.run():
        result = classify("Is this a question?")
        print(result)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    example_wrap()
    example_pinned_version()
    example_trace_decorator()
