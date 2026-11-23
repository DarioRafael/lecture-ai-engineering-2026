"""第2回 宿題（発展）: 用語集の Q&A データで LoRA 学習し、学習前後と「用語集の検索」を比べる。

使い方（リポジトリの直下で、GPU のある環境）:
    python scripts/glossary_lora_compare.py --out lectures/02/advanced

1. scripts/make_sft_dataset.py で用語集から messages 形式の JSONL を作る（58 語 × 2 テンプレート = 116 件）
2. 評価用の質問と正解を用意する（下の EVAL）。3 種類:
   - seen:       学習データと同じ言い回し（「◯◯」とは何ですか？）
   - paraphrase: 言い回しや呼び方を変えた質問（学習データに無い）
   - unknown:    用語集に無い語。「用語集に無い／分からない」と答えるのが正解
3. 学習前の基盤モデル、LoRA 学習後のモデル、単純なキーワード検索（用語集を引いて定義を返す）を同じ質問で採点する
モデル・LoRA の設定は第2回ノートブック（lora_format_tuning.ipynb）と同じ。
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY = ROOT / "data" / "glossary.json"

BASE_MODEL = "Qwen/Qwen3.5-0.8B"
REVISION = "2fc06364715b967f1860aea9cf38778875588b17"

# (種類, 質問, 正解の答えに含まれるべき語句)。unknown は語句の代わりに「分からない」系の表現を求める
EVAL = [
    ("seen", "「宿題の3レベル」とは何ですか？", ["基礎", "実装", "発展"]),
    ("seen", "「answer.md」とは何ですか？", ["fork", "PR"]),
    ("seen", "「lecNN-start タグ」とは何ですか？", ["タグ", "ブランチ"]),
    ("seen", "「既定モデル」とは何ですか？", ["gemini-3.5-flash-lite"]),
    ("seen", "「LoRA」とは何ですか？", ["低ランク"]),
    ("seen", "「レート制限」とは何ですか？", ["429"]),
    ("seen", "「ハーネス」とは何ですか？", ["ツール", "Claude Code"]),
    ("seen", "「TestModel」とは何ですか？", ["Pydantic AI", "テスト"]),
    ("paraphrase", "AIE2026の宿題のレベル分けについて説明してください。", ["基礎", "実装", "発展"]),
    ("paraphrase", "解答ファイル（answer.md）はどうやって提出しますか？", ["PR"]),
    ("paraphrase", "lec03-start というタグは何のためにありますか？", ["ブランチ"]),
    ("paraphrase", "AIE2026で標準で使うモデルは何ですか？", ["gemini-3.5-flash-lite"]),
    ("paraphrase", "Low-Rank Adaptation について簡単に教えてください。", ["低ランク"]),
    ("paraphrase", "APIで429エラーが返ってくるのはなぜですか？", ["上限"]),
    ("paraphrase", "エージェントハーネスって何ですか？", ["ツール"]),
    ("paraphrase", "Pydantic AI の TestModel は何に使いますか？", ["テスト"]),
    ("unknown", "「ベクトルデータベース」とは何ですか？", None),
    ("unknown", "「RAG」とは何ですか？", None),
    ("unknown", "「ゼロショット推論」とは何ですか？", None),
    ("unknown", "「AIE2026の第14回の課題」とは何ですか？", None),
    ("unknown", "「lec09-final タグ」とは何ですか？", None),
    ("unknown", "「蒸留」とは何ですか？", None),
]
ABSTAIN = ["用語集にありません", "用語集には", "わかりません", "分かりません", "存在しません", "確認が必要",
           "情報がありません", "見つかりません", "記載がありません", "知りません"]
NOT_FOUND = "用語集にありません。"


def score(category, answer, must_include):
    if category == "unknown":
        return any(p in answer for p in ABSTAIN)
    return all(w in answer for w in must_include)


def summarize(label, rows):
    out = {"label": label, "n": len(rows)}
    for cat in ("seen", "paraphrase", "unknown"):
        mine = [r for r in rows if r["category"] == cat]
        out[f"{cat}_rate"] = round(sum(r["ok"] for r in mine) / len(mine), 3)
    out["all_rate"] = round(sum(r["ok"] for r in rows) / len(rows), 3)
    return out


def search_answer(question, terms):
    """単純な検索: 質問に用語名か別名（2 文字以上、大文字小文字は区別）が含まれていれば、その定義を返す"""
    hits = []
    for t in terms:
        names = [re.sub(r"（.*?）", "", t["term"]).strip(), t["term"], *t.get("aliases", [])]
        if any(len(n) >= 2 and n in question for n in names):
            hits.append(t["definition"])
    return "\n".join(hits) if hits else NOT_FOUND


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="lectures/02/advanced")
    ap.add_argument("--epochs", type=float, default=5)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    import torch
    import transformers, peft, trl
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    # 1. 用語集から学習データを作る（講座のスクリプトをそのまま使う）
    jsonl = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_sft_dataset.py")],
                           capture_output=True, text=True, encoding="utf-8", check=True).stdout
    records = [json.loads(line) for line in jsonl.splitlines() if line.strip()]
    print(f"学習データ: {len(records)} 件")

    terms = json.loads(GLOSSARY.read_text(encoding="utf-8"))["terms"]
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, revision=REVISION)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, revision=REVISION, dtype=torch.float32).to("cuda")

    def generate(m, question):
        prompt = tok.apply_chat_template([{"role": "user", "content": question}], tokenize=False,
                                         add_generation_prompt=True, enable_thinking=False)
        inputs = tok(prompt, return_tensors="pt").to(m.device)
        with torch.no_grad():
            o = m.generate(**inputs, max_new_tokens=160, do_sample=False, pad_token_id=tok.pad_token_id)
        return tok.decode(o[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    def evaluate(label, answer_fn):
        t0 = time.time()
        rows = []
        for category, q, must in EVAL:
            a = answer_fn(q)
            rows.append({"category": category, "question": q, "must_include": must, "answer": a,
                         "ok": score(category, a, must)})
        s = summarize(label, rows)
        s["seconds"] = round(time.time() - t0, 1)
        print(json.dumps(s, ensure_ascii=False), flush=True)
        return s, rows

    # 2. 学習前と検索
    before, before_rows = evaluate("before", lambda q: generate(model, q))
    search, search_rows = evaluate("search", lambda q: search_answer(q, terms))

    # 3. LoRA 学習（ノートブックと同じ LoRA 設定）
    model.config.use_cache = False
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    sft = SFTConfig(output_dir=str(out / "ckpt"), num_train_epochs=args.epochs, per_device_train_batch_size=4,
                    gradient_accumulation_steps=2, learning_rate=args.lr, lr_scheduler_type="cosine", warmup_steps=6,
                    logging_steps=10, save_strategy="no", max_length=512, packing=False, report_to="none", seed=args.seed)
    trainer = SFTTrainer(model=model, args=sft, train_dataset=Dataset.from_list(records), peft_config=lora,
                         processing_class=tok)
    t0 = time.time()
    trainer.train()
    train_seconds = round(time.time() - t0, 1)
    tuned = trainer.model
    tuned.config.use_cache = True
    tuned.eval()
    losses = [e["loss"] for e in trainer.state.log_history if "loss" in e]

    # 4. 学習後
    after, after_rows = evaluate("after", lambda q: generate(tuned, q))

    result = {
        "config": {"base_model": BASE_MODEL, "revision": REVISION, "train_records": len(records),
                   "epochs": args.epochs, "lr": args.lr, "lora_r": 16, "lora_alpha": 32, "seed": args.seed},
        "versions": {m.__name__: m.__version__ for m in [transformers, peft, trl, torch]},
        "device": torch.cuda.get_device_name(0),
        "training": {"seconds": train_seconds, "steps": trainer.state.global_step, "first_loss": losses[0] if losses else None,
                     "final_loss": losses[-1] if losses else None, "loss_log": losses},
        "before": before, "after": after, "search": search,
        "rows": [{"category": b["category"], "question": b["question"], "must_include": b["must_include"],
                  "before": b["answer"], "before_ok": b["ok"], "after": a["answer"], "after_ok": a["ok"],
                  "search": s["answer"], "search_ok": s["ok"]}
                 for b, a, s in zip(before_rows, after_rows, search_rows)],
        "executed_training_myself": True,
    }
    (out / "result_advanced.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("training", "before", "after", "search")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
