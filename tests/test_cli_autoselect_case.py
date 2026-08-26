r"""cli 扩展名大小写不敏感自动选择：
.HTML/.Txt/.Md 全识别（Round 1814）。

新角度：R1813 锁崩溃边界——**自动选择
对后缀大小写不敏感：.HTML→html、
.TXT→text、.Md→markdown（INFO+OK+exit
0）；大写 .MD 的 JSON source_type
'markdown'（后缀 lower 后判型）**零
覆盖：

- **三种大小写变体**：各自映射正确
- **.MD source_type**：'markdown'
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


def test_autoselect_uppercase_extensions(
        tmp_path):
    cases = [
        ("D.HTML", "<p>a</p>", "html"),
        ("D.TXT", "x", "text"),
        ("D.Md", "## T", "markdown"),
    ]
    for name, content, parser in cases:
        src = tmp_path / name
        src.write_text(content, encoding="utf-8")
        out = tmp_path / (name + ".json")
        r = _cli("parse", str(src), "-o", str(out))
        assert r.returncode == 0, name
        assert "自动选择" in r.stderr, name
        assert parser in r.stderr, name
        assert "[OK]" in r.stdout, name


def test_uppercase_md_source_type(tmp_path):
    src = tmp_path / "D.MD"
    src.write_text("## T\n", encoding="utf-8")
    out = tmp_path / "o.json"
    r = _cli("parse", str(src), "-o", str(out))
    assert r.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_type"] == "markdown"
