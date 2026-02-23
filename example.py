"""
aops — usage examples
=====================
AOps Python client for loading LangChain prompts from the AOps backend.

Prerequisites
-------------
1. AOps backend running  : http://localhost:8000
2. API key issued from the AOps UI (Agent detail page → New API Key)
3. .env file with OPENAI_API_KEY (for chain invocation examples)

Install
-------
    pip install aops

.env
----
    AGENTOPS_API_KEY=aops_...
    OPENAI_API_KEY=sk-...
"""

from dotenv import load_dotenv

load_dotenv()

import aops

# aops reads AGENTOPS_API_KEY from .env automatically after load_dotenv().
# To override or set explicitly:
API_KEY = "aops_aHR0cDovL2xvY2FsaG9zdDo4MDAw_9WGQ-SGP2J2WpFeXBmQ5u50b34ZvhwlhaGaQXJoZJzU"
aops.init(api_key=API_KEY)

from aops.langchain import chain_prompt, pull  # noqa: F401 — pull shown in commented examples
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_openai import ChatOpenAI

# ── 1. pull() — load a prompt ─────────────────────────────────────────────────
# Returns a SystemMessagePromptTemplate combining the chain's persona + content.
# ref format: "agent-name/chain-name"

# system_prompt = pull("my-agent/my-chain")           # latest version
# system_prompt = pull("my-agent/my-chain", version=2)  # pinned version
#
# # ── 2. Build and invoke a chain ───────────────────────────────────────────────
# # SystemMessagePromptTemplate defines the agent's behavior.
# # Combine it with a HumanMessage to form a complete conversation prompt,
# # then pipe into the LLM.
#
# chat_prompt = ChatPromptTemplate.from_messages([
#     system_prompt,
#     HumanMessagePromptTemplate.from_template("{user_input}"),
# ])
#
# llm = ChatOpenAI(model="gpt-4o-mini")
# chain = chat_prompt | llm | StrOutputParser()
#
# result = chain.invoke({"user_input": "Hello, what can you do?"})
# print(result)

# ── 3. @chain_prompt — function decorator ────────────────────────────────────
# Fetches the prompt once and injects it as the first argument.
# Build the chain inside the function and invoke with user arguments.

@chain_prompt("my-agent", "my-chain")
def answer(prompt: SystemMessagePromptTemplate, user_input: str) -> str:
    chat_prompt = ChatPromptTemplate.from_messages([
        prompt,
        HumanMessagePromptTemplate.from_template("{user_input}"),
    ])
    return (chat_prompt | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()).invoke(
        {"user_input": user_input}
    )


# result = answer(user_input="What is AOps?")
# print(result)

# ── 4. @chain_prompt — class decorator ───────────────────────────────────────
# Injects the prompt into __init__ as the first argument after self.
# Build the chain once at construction time and reuse it across calls.

@chain_prompt("test-agent", "user-input")
class MyAgent:
    def __init__(self, prompt: SystemMessagePromptTemplate) -> None:
        chat_prompt = ChatPromptTemplate.from_messages([
            prompt,
            HumanMessagePromptTemplate.from_template("{user_input}"),
        ])
        print(chat_prompt)
        self.chain = chat_prompt | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()

    def run(self, user_input: str) -> str:
        return self.chain.invoke({"user_input": user_input})


agent = MyAgent()
user_input = input("채팅: ")
result = agent.run(user_input=user_input)
print(result)
