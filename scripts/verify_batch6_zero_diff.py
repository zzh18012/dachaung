# -*- coding: utf-8 -*-
"""Stage 6 批次 6 零差异验证（docs/relation-consumption-contract.md §4）。

对照批次 4 封存基线 outputs/evaluation-captionrelation-dev-acceptance.json
（git_commit=5750aef）逐字段 diff 新跑 outputs/evaluation-batch6-zerodiff-check.json。

排除集（契约 §4，逐项归因）：
- wall_time_seconds.total：计时
- provenance.git_commit / run_timestamp_iso：运行环境
- provenance.evaluator_version：1.7→1.8（契约 §5）
- per_doc[].metrics.figure_caption_{precision,recall,f1}.reason：
  parser_does_not_emit_relations → no_annotation_pairs（裁决③移除过时理由）

其余字段必须完全一致（value 与 reason 均比）。任何越界差异 → 退出码 1。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "outputs" / "evaluation-captionrelation-dev-acceptance.json"
NEW = ROOT / "outputs" / "evaluation-batch6-zerodiff-check.json"

_EXCLUDED_PROV = {"git_commit", "run_timestamp_iso", "evaluator_version"}
_FC_KEYS = ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1")

diffs: list[str] = []


def walk(path: str, a, b) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                diffs.append(f"{path}.{k}: only-in-new={b[k]!r}")
            elif k not in b:
                diffs.append(f"{path}.{k}: only-in-old={a[k]!r}")
            else:
                walk(f"{path}.{k}", a[k], b[k])
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(f"{path}: len {len(a)} != {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(f"{path}[{i}]", x, y)
    else:
        if a != b:
            diffs.append(f"{path}: {a!r} != {b!r}")


def excluded(diff_line: str) -> bool:
    path = diff_line.split(":", 1)[0]
    if ".wall_time_seconds." in path and path.endswith(".total"):
        return True
    if path.startswith(".provenance."):
        return path.split(".")[2] in _EXCLUDED_PROV
    if ".metrics.figure_caption_" in path and path.endswith(".reason"):
        return True
    return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    old = json.loads(BASE.read_text(encoding="utf-8"))
    new = json.loads(NEW.read_text(encoding="utf-8"))

    walk("", old, new)

    real = [d for d in diffs if not excluded(d)]
    allowed = [d for d in diffs if excluded(d)]

    # 排除集"必然不同"的断言：evaluator_version 与 figure_caption reason
    # 必须确实变化（证明排除项都有真实归因，而非漏检）
    must_change = [
        any("provenance.evaluator_version" in d for d in diffs),
        any(".metrics.figure_caption_precision.reason" in d for d in diffs),
    ]
    print(f"total field diffs: {len(diffs)}")
    print(f"allowed (exclusion set, with attribution): {len(allowed)}")
    for d in allowed:
        print(f"  [excluded] {d}")
    print(f"unexpected diffs: {len(real)}")
    for d in real[:50]:
        print(f"  [DIFF] {d}")
    print(f"must-change assertions (evaluator_version, fc_reason): {must_change}")
    if real or not all(must_change):
        print("VERDICT: FAIL")
        raise SystemExit(1)
    print("VERDICT: PASS — 除排除集外逐字段一致")


if __name__ == "__main__":
    main()
