"""第1回 宿題（発展）: 複数のモデル・質問で、応答時間とトークン数を計測して比較する。

使い方（リポジトリの直下で）:
    uv run python -m scripts.benchmark_models
    uv run python -m scripts.benchmark_models --repeat 3 --pausa 8 --out lectures/01/benchmark_results.json

モデル × 質問 × 繰り返し回数だけ API を呼び、1回ごとの応答時間とトークン数を記録する。
レート制限（429）やモデルの混雑（503）が出たら、待って再試行し、その回数も記録する。
結果は Markdown の表で表示し、JSON にも保存する。
"""

import argparse
import json
import statistics
import time
from pathlib import Path

from google import genai
from google.genai import errors

from app.ask import DEFAULT_QUESTION
from app.config import get_api_key

MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.1-flash-lite"]

# 出力の長さが違う4種類の質問（ラベル: 質問文）
QUESTIONS = {
    "短い（一言）": "日本の首都はどこですか？一言で答えてください。",
    "一般": "LoRAとは何ですか？",
    "講座固有": DEFAULT_QUESTION,
    "長い（表）": "LoRAとQLoRAの違いを、表を使って詳しく説明してください。",
}

RETRY_CODES = (429, 503)  # 待てば通る可能性があるエラー
MAX_ATTEMPTS = 3
RETRY_WAIT_SEC = 30


def measure(client, model: str, question: str) -> dict:
    """1回の呼び出しを計測する。待って再試行したエラーも記録する。"""
    errors_seen = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            start = time.perf_counter()
            response = client.models.generate_content(model=model, contents=question)
            seconds = time.perf_counter() - start
            usage = response.usage_metadata
            return {
                "ok": True,
                "seconds": round(seconds, 2),
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count,
                "thinking_tokens": getattr(usage, "thoughts_token_count", None) or 0,
                "errors_before_success": errors_seen,
            }
        except errors.APIError as e:
            errors_seen.append(e.code)
            if e.code not in RETRY_CODES or attempt == MAX_ATTEMPTS:
                return {"ok": False, "error": e.code, "errors_before_success": errors_seen}
            time.sleep(RETRY_WAIT_SEC)
    return {"ok": False, "error": "unknown", "errors_before_success": errors_seen}


def _mean(values):
    return round(statistics.mean(values), 2) if values else None


def print_tables(rows: list[dict]) -> None:
    print("\n### モデルごとの平均（成功した呼び出しのみ）\n")
    print("| モデル | 成功/試行 | 平均応答時間(秒) | 平均入力tok | 平均出力tok | 平均思考tok | 出力tok/秒 | 再試行したエラー |")
    print("|---|---|---|---|---|---|---|---|")
    for model in MODELS:
        mine = [r for r in rows if r["model"] == model]
        ok = [r for r in mine if r["ok"]]
        retried = [c for r in mine for c in r["errors_before_success"]]
        sec = _mean([r["seconds"] for r in ok])
        out = _mean([r["output_tokens"] for r in ok])
        rate = round(sum(r["output_tokens"] for r in ok) / sum(r["seconds"] for r in ok), 1) if ok else None
        print(
            f"| {model} | {len(ok)}/{len(mine)} | {sec} | {_mean([r['input_tokens'] for r in ok])} | "
            f"{out} | {_mean([r['thinking_tokens'] for r in ok])} | {rate} | {retried or '-'} |"
        )

    print("\n### 質問 × モデル: 平均応答時間(秒) / 平均出力トークン\n")
    print("| 質問 | " + " | ".join(MODELS) + " |")
    print("|---|" + "---|" * len(MODELS))
    for label in QUESTIONS:
        cells = []
        for model in MODELS:
            ok = [r for r in rows if r["model"] == model and r["label"] == label and r["ok"]]
            cells.append(f"{_mean([r['seconds'] for r in ok])} 秒 / {_mean([r['output_tokens'] for r in ok])} tok" if ok else "失敗")
        print(f"| {label} | " + " | ".join(cells) + " |")


def main() -> None:
    parser = argparse.ArgumentParser(description="モデル・質問ごとに応答時間とトークン数を計測する")
    parser.add_argument("--repeat", type=int, default=2, help="同じ組み合わせを何回呼ぶか")
    parser.add_argument("--pausa", type=float, default=5.0, help="呼び出しの間に待つ秒数（1分あたりの上限対策）")
    parser.add_argument("--out", default="lectures/01/benchmark_results.json", help="結果の保存先（JSON）")
    args = parser.parse_args()

    client = genai.Client(api_key=get_api_key())
    rows = []
    total = len(MODELS) * len(QUESTIONS) * args.repeat
    for model in MODELS:
        for label, question in QUESTIONS.items():
            for i in range(1, args.repeat + 1):
                result = measure(client, model, question)
                rows.append({"model": model, "label": label, "run": i, **result})
                print(f"[{len(rows)}/{total}] {model} | {label} | #{i} -> {result}", flush=True)
                time.sleep(args.pausa)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n保存しました: {args.out}")
    print_tables(rows)


if __name__ == "__main__":
    main()
