# 第5回 解答

## 演習

- 回答モデル（実行時の`[model]`）：`gemini-3.5-flash-lite`（温度などは既定のまま）
- 比較した質問：
  - **Q1（基本）**: 第2回の説明では、LoRAは何を固定し何を学習しますか？ QLoRAは何を加えますか？
  - Q2（複数ページ）: 第3回の例では、コンパクションとセッションをまたぐメモリはどう違いますか。日々のメモはすべて長期メモリに入りますか
  - Q3（資料にない）: 今回作ったRAGの実測平均応答時間と正答率を教えてください
- 対象資料（全文投入と他の方式で範囲が違う点も記録）：
  - 全文投入: 教材JSONの全9資料・438ページ（入力 227,971 文字）。
  - ベクトル検索・Tree・Graph（と、宿題で作った hybrid）: 第1〜3回の本講義 214 ページ。
  - So the full-context row does not have the same scope as the other rows, and its time and tokens cannot be compared fairly with them.

### 各方式の結果（Q1）

| 方式 | 回答の要点・正しさ | 引用ページと根拠 | 時間（秒） | 入力／出力トークン数 | モデル応答回数 | 生成API推定費用（USD） |
|---|---|---|---|---|---|---|
| 全文投入 | LoRA fixes the original weights and learns only the small matrices; QLoRA adds 4bit compression of the weights. Correct. | 第2回 p.51, 52 (the answer names the document and pages, not each sentence) | 2.71 | 117,025 / 138 | 1 | 0.004496 |
| ベクトル検索 | Same content, correct, with each point tied to a page. | 第2回 p.51, 52. 1 search call (`LoRA QLoRA 固定 学習`) | 4.88 | 3,027 / 228 | 2 | 0.001478 |
| Tree | Same content, correct, and adds "less than 1% of the parameters". | 第2回 p.52. 4 `browse_tree` calls (root → 第2回 → the chapter → p.52) | 5.78 | 9,214 / 313 | 5 | 0.003547 |
| Graph | Same content, correct. | 第2回 p.51, 52. 1 `search_graph` call | 4.38 | 5,771 / 185 | 2 | 0.002194 |
| hybrid（宿題で作成） | Same content, correct. | 第2回 p.51, 52. 1 `search_outline` call | 4.77 | 3,229 / 232 | 2 | 0.001549 |

### 他の質問（ベクトル / Tree / Graph / hybrid）

| 質問 | 方式 | 引用ページ | 時間（秒） | 入力／出力 | 応答回数 | 費用（USD） |
|---|---|---|---|---|---|---|
| Q2 | ベクトル検索 | 第3回 p.39, 40, 65 | 5.48 | 2,500 / 542 | 2 | 0.002105 |
| Q2 | Tree | 第3回 p.39, 40 | 8.23 | 11,045 / 571 | 7 | 0.004741 |
| Q2 | Graph | 第3回 p.39, 40, 65 | 5.41 | 5,301 / 500 | 2 | 0.002840 |
| Q2 | hybrid | 第3回 p.13, 38, 39, 40, 65 | 6.34 | 9,009 / 508 | 3 | 0.003973 |
| Q3 | ベクトル検索 | 第2回 p.13 (only as background) | 4.04 | 3,205 / 186 | 2 | 0.001426 |
| Q3 | Tree | none | 5.86 | 5,545 / 311 | 5 | 0.002441 |
| Q3 | Graph | 第2回 p.13 (only as background) | 4.45 | 5,334 / 238 | 2 | 0.002195 |
| Q3 | hybrid | 第2回 p.13, 第1回 p.27 (only as background) | 4.09 | 5,529 / 242 | 2 | 0.002264 |

- 検索だけを実行して見つかったページと、その本文で確認できたこと：
  `python -m app.retrieval "LoRA QLoRA 違い"` returned 5 pages, all from 第2回 chapter 「選んだモデルを、いつ・どう直すか」: p.52 (LoRA と QLoRA), p.51 (PEFT), p.60 (今日の演習), p.47 (根拠と諸説：知識の追加は RAG が効きやすい), p.61 (演習の進め方). The first two directly support the answer (what is fixed, what is learned, what QLoRA adds). p.60 and p.61 only share the words, and p.47 is about RAG, not about the difference between LoRA and QLoRA.
