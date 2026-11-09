# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：
  Same question: 「AIE2026の講座の宿題にある「3レベル」とは何ですか？」. In Lecture 1, `app.ask` (no tools) invented a generic "Level 1 basic / Level 2 applied / Level 3 advanced" scheme, and one run suggested solving the levels in order. The agent first called `search_glossary('3レベル')` and answered exactly from the glossary: 基礎・実装・発展, doing any one completes the homework, and it is generally not graded. It ended with 「（関連回：第1回）」 as INSTRUCTIONS ask.
- `--trace` で見えたツール呼び出し（ツール名と引数）：
  - 「3レベル」: `search_glossary({'query': '3レベル'})`
  - 「LoRAとQLoRAの違いは？」: `search_glossary({'query': 'LoRA'})`, then `search_glossary({'query': 'QLoRA'})`. One term per call, as the docstring says.
  - 「第2回の内容から確認問題を1問出して」: `make_quiz({'lecture': 2})`
  - 「RAGとは何ですか？」: `search_glossary({'query': 'RAG'})` twice with the same argument. RAG is not a glossary term. The search returned 「ファインチューニング」 because its definition mentions RAG.
- 1つの質問での LLM 呼び出し回数（`requests`）：
  2 for the first three questions (one request to choose the tool, one to write the answer). 3 for the RAG question, because of the repeated search. Input / output tokens: 981 / 136, 1394 / 189, 920 / 47, 1650 / 120.
- 追加したツールと、docstring に書いた説明：
  `make_quiz(lecture: int) -> str` in `app/tools.py`, registered with `agent.tool_plain(tools.make_quiz)`. Docstring: 「指定した回（1始まりの整数）の用語から確認問題を1問作り、問題と答えを返す。「第2回の確認問題を出して」のように、復習用の問題を求められたときに使う。answer は答え合わせ用なので、出題するときは question だけを見せる。」 It picks one term of that lecture with `random.choice` and returns `{"question": "「…」の意味は？", "answer": definition}` as JSON. If the lecture has no terms (for example `lecture=0`), it returns a message with the lectures that do have terms. `--list-tools` shows the 3 tools, and `uv run pytest -q` gives 11 passed. In the run above, the agent showed only the question (「Hugging Face Hub」の意味は？) and kept the answer hidden.

## 宿題

- 取り組んだレベル：発展（a）ADK で作り直す
- やったこと：
  - Created `adk_agent/glossary_agent/__init__.py` (`from . import agent`) and `adk_agent/glossary_agent/agent.py`. The ADK agent reuses `INSTRUCTIONS` from `app/agent.py` and the same three tools from `app/tools.py` (`search_glossary`, `get_lecture_summary`, `make_quiz`), with the same model (`gemini-3.5-flash-lite`). Nothing in `app/` was changed for this part.
  - Ran it with `adk run` (google-adk 2.14.0 through `uv run --with google-adk`), one question per run, with `--in_memory` (no local session files) and `--jsonl` (structured events, to see the function calls). On Windows PowerShell the command is `$env:PYTHONPATH="."; uv run --with google-adk adk run adk_agent/glossary_agent`.
  - Asked the same 4 questions to the exercise agent (`python -m app.agent --trace`) and to the ADK agent. All outputs are in `lectures/03/traces/`.
- 結果：

  **Code: how the instructions and tools are passed**

  | | Pydantic AI (`app/agent.py`) | ADK (`adk_agent/glossary_agent/agent.py`) |
  |---|---|---|
  | Instructions | `Agent(instructions=INSTRUCTIONS)` | `Agent(instruction=INSTRUCTIONS)` (singular) |
  | Tools | registered one by one after creating the agent: `agent.tool_plain(func)` | a list in the constructor: `tools=[func, ...]` |
  | Model | passed when running: `run_sync(..., model=build_model())`, so the tests can swap in `TestModel` | fixed in the constructor as a string: `model="gemini-3.5-flash-lite"` |
  | Name | not needed | `name="glossary_agent"` is required, and ADK adds `You are an agent. Your internal name is "glossary_agent".` after the instructions (seen with `--log_level debug`) |
  | Running | own CLI (`main()`, argparse, `--trace` written by hand) | `adk run` CLI (interactive or one query), with sessions handled by ADK |
  | Tool return value | the string is passed as it is | wrapped in a dict: `{"result": "..."}` |
  | Seeing tool calls | `--trace` (`print_trace`) | `--jsonl` events (`functionCall` / `functionResponse`) |
  | API key | `GoogleProvider(api_key=get_api_key())` | read from the `GEMINI_API_KEY` environment variable |

  The ADK file is about 10 lines of code: the imports and one `Agent(...)` call. The Pydantic AI side needs the agent plus the CLI code around it.

  **Answers to the same questions**

  | Question | Pydantic AI: tool calls, `requests`, tokens (in / out) | ADK: tool calls, requests, tokens (in / out) |
  |---|---|---|
  | 3レベル | `search_glossary('3レベル')`, 2, 981 / 136 | same call, 2, 1107 / 124 |
  | LoRAとQLoRAの違い | `search_glossary('LoRA')`, `search_glossary('QLoRA')`, 2, 1394 / 189 | same calls, 2, 1518 / 183 |
  | 第2回の確認問題 | `make_quiz(2)` → 「Hugging Face Hub」, 2, 920 / 47 | `make_quiz(2)` → 「QLoRA」, 2, 1083 / 51 |
  | RAGとは | `search_glossary('RAG')` × 2, 3, 1650 / 120 | `search_glossary('RAG')` × 1, 2, 1090 / 89 |

  - For the first three questions both agents chose the same tools with the same arguments. The answers had almost the same content: the glossary definitions, and the related lecture at the end.
  - Quiz: both showed only the question and hid the answer, as the docstring says. The term was different because `make_quiz` picks a term at random.
  - RAG: both said it is not in the glossary, then quoted the 「ファインチューニング」 definition that mentions RAG. The Pydantic AI run searched twice with the same argument, so it used one more request.
  - On the first three questions ADK used about 120–165 more input tokens, which fits the extra system line and the wrapped tool results.
- 気づき・疑問：
  - The behavior comes from the model, the instructions and the tool docstrings, not from the framework. With the same `INSTRUCTIONS` and functions, both frameworks chose the same tools and arguments and gave almost the same answers.
  - The differences are in the code around the agent. ADK is shorter to declare and gives a CLI, sessions and event logs for free. Pydantic AI keeps the model outside the agent, which is what makes the API-free tests with `TestModel` easy.
  - ADK silently adds text to the system prompt, so what the model sees is not exactly `INSTRUCTIONS`. When comparing agents, it is worth checking the real request.
  - The repeated search for RAG happened in one run only, so it is not clear whether it is random or related to the framework.
  - Questions: How are ADK agents tested without calling the API, like `TestModel` does? How does ADK's session memory behave in a multi-turn conversation compared with Pydantic AI's `message_history`?
