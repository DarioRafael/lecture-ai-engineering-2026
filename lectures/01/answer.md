# 第1回 解答

## 演習

- 講座に固有の質問（宿題の3レベル）へのモデルの回答（要約でよい）：
  The bare model (`gemini-3.5-flash-lite`) does not know the course. It guessed that "AIE2026" is some "AIエンジニア育成講座" and answered with a generic scheme: Level 1 basic / Level 2 applied ("応用") / Level 3 advanced, with typical contents (fill-in-the-blank code, small programs, open-ended challenges). It added hedges such as "it depends on your course" and "ask in Slack/Discord", but the body of the answer still sounded confident.
- 用語集の正しい意味と比べて気づいたこと：
  The glossary (`homework-levels`) says the three levels are 基礎 (check the lecture content), 実装 (write code yourself) and 発展 (investigation / experiments), that doing any ONE of them completes the homework, and that it is generally not graded. The model got the rough idea of "easy / medium / hard", but it named the middle level "応用" instead of "実装", and it never stated as a fact that only one level is enough (one run listed it only as one possibility among others). Some runs pointed the other way: solve the levels in order starting from Level 1, or Level 1 (or 1 and 2) is the required minimum.
- 表示できたトークン数（入力 / 出力）：
  Implemented in `app/ask.py` (`response.usage_metadata`). For the course question: input 21 tokens, output about 520 to 790 tokens depending on the run and the model (tables below). Models that "think" (`gemini-3.5-flash`) also use separate thinking tokens that are NOT included in the output count, so `ask.py` now prints them too, for example `[tokens] 入力: 5 / 出力: 1（＋思考: 113）`.

## 宿題

- 取り組んだレベル：基礎、実装、発展の3つ（最も高いレベル：発展）
- やったこと：
  - **基礎**: asked the same course-specific question 3 times with each of 2 models (`AIE_MODEL` environment variable) and compared the answers. Temperature was left at the default.
  - **実装**: changed `app/ask.py` so it can keep the conversation history: `python -m app.ask --chat` opens a loop that uses `client.chats.create(...)`; the single-question mode still works as before.
  - **発展**: wrote `scripts/benchmark_models.py`. It calls 3 models × 4 questions × 2 repetitions (24 calls), measures the response time with `time.perf_counter()`, records input / output / thinking tokens, waits and retries when it gets a 429 or 503 (and records them), and saves everything to `lectures/01/benchmark_results.json`.
  - The code and the runs were made with the help of Claude Code (AI assistant).
