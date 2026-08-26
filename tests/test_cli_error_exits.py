r"""cli 错误面：缺文件 exit 1 错误 JSON、
非法 --parser exit 2 argparse、validate
坏 JSON exit 1（Round 1804）。

新角度：R1803 锁参数传达——**缺输入
文件 → exit 1 + stderr 结构化 JSON
（code file_not_found、无 details）；
--parser 非法值 → exit 2（argparse 层
拒绝，早于管道——与 process_single 的
unexpected_parser_error 分层）；validate
非 JSON 文件 → exit 1 + '[FAIL] ...
JSON 解析失败'**零覆盖：

- **缺文件**：exit 1、file_not_found
- **--parser nosuch**：exit 2、
  invalid choice 列 6 个合法名
- **坏 JSON**：exit 1、[FAIL] 行
"""

from __future__ import annotations

import json
import subprocess
import sys

from pathlib import Path

PY = sys.executable
ROOT = Path(__file__).resolve().parents[1]


def _cli(*args):
    return subprocess.run(
        [PY, "-m", "app.cli", *args],
        capture_output=True, text=True, cwd=ROOT,
        encoding="utf-8")


def test_cli_missing_file_exit1_json(tmp_path):
    r = _cli(
        "parse", str(tmp_path / "nope.md"),
        "-o", str(tmp_path / "o.json"),
        "--parser", "markdown")
    assert r.returncode == 1
    data = json.loads(r.stderr)
    assert data["errors"][0]["code"] == "file_not_found"
    assert "不存在" in data["errors"][0]["message"]
    assert "details" not in data["errors"][0]
    assert not (tmp_path / "o.json").exists()


def test_cli_invalid_parser_choice_exit2(tmp_path):
    src = tmp_path / "d.txt"
    src.write_text("a\n", encoding="utf-8")
    r = _cli("parse", str(src),
             "-o", str(tmp_path / "o.json"),
             "--parser", "nosuch")
    assert r.returncode == 2
    assert "invalid choice" in r.stderr
    for name in ("fallback", "kreuzberg", "markdown",
                 "html", "text", "ipynb"):
        assert name in r.stderr


def test_cli_validate_bad_json_exit1(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    r = _cli("validate", str(bad))
    assert r.returncode == 1
    combined = r.stdout + r.stderr
    assert "[FAIL]" in combined
    assert "JSON 解析失败" in combined
