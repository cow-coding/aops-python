"""
aops — usage examples
======================
각 예시 파일을 직접 실행하세요.

examples/
  openai_example.py     raw pull() + OpenAI SDK
  anthropic_example.py  raw pull() + Anthropic SDK
  langchain_example.py  aops.langchain — pull(), @chain_prompt
  live_updates.py       백그라운드 polling / 라이브 업데이트 감지

사전 준비:
  AGENTOPS_API_KEY=aops_...   (AOps UI → Agent → API Keys)
  OPENAI_API_KEY=sk-...       (openai_example, langchain_example)
  ANTHROPIC_API_KEY=sk-ant-... (anthropic_example)

실행 예시:
  python examples/openai_example.py
  python examples/langchain_example.py
"""
