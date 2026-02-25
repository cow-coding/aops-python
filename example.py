"""
aops — usage examples
======================
Run each example file directly.

examples/
  openai_example.py     raw pull() + OpenAI SDK
  anthropic_example.py  raw pull() + Anthropic SDK
  langchain_example.py  aops.langchain — pull(), @chain_prompt
  live_updates.py       background polling / live update detection

Setup:
  AGENTOPS_API_KEY=aops_...    (AOps UI → Agent → API Keys)
  OPENAI_API_KEY=sk-...        (openai_example, langchain_example)
  ANTHROPIC_API_KEY=sk-ant-... (anthropic_example)

Run:
  python examples/openai_example.py
  python examples/langchain_example.py
"""