- `--trace`で見えたツール呼び出し（ツール名・引数・回数、Treeでたどった目次など）：
  - ベクトル検索: `search_materials({'query': 'LoRA QLoRA 固定 学習'})`. The model rewrote my question into keywords. 1 call.
  - Graph: `search_graph({'query': 'LoRA QLoRA 固定 学習'})`, 1 call.
  - Tree: `browse_tree({})` → `browse_tree('lec02-main')` → `browse_tree('lec02-main-s045')` → `browse_tree('lec02-main-p052')`. It went down the table of contents to the page and read the full text of one page.
- 取得した情報が足りなかった例、取得できたのに回答へ使えなかった例：
  - Not enough: see the 宿題 section. For a question that spans many chapters (Q4), the vector search did not retrieve 「冪等性がないツール」 (p.27) in any of 3 runs.
  - Retrieved but not used: in Q3 (not in the materials), the methods found a page about asking the same question several times and averaging (第2回 p.13), and the answers used it only as background, saying that the real measured values are not in the materials. That is the wanted behavior.
- 今回の用途に採用したい方式と、その理由・比較条件の限界：
  - For a single fact (Q1), vector search was the cheapest (3,027 input tokens) and as correct as the others. Full-context was also correct and the fastest (2.71 s), but it used 117,025 input tokens (about 39 times more) and about 3 times the cost, and it covered 438 pages instead of 214, so the comparison is not equal.
  - Limits: one run per method for Q1–Q3, one model, and the correctness was checked by me by reading the pages.
- 気づき・疑問：
  - Full-context did not fail. With this model and 117k tokens the answer was correct, so "long input always fails" is not what I saw. The difference is cost, and that the answer does not show the page for each claim.
  - Question: would full-context still be correct if the needed fact were in the middle of 438 pages and not on a page with the same words as the question?

## 宿題

- 取り組んだレベル：発展（Tree と ベクトル検索を組み合わせた取得方法を作る）
- やったこと（変更したファイル・設定・処理、または設計した取得方法）：
  - **Question to solve**: a question whose answer is spread over several chapters: 「第3回で、ツールを使うエージェントに起こりうる危険と、その対策を、章をまたいですべて挙げてください」(Q4). The pages that support the answer are in 第3回 Part 4 (p.24 MCP, p.25–26 Human in the loop, p.27 冪等性がないツール, p.28 情報漏えい), Part 7 (p.48 冪等性の担保) and Part 9 (p.51–53 境界を分ける・サンドボックス). I fixed these 9 pages as the expected set before comparing (my own reading of the table of contents; it is not an official answer).
  - **Design: `search_outline`** (hybrid of vector search and Tree).
    - Vector search finds the entry pages. The full text of the top 3 pages is returned (`OUTLINE_SEED_K = 3` in `app/config.py`).
    - For every chapter that contains one of the 5 hits, the list of all its pages is returned with the title only (`page_id`, `page`, `title`, and `fetched` = whether the body was already returned). The model can then read the other pages it needs with `browse_tree(page_id)`.
    - Why: the vector search is good at finding the entrance but cannot know that the next pages of the chapter are also needed, and Tree can reach them but spends many requests going down from the root. The titles are cheap, so the model can choose the pages itself.
  - Files: `app/retrieval.py` (`search_outline`), `app/tools.py` (tool and its docstring), `app/agent.py` (`HYBRID_INSTRUCTIONS` and the option `--hybrid`, which gives the agent `search_outline` and `browse_tree`), `app/config.py` (`OUTLINE_SEED_K`), `tests/test_search_outline.py` (no API; `uv run pytest -q` gives 18 passed).
  - Iteration: version 1 of `HYBRID_INSTRUCTIONS` said "for questions across chapters, use `search_outline` again with another query". Version 2 changed only one line: for wide questions ("すべて", "章をまたいで"), split the question into at least 3 aspects and call `search_outline` several times with different queries.
- 比較した質問と、固定した条件（モデル・対象資料など）：
  Q4 above, `gemini-3.5-flash-lite`, 第1〜3回 214 pages for every method, default temperature. Each method was run 3 times because the same question gives different results. Two hybrid v1 runs got a rate-limit error first and were run again (the errors are not counted). Traces are in `lectures/05/traces/`.
