# 第2回 解答

## 演習

- 使ったモデル・設定（`result.json` の `config` から）：
  `Qwen/Qwen3.5-0.8B`（revision `2fc06364…`）、LoRA `r=16`・`lora_alpha=32`、`lr=2e-4`、`num_train_epochs=20`（40 steps）、`warmup_steps=6`、`seed=42`、greedy generation（`max_new_tokens=96`）。Trainable parameters: 6,389,760 / 758,782,784（0.84%）. Base weights in fp32: 3.01 GB.
- 自分で学習を実行したか（`executed_training_myself`）：はい（実行できた範囲：sections 0–7 of the notebook. Section 8 (4-bit) was not run.）
  The notebook was run on a local GPU (NVIDIA RTX 5060 Ti 16 GB, Windows, Python 3.12, torch 2.11.0+cu128) instead of Colab, with the same pinned versions (transformers 5.18.0, peft 0.21.1, trl 1.14.2, accelerate 1.15.0, datasets 5.1.0). The cells were run unchanged except the `%pip` cell and the output folder. Training time: 98 s.
- 学習前：`format_rate` = 0.095（2/21） / `content_rate` = 0.0
- 学習後：`format_rate` = 1.0（21/21） / `content_rate` = 0.905（19/21）
- 退行した質問：なし（`regressed` is empty）
- 学習後に残った失敗と、その型（根拠なしの質問に断定した / 根拠ありの質問に確認要求で逃げた / 形式の崩れ）：
  2 failures, both **根拠なしの質問に断定した**. The model answered with the closest FAQ item and `needs_review: false`:
  - 「成績はいつ出ますか」→ the submission deadline (`提出期限は 9 月 30 日 23:59`)
  - 「オフィスアワーは事前予約が必要ですか」→ the office hours (`毎週火曜 17:00〜18:00`)
  No format errors and no "escape" on grounded questions.
- 知識を問う質問（セクション 6）の結果（学習前の分類 → 学習後の分類）と気づいたこと：
  | 質問 | FAQ にある | 学習前 → 学習後 |
  |---|---|---|
  | この講座の最終課題の締切はいつですか | no | format_error → **asserted**（answered 9 月 30 日 23:59） |
  | 担当教員の名前は何ですか | no | format_error → needs_review |
  | 次回の講義のテーマは何ですか | no | format_error → needs_review |
  | 課題の提出期限はいつですか（対照） | yes | format_error → asserted（correct） |

  (The notebook table shows "FAQ にある = False" for the control question because it is a training question and not in `gold`, but it is in the FAQ.)
  Questions that clearly have nothing to do with the FAQ now get "確認が必要". But a question that only looks like an FAQ item ("final assignment deadline" vs "submission deadline") gets a confident wrong answer.
- 学習で変わったこと・変わらなかったこと：
  Changed: the output format (JSON with exactly `answer` and `needs_review`: 10% → 100%), the answers now copy the FAQ sentence, and the fixed "確認が必要" answer for clearly ungrounded questions. Not changed: the judgment for questions close to an FAQ item. The model still picks the nearest item and asserts it. It learned the output pattern, not what it actually knows.

## 宿題

- 取り組んだレベル：基礎、発展（最も高いレベル：発展）
- 変えた設定やデータ：
  - **基礎**: only `lr` changed, 2e-4 → 2e-5 (10 times lower). Everything else was the same, and each setting was run in a fresh process (same as restarting the session). Results: `lectures/02/results/base/` and `lectures/02/results/lr2e-5/`.
  - **発展**: the training data was the glossary Q&A made with `scripts/make_sft_dataset.py` (58 terms × 2 templates = 116 examples, `messages` JSONL), instead of the FAQ. 5 epochs (75 steps), `lr=2e-4`, same LoRA settings as the notebook. Evaluation set made for the glossary: 22 questions in 3 groups, each with expected keywords: 8 with the same wording as the training data, 8 paraphrased (other wording or an alias), and 6 terms that are not in the glossary (the correct answer is "not in the glossary / don't know"). The same questions were also answered by a simple keyword search over the glossary (term or alias found in the question → return its definition, otherwise "用語集にありません"). Script: `scripts/glossary_lora_compare.py`. Results: `lectures/02/advanced/result_advanced.json`.
