"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする
    uv run python -m app.ask --chat     # 会話履歴を保ったまま、続けて質問する（宿題・実装）

ツールを持たない「素の」呼び出し。単発の質問は会話履歴も持たない（--chat のときだけ履歴を保つ）。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def _print_tokens(response) -> None:
    usage = response.usage_metadata
    line = f"[tokens] 入力: {usage.prompt_token_count} / 出力: {usage.candidates_token_count}"
    if usage.thoughts_token_count:  # 思考するモデルは、出力とは別に「思考トークン」を使う
        line += f"（＋思考: {usage.thoughts_token_count}）"
    print(line)


def ask(question: str) -> str:
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(model=MODEL, contents=question)
    _print_tokens(response)

    return response.text


def chat() -> None:
    """会話履歴を保ったまま、続けて質問できる対話モード（第1回 宿題・実装）。"""
    client = genai.Client(api_key=get_api_key())
    # chats.create が履歴を持ち、send_message のたびにこれまでのやり取りを一緒に送る。
    # そのため会話が続くほど「入力トークン数」が増える。
    session = client.chats.create(model=MODEL)

    print("会話モード（空行か exit で終了）")
    while True:
        try:
            question = input("\n[あなた] ").strip()
        except EOFError:
            break
        if question in ("", "exit", "quit"):
            break
        response = session.send_message(question)
        _print_tokens(response)
        print(f"[AI] {response.text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--chat", action="store_true", help="会話履歴を保ったまま続けて質問する")
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    try:
        if args.chat:
            chat()
        else:
            print(f"[質問] {args.question}\n")
            print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
