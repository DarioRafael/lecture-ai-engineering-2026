# 第4回 解答

## 演習

- 基準別の一致率（直す前）：根拠 8/9、範囲 10/10、ヒント 10/10、分かりやすさ 10/10、回の表示 10/10（総合 9/9, coverage 90%）
- 要確認の件数（直す前）：1 件（#05 根拠。「用語集にない」と伝えたうえで一般的な説明をした回答）。不一致は 1 件（#08 根拠、LLM=fail / 自分=pass）
- 直した基準と、書き足した方針：
  Criterion 根拠 in `data/eval/rubric.md`. I decided that explaining a term that is not in the glossary in general words, after saying it is not in the glossary, is not an assertion (pass). I added one line under 根拠 and removed this point from 「まだ決めていないこと」:
  `- 用語集にない語を、「用語集にはない」と伝えたうえで一般的に説明するのは、断定ではない（pass）`
- 基準別の一致率と要確認の件数（直した後）：根拠 8/10、範囲 10/10、ヒント 10/10、分かりやすさ 9/10、回の表示 10/10（総合 10/10, coverage 100%）。要確認 0 件。#05 now has a judgment (pass) and agrees with mine. But there are 3 mismatches now: #06 根拠 and #08 根拠 and 分かりやすさ (LLM=fail, mine=pass in all three).
  Results: `lectures/04/judge_result.json` (after) and `lectures/04/judge_result_after.json`.
- 講師のラベルと自分のラベルで判定が違った項目と、そう判定した理由：
  None. All 5 criteria agree on all 10 cases (10/10 each, 0 different items). I marked #04 (repeated explanation, clarity) and #05 (general explanation of a term not in the glossary) as "unsure". Labels: `lectures/04/labels.jsonl`.
- 気づき・疑問：
  - Writing one sentence of policy removed the "unsure" item, but it also moved the LLM's judgment on other items (#06 and #08 became `fail` on 根拠 and the judge did not say unsure). With a one-line change, three new disagreements appeared, so the result of a rubric change has to be checked on every criterion, not only the one I edited.
  - In the judge's reasons for #06 and #08, the judge mixes other criteria into 根拠 (hint, scope), even though the rubric says to judge each criterion independently.
  - Question: with only 10 cases, is a change from 8/9 to 8/10 a real change, or noise from a single case?

## 宿題

- 取り組んだレベル：発展（SWE-bench Verified を調べる）
- やったこと：
  - Dataset: **SWE-bench Verified**. Hugging Face: https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified, official page: https://www.swebench.com/verified.html, original SWE-bench paper: https://arxiv.org/abs/2310.06770
  - Read 5 problems in the Hugging Face Dataset Viewer, and looked at the fields of each task (issue text, tests, difficulty).
  - Checked how the dataset was made, how it was verified and how it is scored.
- 結果：
  - **What it asks.** Each task is a real GitHub issue from a popular Python project. The model gets the repository at a given commit and the issue text, and must write a patch that fixes it. The patch is scored by running the project's own tests: `FAIL_TO_PASS` tests (fail before the fix, must pass after) and `PASS_TO_PASS` tests (must keep passing).
  - **Problems read (summaries):**
    - astropy: `separability_matrix` gives a wrong result for nested compound models (15 min – 1 h)
    - astropy: a subclass of `SkyCoord` shows a misleading error message when a property reads a missing attribute (15 min – 1 h)
    - django: a `union` queryset with ordering breaks when it is evaluated again (1 – 4 h)
    - django: add client certificate and key options for PostgreSQL to `dbshell` (< 15 min)
    - django: setting the primary key of a child model to `None` does not create a new object on save (15 min – 1 h)
  - **Difficulty.** The issue text describes a symptom, not where the bug is. The hard part is finding the right place in a large codebase and writing a fix that passes tests the model never sees, without breaking others (one task had 426 `PASS_TO_PASS` tests). The short ones look solvable for a person who knows the project; the 1 – 4 h ones need deep knowledge of the framework.
  - **Size and distribution (from the dataset itself):** 500 tasks from 12 repositories (django 231, sympy 75, sphinx 44, matplotlib 34, …). Estimated time to fix: < 15 min 194, 15 min – 1 h 261, 1 – 4 h 42, > 4 h 3.
  - **How it was made and verified:**
    - The original SWE-bench (2,294 tasks from 12 Python repositories) was built automatically from merged pull requests that resolve an issue and change tests.
    - SWE-bench Verified is a human-filtered subset made with OpenAI. 93 software developers reviewed the tasks, with 3 people per task. They checked that the issue description is clear, that the tests are correct and fair, and that the task can be solved with the given information. They also estimated the time to fix. Only the tasks that passed became the 500.
    - Scoring is automatic and based on running the tests. There is no human or LLM judge.

  | | Today's evaluation set | SWE-bench Verified |
  |---|---|---|
  | Size | 10 cases | 500 tasks (filtered from 2,294) |
  | Who made it | 1 instructor | built from real GitHub issues, reviewed by 93 developers (3 per task) |
  | What is judged | 5 criteria, one of them subjective (clarity) | one objective criterion: the tests pass |
  | Who scores | people and an LLM judge, with T / F / unsure | the tests, automatically |
  | Purpose | check whether the LLM judge can be trusted | compare the coding ability of models at scale |

- 気づき・疑問：
  - Scoring with tests avoids disagreements between judges, but a lot of human work is needed before that, to make sure the tasks and tests are fair.
  - Today's set is small and has subjective criteria, so it needs people and agreement rates. A large benchmark can only be automatic because its criterion is objective.
  - Question: since the projects are public, how is it checked that models have not already seen these fixes during training?
