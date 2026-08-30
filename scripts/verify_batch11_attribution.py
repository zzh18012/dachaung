# -*- coding: utf-8 -*-
"""Stage 7 批次 11（P3 heading_order 消费指标族）评测归因验证。

对照批次 10 封存基线 outputs/evaluation-batch10-pdf-unlock.json
逐字段 diff 新跑 outputs/evaluation-batch11-heading-unlock.json。

预期变化（批次 11 核心任务，逐项归因）：
- per_doc[0]（DC-MVP-001 docx）.metrics.heading_order_{precision,
  recall,f1} 新增（only-in-new）：value = 0.8889/1.0/0.9412 + reason
  null（Option 1 序列匹配，dry-run 一致）
- per_doc[1]（DC-MVP-001-PDF）.metrics.heading_order_* 新增：
  null + no_ground_truth_headings（annotation 文件批次 10 已挂接，
  但无 heading_order 键 → 降级路径，注意非 no_annotation）
- provenance.evaluator_version：1.8 → 1.9（新增指标族能力封口）
排除集（运行环境）：
- wall_time_seconds.total / provenance.git_commit / run_timestamp_iso
必然不变断言：
- report_version 维持 1.3
- summary 零差异（heading_order_* 不入 macro average，裁决③）
- 除 heading_order_* 新增与 evaluator_version 外，per_doc 两文档
  其余全部字段零差异（figure_caption_*/chunk_boundary_* 等不变）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "outputs" / "evaluation-batch10-pdf-unlock.json"
NEW = ROOT / "outputs" / "evaluation-batch11-heading-unlock.json"

_EXCLUDED_PROV = {"git_commit", "run_timestamp_iso", "evaluator_version"}

diffs: list[str] = []


def walk(path: str, a, b) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                diffs.append(f"{path}.{k}: only-in-new")
            elif k not in b:
                diffs.append(f"{path}.{k}: only-in-old")
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
    if path.startswith(".per_doc[0].metrics.heading_order_"):
        return True
    if path.startswith(".per_doc[1].metrics.heading_order_"):
        return True
    if path.startswith(".provenance."):
        return path.split(".")[2] in _EXCLUDED_PROV
    return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    old = json.loads(BASE.read_text(encoding="utf-8"))
    new = json.loads(NEW.read_text(encoding="utf-8"))

    walk("", old, new)

    real = [d for d in diffs if not excluded(d)]
    allowed = [d for d in diffs if excluded(d)]

    must_change = [
        any("provenance.git_commit" in d for d in diffs),
        any("provenance.run_timestamp_iso" in d for d in diffs),
        any(".provenance.evaluator_version: " in d for d in diffs),
        any(d.startswith(".per_doc[0].metrics.heading_order_precision")
            for d in diffs),
        any(d.startswith(".per_doc[1].metrics.heading_order_precision")
            for d in diffs),
    ]
    must_not_change = [
        not any("report_version" in d for d in diffs),
        not any(d.startswith(".summary.") for d in diffs),
        not any(
            d.startswith(".per_doc[0].") and ".metrics.heading_order_" not in d
            and ".wall_time_seconds." not in d
            for d in diffs
        ),
        not any(
            d.startswith(".per_doc[1].") and ".metrics.heading_order_" not in d
            and ".wall_time_seconds." not in d
            for d in diffs
        ),
        not any(
            d for d in diffs
            if ".metrics." in d and ".metrics.heading_order_" not in d
        ),
    ]
    print(f"total field diffs: {len(diffs)}")
    print(f"allowed (exclusion set, with attribution): {len(allowed)}")
    for d in sorted(allowed):
        print(f"  [excluded] {d}")
    print(f"unexpected diffs: {len(real)}")
    for d in real[:50]:
        print(f"  [DIFF] {d}")
    print(f"must-change (env×2 + evaluator_version + ho keys×2): {must_change}")
    print(f"must-not-change (report_version, summary, other_fields): "
          f"{must_not_change}")
    if real or not all(must_change) or not all(must_not_change):
        print("VERDICT: FAIL")
        raise SystemExit(1)
    print("VERDICT: PASS — 仅 heading_order_* 新增（docx 解锁 + PDF 降级）+ "
          "evaluator_version 1.8→1.9 + 运行环境；report_version/summary/"
          "其余指标族零变化")


if __name__ == "__main__":
    main()
