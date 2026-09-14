r"""引用内部空白与表单元格多空格（Round 1875）。

新角度（probe 实证，grep 零覆盖；R1874 锁普通段落内部/两端，
本批锁 **blockquote 容器**与 **pipe 表单元格**的同类形态）：
- **bq 内部缩进保留**：'> a\\n>     b' → 'a\\n    b'（标记 '>'
  剥后内部行 4 空格原样）
- **bq 两端剥**：'>   lead\\n> trail   ' → 'lead\\ntrail'
  （标记后空格与块两端一并剥净）
- **表单元格多空格**：'| a   b |' → content 逐字保留（管道表
  不折叠单元格内部空格）
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


def test_bq_interior_indent_preserved(tmp_path: Path):
    data = _run(tmp_path, "a.md", "> a\n>     b\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "a\n    b", {"kind": "blockquote"})]


def test_bq_boundary_stripped(tmp_path: Path):
    data = _run(tmp_path, "b.md", ">   lead\n> trail   \n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "lead\ntrail", {"kind": "blockquote"})]


def test_table_cell_multi_space_preserved(tmp_path: Path):
    body = "| a   b | c   d |\n| --- | --- |\n| 1   2 | 3 |\n"
    data = _run(tmp_path, "c.md", body)
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("table", body.rstrip("\n"),
         {"row_count": 2, "col_count": 2,
          "source": "markdown_pipe_table"})]
