# -*- coding: utf-8 -*-
"""Stage 9 批次 26：双标注一致率 CLI（标注指南 §7）。

用法（项目 venv python 运行；两份输入须为同一 doc_id 的标注 JSON，
第一份 = Claude 草案，第二份 = 用户独立复核）：
  python scripts/stage9_agreement.py \
      --a samples/private/stage9-corpus/annotations/<doc>.json \
      --b samples/private/stage9-corpus/annotations/<doc>-review.json \
      [--json] [--max-disagreements 40]

退出码：0 = 一致率 ≥0.85；1 = 一致率 <0.85（停机线预警——是否停机
仍须仲裁判定收敛性）；2 = 输入/IO 错误。输入应先过
stage9_validate_annotations.py（本脚本不重复 schema 校验）。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stage9.agreement import (  # noqa: E402
    AgreementInputError,
    compute_agreement,
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="双标注一致率（unit 级：切分一致 + gold_segment 一致）")
    parser.add_argument("--a", required=True, help="第一份标注 JSON")
    parser.add_argument("--b", required=True, help="第二份标注 JSON")
    parser.add_argument("--json", action="store_true",
                        help="机器可读 JSON 输出")
    parser.add_argument("--max-disagreements", type=int, default=40,
                        help="human 模式每类分歧最多列出条数（默认 40）")
    args = parser.parse_args(argv)

    result = {"tool": "stage9_agreement", "ok": True}
    try:
        with open(args.a, encoding="utf-8") as fh:
            ann_a = json.load(fh)
        with open(args.b, encoding="utf-8") as fh:
            ann_b = json.load(fh)
        report = compute_agreement(ann_a, ann_b)
    except (OSError, json.JSONDecodeError,
            AgreementInputError, KeyError, TypeError, IndexError) as exc:
        result.update({"ok": False, "error": str(exc),
                       "error_type": type(exc).__name__})
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        show(report, args.max_disagreements)
    return 1 if report["below_threshold"] else 0


def show(report, limit):
    rate = report["agreement"]
    print("doc_id: %s" % report["doc_id"])
    print("一致率: %s（阈值 %s）"
          % ("n/a" if rate is None else "%.4f" % rate,
             report["threshold"]))
    print("units: a=%d b=%d 对齐=%d 一致=%d 并集=%d"
          % (report["units_a"], report["units_b"], report["matched"],
             report["agree"], report["union"]))
    print("分歧: kind_diff=%d segment_diff=%d only_a=%d only_b=%d "
          "hard_boundary_diff=%d（信息项）"
          % (len(report["kind_diff"]), len(report["segment_diff"]),
             len(report["only_a"]), len(report["only_b"]),
             report["hard_boundary_diff"]))
    sections = (
        ("kind 不一致（文本对齐但 unit 类别不同）", report["kind_diff"],
         _pair_brief),
        ("gold_segment 不一致（切分一致但段归属不同）",
         report["segment_diff"], _pair_brief),
        ("仅 A 有（B 未切出/文本不同）", report["only_a"], _unit_brief),
        ("仅 B 有（A 未切出/文本不同）", report["only_b"], _unit_brief),
    )
    for title, items, fmt in sections:
        if not items:
            continue
        print("—— %s（%d，列前 %d）——" % (title, len(items), limit))
        for item in items[:limit]:
            print("  " + fmt(item))


def _unit_brief(u):
    return "%s p%s %s seg=%s %r" % (u["unit_id"], u["page"], u["kind"],
                                     u["gold_segment_id"],
                                     u["preview"][:50])


def _pair_brief(pair):
    return "%s | A: %s | B: %s" % (
        pair["a"]["unit_id"], _unit_brief(pair["a"]),
        _unit_brief(pair["b"]))


if __name__ == "__main__":
    sys.exit(main())
