r"""md 段落空白：内部行缩进保留 / 两端剥 / 缩进行非代码（Round 1874）。

新角度（probe 实证；text 解析器同型已锁（R1713 'a\\n b' 与
text_edges8 内部缩进保留），**md 侧**内部缩进保留、两端剥、
4 空格/tab 缩进行退化为 paragraph 全库零覆盖——CommonMark 缩进
代码块在此实现不存在）：
- **内部缩进保留**：'a\\n    b' → 'a\\n    b'（第二行 4 空格
  原样在 content，不是 code_block）
- **两端剥**：'  a\\nb  ' → 'a\\nb'（块级 strip 仅作用于边界行）
- **缩进行成段**：'    code' / '\\tcode tab' → paragraph
  'code' / 'code tab'（缩进剥净，无缩进代码语义）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, name: str, body: str) -> dict:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name="markdown")
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_md_paragraph_interior_indent_preserved(tmp_path: Path):
    data = _run(tmp_path, "a.md", "a\n    b\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "a\n    b", {})]


def test_md_paragraph_boundary_stripped(tmp_path: Path):
    data = _run(tmp_path, "b.md", "  a\nb  \n")
    assert [(e["type"], e["content"])
            for e in data["elements"]] == [
        ("paragraph", "a\nb")]


def test_indented_line_degrades_to_stripped_paragraph(tmp_path: Path):
    data = _run(tmp_path, "c.md", "    code\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "code", {})]

    data = _run(tmp_path, "d.md", "\tcode tab\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "code tab", {})]
