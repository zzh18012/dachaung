# -*- coding: utf-8 -*-
"""Stage 6 批次 4 holdout（holdout-caption-relation）一次性首跑。

纪律（docs/caption-relation-contract.md §6 + 2026-08-30 裁决⑤）：
- 期望 relations/elements 在本夹具任何 parser 运行之前手工推导冻结
  （samples/synthetic/holdout-caption/expectations.json），本脚本只比对；
- 合成夹具字节固定：运行时校验 sha256 与冻结登记一致，漂移即拒跑，
  且永不调用生成脚本重新生成；
- 必须在干净工作树、固定干净 SHA 下运行一次，报告封存 outputs/，
  之后永不重跑（输出文件已存在即拒绝）。

比对口径：schema_version（期望 0.4.0）、逐 element 的
element_id/type/source_locator（image 的 locator 只投影
family/paragraph_index/section）、全部 caption 的 content、
relations 数组全等（含 metadata.rule 与排序）。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOLDOUT_DIR = ROOT / "samples" / "synthetic" / "holdout-caption"
OUT = ROOT / "outputs" / "holdout-caption-v1-firstrun.json"

_IMAGE_LOCATOR_KEYS = ("family", "paragraph_index", "section")


def _die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _project(locator: dict, etype: str) -> dict:
    if etype == "image":
        return {k: locator[k] for k in _IMAGE_LOCATOR_KEYS if k in locator}
    return locator


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if OUT.exists():
        _die(f"holdout 首跑报告已存在，禁止重跑: {OUT}")
    if not HOLDOUT_DIR.is_dir():
        _die(f"holdout 目录不存在: {HOLDOUT_DIR}")

    # 干净树 + 干净 SHA
    if subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT,
        capture_output=True, text=True,
    ).stdout.strip():
        _die("工作树不干净（存在未提交改动），holdout 首跑要求干净树")
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True,
    ).stdout.strip()

    fixture = HOLDOUT_DIR / "expectations.json"
    spec = json.loads(fixture.read_text(encoding="utf-8"))
    docx_path = HOLDOUT_DIR / spec["fixture"]

    # 裁决⑤：夹具字节固定，漂移即拒绝
    fixture_sha = _sha256(docx_path)
    if fixture_sha != spec["fixture_sha256"]:
        _die(
            f"夹具 sha256 漂移: got {fixture_sha}, "
            f"expect {spec['fixture_sha256']}（裁决⑤ 字节固定，禁止重新生成）"
        )

    sys.path.insert(0, str(ROOT))
    from app.pipeline import process_single  # noqa: E402

    document, errors = process_single(
        docx_path, None, parser_name=spec["parser"], write_json=False,
    )
    result: dict = {
        "fixture": spec["fixture"],
        "fixture_sha256": fixture_sha,
        "parser": spec["parser"],
        "errors": [str(e) for e in errors],
        "checks": {},
    }
    if errors or document is None:
        result["pass"] = False
        report = {
            "holdout": spec["holdout"],
            "kind": spec["kind"],
            "policy": "one-shot first run at clean SHA; sealed to outputs/; never re-run",
            "git_sha": sha,
            "expectations_sha256": _sha256(fixture),
            "expected_schema_version": spec["expected_schema_version"],
            "ran_at_utc": datetime.now(timezone.utc).isoformat(),
            "all_pass": False,
            "fixture_result": result,
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"all_pass=False git_sha={sha}")
        print(f"report sealed: {OUT}")
        print(f"report sha256: {_sha256(OUT)}")
        raise SystemExit(1)

    d = document.to_dict()
    got_elements = [
        {
            "element_id": e["element_id"],
            "type": e["type"],
            "source_locator": _project(e["source_locator"], e["type"]),
        }
        for e in d["elements"]
    ]
    got_captions = {
        e["element_id"]: e["content"]
        for e in d["elements"] if e["type"] == "caption"
    }
    got_relations = [
        {
            "type": r["type"], "from_id": r["from_id"],
            "to_id": r["to_id"], "metadata": r.get("metadata", {}),
        }
        for r in d["relations"]
    ]
    checks = {
        "schema_version": d["schema_version"] == spec["expected_schema_version"],
        "element_count": len(got_elements) == len(spec["expected_elements"]),
        "elements_exact": got_elements == spec["expected_elements"],
        "caption_contents_exact": got_captions == spec["expected_caption_contents"],
        "relations_exact": got_relations == spec["expected_relations"],
    }
    result["checks"] = checks
    result["got_schema_version"] = d["schema_version"]
    result["got_relations"] = got_relations
    result["pass"] = all(checks.values())

    report = {
        "holdout": spec["holdout"],
        "kind": spec["kind"],
        "policy": "one-shot first run at clean SHA; sealed to outputs/; never re-run",
        "git_sha": sha,
        "expectations_sha256": _sha256(fixture),
        "expected_schema_version": spec["expected_schema_version"],
        "ran_at_utc": datetime.now(timezone.utc).isoformat(),
        "all_pass": bool(result["pass"]),
        "fixture_result": result,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"all_pass={result['pass']} git_sha={sha}")
    print(f"report sealed: {OUT}")
    print(f"report sha256: {_sha256(OUT)}")
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
