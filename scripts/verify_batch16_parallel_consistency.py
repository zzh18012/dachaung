"""批次 16 并行一致性验证：顺序 vs 并行评测报告对比。

用法：
    python scripts/verify_batch16_parallel_consistency.py <seq.json> <par.json>

验收口径（批次 16 步骤 1 裁决）：
- per_doc 按 doc_id 排序后逐字节相同（wall_time_seconds 除外）
- summary / devset / expected_failures / report_version 相同
- provenance 除 run_timestamp_iso 与 git 状态（commit/dirty 随运行时刻变化）外相同

退出码：0 一致 / 1 不一致 / 2 用法错误。
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

# Windows 控制台 utf-8（与 app/evaluation CLI 同款处理）
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass

PROVENANCE_VOLATILE_KEYS = ("run_timestamp_iso", "git_commit", "git_dirty")


def _strip_volatile(report: dict) -> dict:
    r = copy.deepcopy(report)
    for d in r.get("per_doc", []):
        d.pop("wall_time_seconds", None)
    prov = r.get("provenance", {})
    for k in PROVENANCE_VOLATILE_KEYS:
        prov.pop(k, None)
    return r


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    seq_path, par_path = Path(argv[1]), Path(argv[2])
    for p in (seq_path, par_path):
        if not p.is_file():
            print(f"[ERROR] 报告不存在: {p}", file=sys.stderr)
            return 2

    a = json.loads(seq_path.read_text(encoding="utf-8"))
    b = json.loads(par_path.read_text(encoding="utf-8"))

    problems: list[str] = []

    pa = sorted(a.get("per_doc", []), key=lambda d: d.get("doc_id", ""))
    pb = sorted(b.get("per_doc", []), key=lambda d: d.get("doc_id", ""))
    ids_a = [d.get("doc_id") for d in pa]
    ids_b = [d.get("doc_id") for d in pb]
    if ids_a != ids_b:
        problems.append(f"per_doc doc_id 集合不同: {ids_a} vs {ids_b}")
    else:
        for d1, d2 in zip(pa, pb):
            d1c = copy.deepcopy(d1)
            d2c = copy.deepcopy(d2)
            d1c.pop("wall_time_seconds", None)
            d2c.pop("wall_time_seconds", None)
            if d1c != d2c:
                for k in d1c:
                    if d1c.get(k) != d2c.get(k):
                        problems.append(
                            f"per_doc[{d1.get('doc_id')}].{k} 不同: "
                            f"{json.dumps(d1c.get(k), ensure_ascii=False)[:200]} vs "
                            f"{json.dumps(d2c.get(k), ensure_ascii=False)[:200]}"
                        )

    for key in ("report_version", "summary", "devset", "expected_failures"):
        if a.get(key) != b.get(key):
            problems.append(f"{key} 不同")

    prov_a = {k: v for k, v in a.get("provenance", {}).items() if k not in PROVENANCE_VOLATILE_KEYS}
    prov_b = {k: v for k, v in b.get("provenance", {}).items() if k not in PROVENANCE_VOLATILE_KEYS}
    if prov_a != prov_b:
        problems.append(
            f"provenance（剔除 {PROVENANCE_VOLATILE_KEYS}）不同: {prov_a} vs {prov_b}"
        )

    if problems:
        print("[FAIL] 并行一致性验证未通过：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(
        f"[OK] 并行一致性验证通过：{len(pa)} 文档 per_doc 排序后逐字节相同"
        f"（wall_time_seconds 除外）；summary/devset/expected_failures/provenance 一致。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
