r"""cli parse/validate md：OK 摘要行、
Schema 校验通过、空文件错误 JSON 与
退出码（Round 1802）。

新角度：R1801 锁余块终结——**CLI 层
（此前轮次全走 process_single）：parse
md → '[OK] in → out (elements=2,
chunks=1, warnings=0)' exit 0；validate
独立子命令 → '通过 Schema 校验' exit
0；空 md → stdout 结构化错误 JSON
（code no_extracted_elements、
details.warnings 含 md_no_content、
source_type markdown）exit 1**零覆盖：

- **parse**：exit 0 + out.json 落盘
- **validate**：exit 0 中文通过语
- **空文件**：exit 1 + 可解析错误 JSON
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


def test_cli_parse_md_ok(tmp_path):
    src = tmp_path / "d.md"
    src.write_text("## T\n\nbody\n", encoding="utf-8")
    out = tmp_path / "out.json"
    r = _cli("parse", str(src), "-o", str(out),
             "--parser", "markdown")
    assert r.returncode == 0
    assert "[OK]" in r.stdout
    assert "elements=2" in r.stdout
    assert "chunks=1" in r.stdout
    assert "warnings=0" in r.stdout
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["elements"]) == 2


def test_cli_validate_ok(tmp_path):
    src = tmp_path / "d.md"
    src.write_text("## T\n\nbody\n", encoding="utf-8")
    out = tmp_path / "out.json"
    _cli("parse", str(src), "-o", str(out),
         "--parser", "markdown")
    r = _cli("validate", str(out))
    assert r.returncode == 0
    assert "Schema" in r.stdout


def test_cli_empty_md_error_json(tmp_path):
    src = tmp_path / "e.md"
    src.write_text("", encoding="utf-8")
    out = tmp_path / "e.json"
    r = _cli("parse", str(src), "-o", str(out),
             "--parser", "markdown")
    assert r.returncode == 1
    assert not out.exists()
    stream = r.stdout if "{" in r.stdout else r.stderr
    i = stream.find("{")
    data = json.loads(stream[i:])
    assert data["errors"][0]["code"] == (
        "no_extracted_elements")
    assert data["errors"][0]["details"][
        "source_type"] == "markdown"
    warn_codes = [w["code"] for w in
                  data["errors"][0]["details"]["warnings"]]
    assert "md_no_content" in warn_codes