- 結果（変更前後の回答・根拠、`--trace`の出力、時間・トークン数・生成API推定費用など）：
  Pages cited in the answer, out of the 9 expected pages (24, 25, 26, 27, 28, 48, 51, 52, 53):

  | 方式 | Run 1 | Run 2 | Run 3 | 入力トークン（3回） | 応答回数（3回） | 時間（秒, 3回） | 費用（USD, 3回） |
  |---|---|---|---|---|---|---|---|
  | ベクトル検索 | 7/9 | 4/9 | 4/9 | 28,568 / 6,499 / 6,530 | 6 / 3 / 3 | 15.56 / 6.62 / 8.36 | 0.008163 / 0.002332 / 0.003216 |
  | Tree | 6/9 | 8/9 | 8/9 | 17,538 / 17,538 / 17,538 | 8 / 8 / 8 | 10.40 / 12.50 / 9.30 | 0.007131 / 0.006753 / 0.006653 |
  | Graph | 5/9 | 5/9 | 5/9 | 4,798 / 26,955 / 14,227 | 2 / 4 / 3 | 5.98 / 9.44 / 7.25 | 0.002639 / 0.006790 / 0.004752 |
  | hybrid v1 | 5/9 | 5/9 | 5/9 | 10,215 / 10,215 / 9,230 | 4 / 4 / 4 | 10.05 / 8.46 / 6.70 | 0.004742 / 0.004198 / 0.004406 |
  | hybrid v2 | 4/9 | 6/9 | 5/9 | 10,287 / 16,598 / 5,937 | 4 / 5 / 3 | 7.76 / 9.65 / 6.32 | 0.004584 / 0.006160 / 0.003499 |

  - **p.27 (冪等性がないツール)**: the vector search never cited it (0 of 3 runs). Tree, Graph, hybrid v1 and hybrid v2 cited it in every run. This is the improvement I wanted: the outline of the chapter shows the title 「冪等性がないツール」 next to the pages that were found.
  - **p.48 (冪等性の担保)**: only hybrid cited it (v1 runs 1 and 2, v2 run 2). The outline of Part 7 appeared only when a query hit that chapter.
  - **p.51–53 (境界・サンドボックス)**: Tree cited all three in runs 2 and 3 (and only p.52 in run 1), and the vector search cited them in run 1 only. The hybrid never reached Part 9 in 6 runs, so my method did not solve that part. The model decided it had enough and did not search for the isolation topic, even after I asked for more aspects in v2.
  - Cost: hybrid v1 used about 10k input tokens, between the vector search (6.5k in the two stable runs, 28.6k in the run with 5 searches) and Tree (17.5k, always 8 requests, the same path every time). Tree reached the most expected pages but always used the most requests.
  - Off-topic pages: Graph run 2 cited p.20, 29, 59, 70 and run 3 cited p.70, which are not about tool safety. They came from the shared terms.
  - Other questions: Q1 and Q3 gave the same answers as the other methods with similar cost (Q1: 3,229 input tokens, Q3: 5,529). For Q2 (two chapters) hybrid used 9,009 input tokens against 2,500 for the vector search, with the same pages plus p.13 and p.38 that were not needed.
- 改善した例と、残る失敗・制約：
  - Improved: p.27 was found in every run and p.48 in some runs, which the vector search missed, at a lower cost than Tree.
  - Remaining failures: Part 9 (サンドボックス) was never found by hybrid, and hybrid is more expensive than the vector search for simple questions (Q2). The wording change in v2 did not improve the average (4/9, 6/9, 5/9 against 5/9 each for v1), so it is not an improvement. With 3 runs this difference is within noise.
  - Limits: one question, my own expected set, one model, 3 runs, and the pages cited are counted from the answer text, not from what was retrieved. I did not check each claim in the answers one by one. For these reasons I would not adopt hybrid in general. For a question that needs one page I would use the vector search, and for a wide question I would use Tree.
- 気づき・疑問：
  - Retrieval design changes which evidence appears more than the model does: the answers were fluent in every method, even when pages were missing, so the missing pages are only visible when the expected pages are fixed beforehand.
  - In hybrid the model sometimes called `browse_tree` with no argument and got the root list again, which wasted one request. A clearer tool description could avoid this.
  - Question: would a second vector search with the chapter title as the query find Part 9 more reliably than the model deciding by itself?
