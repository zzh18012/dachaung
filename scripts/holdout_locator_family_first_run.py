# -*- coding: utf-8 -*-
"""Stage 6 批次 3 holdout（holdout-locator-family）一次性首跑。

纪律（docs/locator-kvfs-contract.md §6 + ADOPTION.md 十九）：
- 期望 elements 在实现前手工推导冻结（expectations-elements.json，
  sha256 记录于 ADOPTION.md），本脚本只比对、不推导；
- 必须在干净工作树、固定干净 SHA 下运行一次，报告封存 outputs/，
  之后永不重跑（输出文件已存在即拒绝）。

比对口径：每 fixture 的 parser、schema_version（期望 0.3.0）、
逐 element 的 element_id / type / source_locator 全字段相等。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOLDOUT = ROOT / "samples/private/holdout-locator-family"
OUT = ROOT / "outputs/holdout-locatorfamily-v1-firstrun.json"


def _die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if OUT.exists():
        _die(f"holdout 首跑报告已存在，禁止重跑: {OUT}")
    if not HOLDOUT.is_dir():
        _die(f"holdout 目录不存在: {HOLDOUT}")

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
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
        capture_output=True, text=True,
    ).stdout.strip()
    if dirty:
        _die("工作树不干净")

    exp_path = HOLDOUT / "expectations-elements.json"
    exp_doc = json.loads(exp_path.read_text(encoding="utf-8"))

    sys.path.insert(0, str(ROOT))
    from app.pipeline import process_single  # noqa: E402

    fixtures_out: dict[str, dict] = {}
    all_pass = True
    for name, spec in exp_doc["fixtures"].items():
        fpath = HOLDOUT / name
        document, errors = process_single(
            fpath, None, parser_name=spec["parser"], write_json=False,
        )
        result: dict = {
            "fixture_sha256": _sha256(fpath),
            "parser": spec["parser"],
            "errors": [str(e) for e in errors],
            "checks": {},
        }
        if errors or document is None:
            result["pass"] = False
            all_pass = False
            fixtures_out[name] = result
            continue

        d = document.to_dict()
        got = [
            {
                "element_id": e["element_id"],
                "type": e["type"],
                "source_locator": e["source_locator"],
            }
            for e in d["elements"]
        ]
        checks = {
            "schema_version": d["schema_version"] == spec["expected_schema_version"],
            "element_count": len(got) == len(spec["expected_elements"]),
            "elements_exact": got == spec["expected_elements"],
        }
        result["checks"] = checks
        result["got_schema_version"] = d["schema_version"]
        result["got_elements"] = got
        result["pass"] = all(checks.values())
        all_pass = all_pass and result["pass"]
        fixtures_out[name] = result

    report = {
        "holdout": "holdout-locator-family",
        "kind": "batch3-locator-family-first-run",
        "policy": "one-shot first run at clean SHA; sealed to outputs/; never re-run",
        "git_sha": sha,
        "expectations_sha256": _sha256(exp_path),
        "expected_schema_version": "0.3.0",
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
