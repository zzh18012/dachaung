r"""cli inspect 零块与警告态：纯图无 chunk
行、warnings 计数、错误 JSON 不落盘链
（Round 1808）。

新角度：R1807 锁 inspect 聚合——**纯图
文档 chunks=0：'chunk text'/'chunk
refs' 行整体缺席（零块守卫、无除零）、
element text total_chars=0；空围栏警告
文档 counts warnings=1；失败 parse 不
落盘 → 后续 inspect 必 '文件不存在'
exit 2**零覆盖：

- **纯图**：chunks=0、无 chunk 行
- **警告计数**：warnings=1
- **失败链**：错误 JSON 只在 stderr、
  inspect 接不到
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


def test_inspect_image_only_no_chunk_lines(
        tmp_path):
    src = tmp_path / "d.html"
    src.write_text('<img src="a.png">',
                   encoding="utf-8")
    out = tmp_path / "o.json"
    r = _cli("parse", str(src), "-o", str(out),
             "--parser", "html")
    assert r.returncode == 0
    r = _cli("inspect", str(out))
    assert r.returncode == 0
    assert "counts:      elements=1 chunks=0" \
        in r.stdout
    assert "elements by type: image=1" in r.stdout
    assert "element text: total_chars=0 avg=0" \
        in r.stdout
    assert "chunk text:" not in r.stdout
    assert "chunk refs:" not in r.stdout


def test_inspect_counts_warnings(tmp_path):
    src = tmp_path / "w.md"
    src.write_text("```\n```\n\nbody\n",
                   encoding="utf-8")
    out = tmp_path / "w.json"
    r = _cli("parse", str(src), "-o", str(out),
             "--parser", "markdown")
    assert r.returncode == 0
    r = _cli("inspect", str(out))
    assert r.returncode == 0
    assert "elements=1 chunks=1 relations=0" \
        " warnings=1 errors=0" in r.stdout


def test_failed_parse_chain_to_inspect(tmp_path):
    src = tmp_path / "z.md"
    src.write_text("", encoding="utf-8")
    out = tmp_path / "z.json"
    r = _cli("parse", str(src), "-o", str(out),
             "--parser", "markdown")
    assert r.returncode == 1
    assert not out.exists()
    r = _cli("inspect", str(out))
    assert r.returncode == 2
    assert "文件不存在" in r.stderr
