r"""cli inspect：摘要行、聚合统计（元素/
块/引用 min-max-avg）、缺文件 exit 2
（Round 1807）。

新角度：R1806 锁 JSON 成功态——**inspect
子命令输出结构化摘要：document_id/
source（type+hash 16 前缀…）/counts/
elements by type/element text（total+
avg）/chunk text（min max avg total）/
chunk refs；'a bb ccc' 三段合一块 →
element total=6 avg=2、chunk 8、refs
min=3 avg=3.0；缺文件 exit 2 + '[ERROR]
文件不存在'**零覆盖：

- **md 单标题**：heading=1、chunk
  min=1 max=1
- **三段合并**：聚合值全对
- **缺文件**：exit 2（与 parse 的
  exit 1 分层）
"""

from __future__ import annotations

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


def _parse(tmp_path, name, text, parser):
    src = tmp_path / name
    src.write_text(text, encoding="utf-8")
    out = tmp_path / (name + ".json")
    r = _cli("parse", str(src), "-o", str(out),
             "--parser", parser)
    assert r.returncode == 0
    return out


def test_cli_inspect_summary_lines(tmp_path):
    out = _parse(tmp_path, "d.md", "## T\n",
                 "markdown")
    r = _cli("inspect", str(out))
    assert r.returncode == 0
    for frag in ("document_id: doc-",
                 "type=markdown",
                 "counts:      elements=1 chunks=1",
                 "elements by type: heading=1",
                 "chunk text:  min=1 max=1 avg=1 total=1",
                 "chunk refs:  min=1 max=1 avg=1.0"):
        assert frag in r.stdout, frag


def test_cli_inspect_aggregates(tmp_path):
    out = _parse(tmp_path, "m.txt",
                 "a\n\nbb\n\nccc\n", "text")
    r = _cli("inspect", str(out))
    assert r.returncode == 0
    for frag in ("elements=3 chunks=1",
                 "elements by type: paragraph=3",
                 "element text: total_chars=6 avg=2",
                 "chunk text:  min=8 max=8 avg=8 total=8",
                 "chunk refs:  min=3 max=3 avg=3.0"):
        assert frag in r.stdout, frag


def test_cli_inspect_missing_exit2(tmp_path):
    r = _cli("inspect",
             str(tmp_path / "nope.json"))
    assert r.returncode == 2
    assert "文件不存在" in r.stderr
