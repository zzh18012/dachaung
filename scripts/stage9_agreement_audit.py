# -*- coding: utf-8 -*-
"""编号不变性辅助审计 CLI（外部评审 R-A；G⑥ 前置）。

对同一 doc_id 的两份标注输出两个口径的一致率与分解：
原始 = 冻结 v1 字符串口径（原报告不动）；分区 = 段标签按对齐
等价类规范化后的辅助口径。两者之差 = 纯编号伪分歧量级。

用法：
  python scripts/stage9_agreement_audit.py \
      --a samples/private/stage9-corpus/annotations/<doc>.json \
      --b samples/private/stage9-corpus/annotations-user/<doc>.json \
      [--json]
退出码：0 正常；2 输入错误。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stage9.agreement import AgreementInputError  # noqa: E402
from stage9.agreement_audit import audit_agreement  # noqa: E402


def _fmt(v):
    return "n/a" if v is None else "%.4f" % v


def show(r):
    o, p = r["original"], r["partition"]
    print("doc_id: %s（编号不变性辅助审计——不改冻结口径与原始报告）"
          % r["doc_id"])
    print("原始口径:   agreement=%s [%s, %s] decision=%s "
          "segment_diff=%d kind_diff=%d"
          % (_fmt(o["agreement"]), _fmt(o["agreement_lower"]),
             _fmt(o["agreement_upper"]), o["decision"],
             r["original_segment_diff_count"],
             r["original_kind_diff_count"]))
    print("分区口径:   agreement=%s [%s, %s] decision=%s "
          "segment_diff=%d"
          % (_fmt(p["agreement"]), _fmt(p["agreement_lower"]),
             _fmt(p["agreement_upper"]), p["decision"],
             r["partition_segment_diff_count"]))
    print("units: a=%d b=%d 对齐=%d union=%d"
          % (o["units_a"], o["units_b"], r["aligned_pair_count"],
             o["union"]))
    print("分解: 仅编号伪分歧(label_only)=%d 分区新增严判"
          "(partition_only)=%d 双口径都分歧=%d"
          % (len(r["label_only_pairs"]),
             len(r["partition_only_pairs"]),
             r["both_diff_pair_count"]))
    v = r["segment_vocab"]
    print("段词表: a=%d b=%d 交集=%d 风格=%s"
          % (v["ids_a"], v["ids_b"], v["overlap"], v["style"]))
    for tag, key in (("仅编号差异对", "label_only_pairs"),
                     ("分区严判对", "partition_only_pairs")):
        pairs = r[key]
        if pairs:
            print("—— %s（%d，列前 10）——" % (tag, len(pairs)))
            for a_uid, b_uid in pairs[:10]:
                print("  A:%s | B:%s" % (a_uid, b_uid))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="编号不变性辅助审计（段标签按对齐等价类规范化）")
    parser.add_argument("--a", required=True, help="第一份标注 JSON")
    parser.add_argument("--b", required=True, help="第二份标注 JSON")
    parser.add_argument("--json", action="store_true",
                        help="机器可读 JSON 输出")
    args = parser.parse_args(argv)
    result = {"tool": "stage9_agreement_audit", "ok": True}
    try:
        with open(args.a, encoding="utf-8") as fh:
            ann_a = json.load(fh)
        with open(args.b, encoding="utf-8") as fh:
            ann_b = json.load(fh)
        report = audit_agreement(ann_a, ann_b)
    except (OSError, json.JSONDecodeError, AgreementInputError,
            KeyError, TypeError, IndexError) as exc:
        result.update({"ok": False, "error": str(exc),
                       "error_type": type(exc).__name__})
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        show(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
