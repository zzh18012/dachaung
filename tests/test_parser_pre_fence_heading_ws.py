r"""pre 剥两端 / fence 全逐字 / 标题内部多空格（Round 1876）。

新角度（probe 实证，grep 零覆盖；R1874/75 锁段落与 bq 两端剥，
本批三向对照——**同为"保留格式"语义的 pre 与 fence 对首行缩进
处理不同**）：
- **pre 剥两端**：'<pre>  a\\n    b  </pre>' → 'a\\n    b'
  （两端空格剥净，内部换行+缩进保留）
- **fence 全逐字**：'```\\n  a\\n    b\\n```' → '  a\\n    b'
  （首行前导空格保留——与 pre 形成对照；edges17 只锁纯空白体）
- **标题内部多空格**：'# a    b' → 'a    b'（不折叠）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, name: str, body: str, parser: str) -> dict:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name=parser)
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_pre_strips_ends_keeps_interior(tmp_path: Path):
    data = _run(tmp_path, "a.html", "<pre>  a\n    b  </pre>", "html")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "a\n    b", {"kind": "preformatted"})]


def test_fence_content_fully_verbatim(tmp_path: Path):
    data = _run(tmp_path, "b.md", "```\n  a\n    b\n```\n", "markdown")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "  a\n    b",
         {"kind": "code_block", "language": ""})]


def test_heading_interior_multi_space(tmp_path: Path):
    data = _run(tmp_path, "c.md", "# a    b\n", "markdown")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("heading", "a    b", {"level": 1})]
