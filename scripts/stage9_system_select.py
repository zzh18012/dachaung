# -*- coding: utf-8 -*-
"""Stage 9 批次 26：系统侧 max_chars dev 选优 CLI（G⑦ 预实现，裁决 C）。

用法（项目 venv python 运行）：
  python scripts/stage9_system_select.py \
      --manifest samples/private/stage9-corpus/manifest.json \
      --annotations samples/private/stage9-corpus/annotations \
      --gold-revision <G⑥ 冻结签发的 gold revision> \
      [--report outputs/stage9-system-select.json] [--json]

预注册：stage9/system_select_preregistration.json（先于实现与任何
真实运行提交；本 CLI 逐项核对预注册并拒绝偏离）。

硬边界（GPT 裁决 2026-09-07 C）：
- G⑥ 完成前禁止在真实 14-dev gold 上做 max_chars 参数探索（含自称
  dry run）——--gold-revision 为强制参数，真实 gold revision 只能由
  G⑥ 冻结产生；合成测试用显式 "synthetic-*" 值；
- split 固定 dev（预注册 14 篇单列，逐篇核对）；comparison/holdout
  拒绝运行；
- manifest 字节 SHA-256 必须等于预注册期望值（冻结层防篡改）；
- 报告必含 provenance：manifest_sha256 / gold_revision /
  preregistration_sha256 / implementation_commit / 网格 / 规则 /
  边界处理；N/A 与 reason 分布必报（指南 §9）。

退出码：0 = 完成；2 = 输入错误/预注册核对失败/全 N/A 选优失败。
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stage9.system_eval import (  # noqa: E402
    evaluate_system_doc,
    load_preregistration,
    run_system_chunks,
    system_macro_and_select,
)


def _git_head():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parents[1]), timeout=10)
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="系统侧 max_chars dev 选优（G⑦；预注册核对 + "
                    "gold revision 运行时绑定）")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--gold-revision", required=True,
                        help="G⑥ 冻结签发的 gold revision（强制——G⑥ 前"
                             "真实语料参数探索被双重禁止；合成测试用"
                             " synthetic-*）")
    parser.add_argument("--split", default="dev",
                        help="参与的 split（预注册固定 dev）")
    parser.add_argument("--report", help="报告 JSON 落盘路径")
    parser.add_argument("--json", action="store_true",
                        help="stdout 输出完整 JSON（默认摘要表）")
    args = parser.parse_args(argv)

    prereg, prereg_sha = load_preregistration()
    if args.split != prereg["participating_split"]:
        print("split %r 不在预注册参与集（固定 %r；comparison/holdout "
              "禁止调参）" % (args.split, prereg["participating_split"]),
              file=sys.stderr)
        return 2

    manifest_path = Path(args.manifest)
    try:
        manifest_raw = manifest_path.read_bytes()
        manifest = json.loads(manifest_raw.decode("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print("manifest 读取失败: %s" % exc, file=sys.stderr)
        return 2
    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    if manifest_sha != prereg["manifest_sha256_expected"]:
        print("manifest SHA-256 与预注册期望不符：\n  got      %s\n"
              "  expected %s\n（冻结层被改动须重新裁决，拒绝运行）"
              % (manifest_sha, prereg["manifest_sha256_expected"]),
              file=sys.stderr)
        return 2

    grid = prereg["candidate_grid"]
    dev_docs = [d for d in manifest.get("docs", [])
                if d.get("split") == prereg["participating_split"]]
    dev_ids = [d["doc_id"] for d in dev_docs]
    if sorted(dev_ids) != sorted(prereg["dev_doc_ids"]):
        print("manifest dev 集与预注册 dev_doc_ids 不符：\n  manifest:"
              " %s\n  prereg:  %s" % (sorted(dev_ids),
                                      sorted(prereg["dev_doc_ids"])),
              file=sys.stderr)
        return 2
    files_dir = manifest_path.parent / "files"

    doc_reports = []
    na_distribution = {}
    for doc in dev_docs:
        doc_id = doc["doc_id"]
        ann_path = Path(args.annotations) / (doc_id + ".json")
        try:
            ann = json.loads(ann_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print("标注读取失败 %s: %s" % (ann_path, exc), file=sys.stderr)
            return 2
        if ann.get("doc_id") != doc_id:
            print("doc_id mismatch: %s" % ann_path, file=sys.stderr)
            return 2
        source = (files_dir / ("%s.%s" % (doc_id, doc["format"]))).resolve()
        chunks_by_param = {}
        na_by_param = {}
        for p in grid:
            chunks, reason = run_system_chunks(source, p)
            if chunks is None:
                na_by_param[p] = reason
            else:
                chunks_by_param[p] = chunks
        doc_reports.append(
            evaluate_system_doc(ann, chunks_by_param, grid, na_by_param))
        for p, reason in na_by_param.items():
            na_distribution[reason] = na_distribution.get(reason, 0) + 1

    macro, best_p, best_v = system_macro_and_select(doc_reports, grid)
    if best_p is None:
        print("全网格无任何非 N/A 文档——选优失败（不产生 N*=null 的"
              "伪结果）", file=sys.stderr)
        return 2

    payload = {
        "tool": "stage9_system_select",
        "preregistration": prereg["preregistration"],
        "preregistration_sha256": prereg_sha,
        "param": prereg["param"],
        "candidate_grid": grid,
        "selection_rule": ("macro ARI 最大者；平局取最小 %s（预注册"
                           " 2026-09-07 冻结）" % prereg["param"]),
        "participating_split": prereg["participating_split"],
        "doc_count": len(doc_reports),
        "na_distribution": na_distribution,
        "selection": {"max_chars": best_p, "macro_ari": best_v},
        "macro": {str(p): macro[p] for p in grid},
        "provenance": {
            "manifest_sha256": manifest_sha,
            "gold_revision": args.gold_revision,
            "preregistration_sha256": prereg_sha,
            "implementation_commit": _git_head(),
            "edge_handling": prereg["edge_handling"],
        },
        "docs": doc_reports,
    }
    if args.report:
        rp = Path(args.report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        with open(rp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        print("split=%s docs=%d grid=%s gold_revision=%s"
              % (args.split, len(doc_reports), grid, args.gold_revision))
        print("N/A 分布: %s" % (json.dumps(na_distribution,
                                           ensure_ascii=False) or "{}"))
        for p in grid:
            v = macro[p]
            print("  max_chars=%-5d macro-ARI=%s"
                  % (p, "-" if v is None else "%.4f" % v))
        print("选优: max_chars*=%d macro=%s（平局取最小，预注册规则）"
              % (best_p, "%.4f" % best_v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
