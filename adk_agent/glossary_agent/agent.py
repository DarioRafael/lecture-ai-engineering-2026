"""第3回 宿題（発展 a）: 演習のエージェントを ADK で組み立て直したもの。

指示（INSTRUCTIONS）とツール（app/tools.py の関数）は演習と同じものをそのまま使い、
エージェントを組み立てる部分だけを ADK で書く。

実行（リポジトリの直下で）:
    PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent
"""

from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS
from app.config import MODEL

root_agent = Agent(
    model=MODEL,
    name="glossary_agent",
    instruction=INSTRUCTIONS,
    tools=[tools.search_glossary, tools.get_lecture_summary, tools.make_quiz],
)
