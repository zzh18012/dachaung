# -*- coding: utf-8 -*-
"""Stage 9 批次 26：基线 dev 选优 CLI（设计 §5：N 网格仅 dev 搜索）。

用法（项目 venv python 运行）：
  python scripts/stage9_baseline_select.py \
      --manifest samples/private/stage9-corpus/manifest.draft.json \
      --annotations samples/private/stage9-corpus/annotations \
      [--split dev] [--report outputs/stage9-baseline-select.json] [--json]

退出码：0 = 完成；2 = 输入/IO 错误。输出：逐篇 × (B1 / B2-foldws-v1,
N) 的 ARI 与披露计数、集级 macro average、选优结果（平局取最小 N）。
B2-foldws-v1 为冻结显式变体（GPT 裁决 2026-09-05 C3 追认：
input_view=fold_ws，换行级分隔符结构性恒不命中）。manifest 冻结前的
运行视为 dry run；N* 冻结硬门槛 = 最终 14 篇 dev 全网格重跑。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stage9.baseline_eval import (  # noqa: E402
    BASELINE_CONFIG,
    select_baselines,
    evaluate_doc,
)
from stage9.baselines import B1_N_GRID  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="B1/B2 N 网格 dev 选优（ARI macro average）")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--split", default="dev",
                        help="参与的 split（默认 dev；holdout 禁止）")
    parser.add_argument("--report", help="报告 JSON 落盘路径")
    parser.add_argument("--json", action="store_true",
                        help="stdout 输出完整 JSON（默认摘要表）")
    args = parser.parse_args(argv)
    if args.split == "holdout":
        print("holdout 仅最终评测跑一次，禁止参数搜索", file=sys.stderr)
        return 2

    try:
        with open(args.manifest, encoding="utf-8") as fh:
            manifest = json.load(fh)
        doc_ids = [d["doc_id"] for d in manifest["docs"]
                   if d.get("split") == args.split]
        if not doc_ids:
            print("split %r has no docs in manifest" % args.split,
                  file=sys.stderr)
            return 2
        doc_reports = []
        for doc_id in doc_ids:
            path = Path(args.annotations) / (doc_id + ".json")
            with open(path, encoding="utf-8") as fh:
                ann = json.load(fh)
            if ann.get("doc_id") != doc_id:
                print("doc_id mismatch: %s" % path, file=sys.stderr)
                return 2
            doc_reports.append(evaluate_doc(ann))
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print("input error: %s" % exc, file=sys.stderr)
        return 2

    macro, selection = select_baselines(doc_reports)
    payload = {
        "tool": "stage9_baseline_select",
        "split": args.split,
        "doc_count": len(doc_reports),
        "n_grid": list(B1_N_GRID),
        "selection_rule": "macro ARI 最大者；平局取最小 N",
        "baseline_config": BASELINE_CONFIG,
        "selection": selection,
        "macro": macro,
        "docs": doc_reports,
        "variant_note": (
            "B2-foldws-v1 为冻结显式变体（GPT 裁决 2026-09-05 C3）："
            "input_view=fold_ws，前两级分隔符（\\n\\n 与 \\n）结构性恒"
            "不命中；设计 §5 原始 B2（保留换行输入）记未执行/不可复现"),
        "dry_run_note": (
            "manifest 冻结前运行视为 dry run；N* 冻结硬门槛 = 最终 "
            "14 篇 dev 全网格重跑（13 篇 dev 结果非正式）"),
    }
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        show(payload)
    return 0


def show(payload):
    print("split=%s docs=%d grid=%s"
          % (payload["split"], payload["doc_count"], payload["n_grid"]))
    print("%-4s %s" % ("N", "  ".join("macro-ARI")))
    for bl, per_n in payload["macro"].items():
        cells = "  ".join(
            "%6s" % ("-" if per_n[n] is None else "%.4f" % per_n[n])
            for n in payload["n_grid"])
        print("%-4s %s" % (bl, cells))
    for bl, sel in payload["selection"].items():
        tie = ("（平局 %s，取最小 N）" % sel["tied_with"]
               if len(sel["tied_with"]) > 1 else "")
        macro_txt = ("-" if sel["macro_ari"] is None
                     else "%.4f" % sel["macro_ari"])
        print("%s: N*=%s macro=%s%s" % (bl, sel["n"], macro_txt, tie))
    for d in payload["docs"]:
        b1 = d["results"]["B1"][payload["n_grid"][0]]
        print("  %-38s chars=%-7d text_units=%-5d "
              "unmatched=%d cross=%d uncovered=%d（首格 N=%s 披露）"
              % (d["doc_id"], d["chars"], d["text_units"],
                 b1["unmatched_chunks"], b1["cross_chunk_units"],
                 b1["uncovered_units"], payload["n_grid"][0]))


if __name__ == "__main__":
    sys.exit(main())
