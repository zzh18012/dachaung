# -*- coding: utf-8 -*-
"""Stage 7 批次 10（P2 PDF 侧标注解锁）评测归因验证。

对照批次 9 封存基线 outputs/evaluation-batch9-figcap-unlock.json
逐字段 diff 新跑 outputs/evaluation-batch10-pdf-unlock.json。

预期变化（批次 10 核心任务 + 两个可归因副作用，逐项核对）：
- per_doc[1]（DC-MVP-001-PDF）.metrics.figure_caption_{precision,recall,
  f1} 的 value 与 reason：null+no_annotation → 1.0+null（Option A 解锁）
- per_doc[1].metrics.chunk_boundary_{precision,recall,f1} 的 reason：
  no_annotation → no_ground_truth_anchors（annotation 文件出现但未标注
  anchors 的降级路径迁移；value 两轮均为 null 不变）
排除集（运行环境）：
- wall_time_seconds.total / provenance.git_commit / run_timestamp_iso
必然不变断言：
- provenance.evaluator_version 维持 1.8
- per_doc[0]（docx）全部字段零差异（figure_caption_* 维持 1.0）
- 除上述 9 条指标路径外，其余全部 .metrics. 路径与 summary/devset 零差异
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "outputs" / "evaluation-batch9-figcap-unlock.json"
NEW = ROOT / "outputs" / "evaluation-batch10-pdf-unlock.json"

_EXCLUDED_PROV = {"git_commit", "run_timestamp_iso"}

_FIGCAP_PATHS = {
    f".per_doc[1].metrics.figure_caption_{k}.{f}"
    for k in ("precision", "recall", "f1")
    for f in ("value", "reason")
}
_CHUNK_REASON_PATHS = {
    f".per_doc[1].metrics.chunk_boundary_{k}.reason"
    for k in ("precision", "recall", "f1")
}
_ALLOWED = _FIGCAP_PATHS | _CHUNK_REASON_PATHS

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
    return path in _ALLOWED


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
        any(".per_doc[1].metrics.figure_caption_precision.value" in d for d in diffs),
        any(".per_doc[1].metrics.figure_caption_precision.reason" in d for d in diffs),
        all(any(p in d for d in diffs) for p in sorted(_FIGCAP_PATHS)),
        all(any(p in d for d in diffs) for p in sorted(_CHUNK_REASON_PATHS)),
    ]
    must_not_change = [
        not any("provenance.evaluator_version" in d for d in diffs),
        not any(
            d.startswith(".per_doc[0].") and ".wall_time_seconds." not in d
            for d in diffs
        ),
        not any(
            d for d in diffs
            if ".metrics." in d and d.split(":", 1)[0] not in _ALLOWED
        ),
    ]
    print(f"total field diffs: {len(diffs)}")
    print(f"allowed (exclusion set, with attribution): {len(allowed)}")
    for d in sorted(allowed):
        print(f"  [excluded] {d}")
    print(f"unexpected diffs: {len(real)}")
    for d in real[:50]:
        print(f"  [DIFF] {d}")
    print(f"must-change (env×2 + figcap×6 + chunk_reason×3): {must_change}")
    print(f"must-not-change (evaluator_version, docx, other_metrics): "
          f"{must_not_change}")
    if real or not all(must_change) or not all(must_not_change):
        print("VERDICT: FAIL")
        raise SystemExit(1)
    print("VERDICT: PASS — 仅 PDF figure_caption_* 解锁（6 路径）+ "
          "chunk_boundary reason 迁移（3 路径）+ 运行环境；"
          "docx 与其余指标族零变化")


if __name__ == "__main__":
    main()