- 結果（比較表や数字）：

  **基礎: changing the learning rate**

  | | lr = 2e-4 (original) | lr = 2e-5 |
  |---|---|---|
  | format_rate (before → after) | 0.095 → **1.0** | 0.095 → **1.0** |
  | content_rate (before → after) | 0.0 → **0.905** | 0.0 → **0.714** |
  | loss at step 10 / final loss (step 40) | 1.563 / **0.014** | 2.337 / **1.078** |
  | training time | 98 s | 80 s |
  | failures after training | 2 | 6 |
  | regressed | none | none |

  With lr = 2e-5 the JSON format was still learned perfectly, even with a much higher final loss, so the format is the easy part. But the exact wording and the decision of when to say "確認が必要" were not learned. Failures with 2e-5: 1 grounded question escaped (「PDF 以外でも出せますか」→ 記載がありません), 3 ungrounded questions got invented answers (「課題の文字数に制限はありません」「フィードバックはもらえません」「事前予約が必要です」), and 2 had `needs_review: true` but an answer without "確認". Invented answers in a perfect format look reliable, which is worse than a format error. The time difference (98 s vs 80 s) is run-to-run noise; both runs had 40 steps.

  **発展: glossary data, before vs after LoRA vs search**

  | Group | Before (base model) | After LoRA | Glossary search |
  |---|---|---|---|
  | Same wording as training (8) | 0% | 37.5% | 100% |
  | Paraphrased (8) | 25% | 50% | 75% |
  | Not in glossary → says so (6) | 0% | 0% | 100% |
  | All (22) | 9.1% | 31.8% | 90.9% |

  Training: 116 examples, 75 steps, 118 s, loss 3.28 → 0.35.
  - After training the model writes in the glossary style ("AIE2026の…") and sometimes reproduces a definition almost exactly (LoRA, レート制限). Sometimes it keeps the words but changes the meaning (既定モデル: 「…を考えて選んでいる」 became 「…を考えずに選んでいる」). It often mixes definitions and invents details: 「蒸留」→ "Pydantic AIでは Vaporizer class", 「lec03-start」→ an invented date "2026年10月24日 10:00", 「answer.md」→ an invented tool name.
  - For the 6 terms that are not in the glossary, the model never said it did not know, before or after training. After training it answers them in the glossary style, which looks more trustworthy but is wrong. The training data had no "unknown" examples, so the model learned "always answer in this style".
  - The keyword scoring is only approximate. 「AIE2026で標準で使うモデル」 was scored wrong because the answer wrote "Gemini-3.5-flash-lite" with a capital G, although it is correct. Some answers contained the keyword but were wrong (after training, 「エージェントハーネス」 was described as a settings file).
  - The search was perfect for the same wording and for unknown terms, but missed the paraphrases that do not contain the term or an alias (「宿題のレベル分け」「標準で使うモデル」).
- ファインチューニングが向く場面・向かない場面についての考察：
  - **Good fit:** fixing the output format and behavior. With only 14 examples and 98 s of training, the JSON format with `needs_review` went from 10% to 100%. It also fits a consistent tone or style, and shorter prompts with a small model, so inference is cheaper.
  - **Bad fit:** adding or updating knowledge. With 116 examples × 5 epochs the model reproduced only some definitions, mixed others and invented details. Changing one definition means training again, the answer cannot show its source, and the model does not learn "I don't know" unless the data has such examples.
  - **Search over the glossary (like RAG):** exact, easy to update (edit the JSON), the source is visible, and it can say "not found". Its weak point is wording: keyword search misses paraphrases and synonyms, and an LLM is still needed to write a natural answer from the retrieved text.
  - **Conclusion:** use search for knowledge and fine-tuning (or a prompt and structured output) for the format. Better search, with more aliases or embeddings, would fix the paraphrase problem more cheaply than more training.
