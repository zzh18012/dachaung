r"""br 在结构元素里：文本流变空格、表单元格内丢弃（Round 1880）。

新角度（probe 实证；edges.py:423 只弱断言 p 内 br（any 命中），
heading/li/bq/pre/td 内 br 的**精确内容**与 img 冲刷对照零覆盖）：
- **结构元素保型**：'<h1>a<br>b</h1>' / '<li>a<br>b</li>' /
  '<blockquote>a<br>b</blockquote>' → 单元素 'a b'——br 变空格
  不冲刷（与 img 的类型丢失形成对照）
- **表单元格内丢弃**：'<td>a<br>b</td>' → 单元格 'ab'——br
  零贡献（无空格直接拼接）
- **pre 内同样空格**：'<pre>a<br>b</pre>' → 'a b' kind
  preformatted
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, body: str) -> dict:
    p = tmp_path / "a.html"
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / "a.json"
    _, errs = process_single(p, out, parser_name="html")
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_br_space_keeps_structural_type(tmp_path: Path):
    cases = [
        ("<h1>a<br>b</h1>", [("heading", "a b", {"level": 1})]),
        ("<ul><li>a<br>b</li></ul>",
         [("list_item", "a b",
           {"ordered": False, "marker": "unordered"})]),
        ("<blockquote>a<br>b</blockquote>",
         [("paragraph", "a b", {"kind": "blockquote"})]),
    ]
    for body, expected in cases:
        data = _run(tmp_path, body)
        assert [(e["type"], e["content"], e["metadata"])
                for e in data["elements"]] == expected, body


def test_br_dropped_in_table_cell(tmp_path: Path):
    data = _run(tmp_path, "<table><tr><td>a<br>b</td></tr></table>")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("table", "| ab |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_br_space_in_pre(tmp_path: Path):
    data = _run(tmp_path, "<pre>a<br>b</pre>")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "a b", {"kind": "preformatted"})]
