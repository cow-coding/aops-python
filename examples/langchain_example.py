"""
LangChain integration example — aops.langchain
=================================================
aops.langchain.pull()  →  SystemMessagePromptTemplate  →  LangChain chain
AopsCallbackHandler  →  auto-logs LLM input/output

Before running:
    pip install "aops[langchain]" langchain-openai python-dotenv
    AGENTOPS_API_KEY=aops_...  OPENAI_API_KEY=sk-...
"""

import os
from dotenv import load_dotenv

load_dotenv()

import aops
from aops.langchain import pull, chain_prompt, AopsCallbackHandler
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_openai import ChatOpenAI

aops.init(api_key=os.getenv("AGENTOPS_API_KEY"), agent="test-agent")

MODEL = "gpt-4o-mini"

handler = AopsCallbackHandler()
llm = ChatOpenAI(model=MODEL, callbacks=[handler])


# ── Example 1: pull() + AopsCallbackHandler ───────────────────────────────────

def example_pull():
    print("=== Example 1: aops.langchain.pull() + AopsCallbackHandler ===")
    with aops.run():
        prompt = pull("user-input")

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


# ── Example 2: @chain_prompt function decorator ───────────────────────────────

@chain_prompt("user-input")
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
    print("\n=== Example 2: @chain_prompt function decorator ===")
    with aops.run():
        result = answer(user_input="What's the weather like tomorrow?")
        print(result)


# ── Example 3: @chain_prompt class decorator ──────────────────────────────────

@chain_prompt("user-input")
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
    print("\n=== Example 3: @chain_prompt class decorator ===")
    with aops.run():
        agent = WeatherAgent()
        result = agent.run(user_input="How's the weather in Busan this weekend?")
        print(result)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    example_pull()
    example_function_decorator()
    example_class_decorator()
