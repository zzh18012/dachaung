# -*- coding: utf-8 -*-
"""Stage 6 批次 5 holdout（holdout-table-linearization）一次性首跑。

纪律（docs/table-linearization-contract.md §5 + 裁决⑤ 沿用）：
- 期望 elements/tables 在本批任何 parser 运行于这些夹具之前手工推导
  冻结（samples/synthetic/holdout-table/expectations.json），本脚本只比对；
- 夹具字节固定：运行时校验 sha256 与冻结登记一致，漂移即拒跑；
- 干净工作树、固定干净 SHA 下运行一次，报告封存 outputs/，永不重跑。

比对口径：schema_version（期望 0.4.0）、逐 element 的
element_id/type/source_locator/content 全等；table element 额外比对
metadata 的 row_count/col_count/source 子集。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOLDOUT_DIR = ROOT / "samples" / "synthetic" / "holdout-table"
OUT = ROOT / "outputs" / "holdout-table-v1-firstrun.json"

_TABLE_META_KEYS = ("row_count", "col_count", "source", "table_index")


def _die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if OUT.exists():
        _die(f"holdout 首跑报告已存在，禁止重跑: {OUT}")
    if not HOLDOUT_DIR.is_dir():
        _die(f"holdout 目录不存在: {HOLDOUT_DIR}")

    if subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT,
        capture_output=True, text=True,
    ).stdout.strip():
        _die("工作树不干净（存在未提交改动），holdout 首跑要求干净树")
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True,
    ).stdout.strip()

    exp_path = HOLDOUT_DIR / "expectations.json"
    spec = json.loads(exp_path.read_text(encoding="utf-8"))

    sys.path.insert(0, str(ROOT))
    from app.pipeline import process_single  # noqa: E402

    fixtures_out: dict[str, dict] = {}
    all_pass = True
    for name, fspec in spec["fixtures"].items():
        fpath = HOLDOUT_DIR / name
        fixture_sha = _sha256(fpath)
        if fixture_sha != fspec["fixture_sha256"]:
            _die(
                f"{name} sha256 漂移: got {fixture_sha}, "
                f"expect {fspec['fixture_sha256']}（裁决⑤ 字节固定，禁止重新生成）"
            )
        document, errors = process_single(
            fpath, None, parser_name=fspec["parser"], write_json=False,
        )
        result: dict = {
            "fixture_sha256": fixture_sha,
            "parser": fspec["parser"],
            "errors": [str(e) for e in errors],
            "checks": {},
        }
        if errors or document is None:
            result["pass"] = False
            all_pass = False
            fixtures_out[name] = result
            continue

        d = document.to_dict()
        got = []
        for e in d["elements"]:
            entry = {
                "element_id": e["element_id"],
                "type": e["type"],
                "source_locator": e["source_locator"],
                "content": e["content"],
            }
            if e["type"] == "table":
                entry["metadata"] = {
                    k: e["metadata"][k]
                    for k in _TABLE_META_KEYS if k in e["metadata"]
                }
            got.append(entry)
        expected = fspec["expected_elements"]
        checks = {
            "schema_version": d["schema_version"] == fspec["expected_schema_version"],
            "element_count": len(got) == len(expected),
            "elements_exact": got == expected,
        }
        result["checks"] = checks
        result["got_schema_version"] = d["schema_version"]
        result["got_elements"] = got
        result["pass"] = all(checks.values())
        all_pass = all_pass and result["pass"]
        fixtures_out[name] = result

    report = {
        "holdout": spec["holdout"],
        "kind": spec["kind"],
        "policy": "one-shot first run at clean SHA; sealed to outputs/; never re-run",
        "git_sha": sha,
        "expectations_sha256": _sha256(exp_path),
        "expected_schema_version": "0.4.0",
        "ran_at_utc": datetime.now(timezone.utc).isoformat(),
        "all_pass": all_pass,
        "fixtures": fixtures_out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"all_pass={all_pass} git_sha={sha}")
    print(f"report sealed: {OUT}")
    print(f"report sha256: {_sha256(OUT)}")
    raise SystemExit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