- 結果：

  ### 基礎: same question 3 times, 2 models

  | Model | Run | Input tokens | Output tokens (visible) |
  |---|---|---|---|
  | gemini-3.5-flash-lite | 1 | 21 | 565 |
  | gemini-3.5-flash-lite | 2 | 21 | 570 |
  | gemini-3.5-flash-lite | 3 | 21 | 556 |
  | gemini-3.5-flash | 1 | 21 | 606 |
  | gemini-3.5-flash | 2 | 21 | 718 |
  | gemini-3.5-flash | 3 | 21 | 547 |

  (For `gemini-3.5-flash` these counts leave out the thinking tokens, which I only noticed in the 発展 part.)

  - Every run gave the same skeleton (three generic levels from easy to hard), but the wording, the structure and the details changed each time, even with the same model and the same question.
  - flash-lite: run 1 advised solving the levels in order from Level 1. Run 2 described Level 1 as "copy and run the sample code" and ended with a "how to check" section. Run 3 listed several possible meanings, including levels based on how much AI is used.
  - flash: run 3 said it could mean two things, "degree of completion" or "maturity in using AI". Run 1 said that completing up to Level 2 is "often required to pass", which contradicts the glossary (one level is enough). Run 2 said Level 1 is the "minimum condition for completion".
  - The first two `gemini-3.5-flash` calls returned a 503 ("model is busy") and worked after a retry.

  ### 実装: conversation history

  Test with `python -m app.ask --chat` (three messages in the same conversation):

  | Turn | My message (summary) | Input tokens | Output tokens | Reply |
  |---|---|---|---|---|
  | 1 | "My name is Dario and my favorite color is green. Remember it." | 17 | 34 | Greeted me and confirmed both facts |
  | 2 | "What is my favorite color?" | 67 | 10 | "Your favorite color is green." |
  | 3 | "And what is my name?" | 92 | 5 | "Your name is Dario." |

  The model remembers because the whole conversation is sent again with every message. That is why the input tokens grow (17 → 67 → 92) even though my messages are short, so a long conversation costs more tokens and gets closer to token limits.

  ### 発展: response time and tokens, 3 models × 4 questions × 2 repetitions

  All 24 calls finished successfully. Two calls got a 503 first and worked after waiting 30 seconds (one 503 on a `gemini-3.5-flash` call, and two 503 in a row on one `gemini-3.1-flash-lite` call, so 3 errors in total). No 429 appeared. Raw data: `lectures/01/benchmark_results.json`.

  By model (mean of the 8 calls of each model):

  | Model | Mean time (s) | Median (s) | Min – Max (s) | Mean input tok | Mean output tok | Mean thinking tok | Output tok/s |
  |---|---|---|---|---|---|---|---|
  | gemini-3.5-flash-lite | 2.58 | 2.79 | 0.57 – 3.89 | 14.5 | 524 | 0 | 203 |
  | gemini-3.5-flash | 16.35 | 14.68 | 1.88 – 48.11 | 14.5 | 670 | 934 | 41 (98 if thinking is counted) |
  | gemini-3.1-flash-lite | 7.69 | 5.29 | 3.00 – 22.06 | 14.5 | 560 | 0 | 73 |

  By question and model (mean time / mean visible output tokens, n = 2 each):

  | Question | gemini-3.5-flash-lite | gemini-3.5-flash | gemini-3.1-flash-lite |
  |---|---|---|---|
  | Short (one word answer) | 1.17 s / 3 tok | 2.46 s / 1 tok | 15.2 s / 3 tok |
  | General (What is LoRA?) | 2.85 s / 609 tok | 13.25 s / 642 tok | 4.59 s / 752 tok |
  | Course-specific (3 levels) | 2.67 s / 547 tok | 34.02 s / 732 tok | 7.96 s / 694 tok |
  | Long (answer with a table) | 3.64 s / 938 tok | 15.66 s / 1308 tok | 3.02 s / 793 tok |

  What I see:
  - `gemini-3.5-flash-lite` is clearly the fastest and the most stable (always under 4 s). `gemini-3.5-flash` is about 6 times slower on average. It "thinks" first: on average 934 thinking tokens per call against 670 visible output tokens. Even for the one-word question it produced 1 output token but 64 to 107 thinking tokens.
  - The time does not follow the output length. `gemini-3.1-flash-lite` needed 8 to 22 s for a 3-token answer but only 3 s for a long table. My guess is server load, since this model also had two 503 in a row, but I did not test it.
  - The same question gave different lengths on different models (long question: 793 to 1308 visible tokens), while the input tokens were the same for all models.
  - Small sample: with only 2 repetitions, the same cell varied a lot (`gemini-3.5-flash`, course question: 19.9 s and 48.1 s). Only the big gaps (flash-lite vs flash) are reliable. "Output tok/s" is the visible output tokens divided by the total time, so it includes waiting and is not pure generation speed.

  Relation with the free-tier rate limits:
  - The official page (ai.google.dev/gemini-api/docs/rate-limits) says the limits apply per project (not per API key), are measured in requests per minute (RPM), tokens per minute (TPM) and requests per day (RPD), and depend on the model and the tier. It does not list the numbers for the free tier and sends you to AI Studio. I could not open AI Studio (it needs a Google sign-in), so I do not give exact limit values here.
  - My run used 27 requests (24 calls + 3 retries) in 7.3 minutes, about 3.7 requests per minute and about 3,000 tokens per minute counting thinking tokens, with a 5 s pause between calls. No 429 appeared, so I stayed under the limit of my account, but this only shows I did not reach it, not what it is. The three errors were 503 (the model is busy), which is a server problem, not my quota.
  - The speed of the model changes how fast a script reaches the RPM limit. Called one after another without a pause, `gemini-3.5-flash-lite` (2.6 s per call) could send about 23 requests per minute, while `gemini-3.5-flash` (16 s per call) at most about 3.7. So a slow model slows the script down by itself, and a fast model needs the pause or the retry logic.
  - The course agent calls the LLM several times for one question (as the README says), so it reaches the per-minute limit sooner than `ask.py`.
  - `gemini-3.5-flash` used about 2.4 times more tokens than the visible output suggests (670 visible + 934 thinking). If token limits count thinking tokens too (I did not verify how the quota counts them), this model would reach a token limit faster than its visible output suggests.
- 気づき・疑問：
  - The same question gives different answers each time, and none of them was the real answer. A plain LLM states plausible things about a course it has never seen, so the glossary (Lecture 3, search tool) is needed.
  - Hedges like "generally" and "please check with your course" do not tell the reader that the model simply does not know.
  - The visible output token count is not the real usage for thinking models. I found this by comparing the numbers, and changed `ask.py` to print the thinking tokens.
  - A "lite" or faster-looking model is not always faster: `gemini-3.1-flash-lite` was slower than `gemini-3.5-flash-lite` in my sample, but I cannot tell whether the cause is the model or the load at that moment.
  - Open questions: How much does a lower temperature reduce the differences between runs (I did not test temperature)? Do thinking tokens count toward the free-tier limits? What are the real free-tier numbers in AI Studio? Would the times be the same at another hour of the day?
