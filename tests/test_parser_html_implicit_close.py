r"""隐式闭合：h1<h2 / li<li 开新元素，table 无 tr 整表错误（Round 1871）。

新角度（probe 实证；R1870 锁 p 的同 kind 忽略合并，本批对照
h/li **异 kind/同 kind 开新**的隐式闭合；'<table><td>'（无 tr）
edges14 只锁有 tr 的未闭合形态，无 tr 形态 + pipeline 级结构化
错误全库零覆盖）：
- **标题隐式闭合**：'<h1>a<h2>b</h2><p>t</p>' → 两个 heading
  （level 1/2），h2 的 section_path 'a > b'（畸形嵌套仍建立
  层级栈），段落 't' 继承 'a > b'
- **li 隐式闭合**：'<li>a<li>b'（裸）与 '<ul><li>a<li>b</ul>'
  → 两个 list_item（与 p 的合并形成对照）
- **表无 tr**：'<table><td>x</td></table>' → 整表消失，
  pipeline 级 no_extracted_elements 结构化错误 + 不写盘
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, body: str):
    p = tmp_path / "a.html"
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / "a.json"
    _, errs = process_single(p, out, parser_name="html")
    return errs, out


def test_sibling_headings_implicit_close(tmp_path: Path):
    _, out = _run(tmp_path, "<h1>a<h2>b</h2><p>t</p>")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [(e["type"], e["content"], e["metadata"]) for e in data["elements"]] == [
        ("heading", "a", {"level": 1}),
        ("heading", "b", {"level": 2}),
        ("paragraph", "t", {}),
    ]
    paths = [e["source_locator"]["section_path"]
             for e in data["elements"]]
    assert paths == ["a", "a > b", "a > b"]


def test_sibling_li_implicit_close(tmp_path: Path):
    for name, body in (("a", "<li>a<li>b"),
                       ("b", "<ul><li>a<li>b</ul>")):
        _, out = _run(tmp_path, body)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert [(e["type"], e["content"], e["metadata"])
                for e in data["elements"]] == [
            ("list_item", "a", {"ordered": False, "marker": "unordered"}),
            ("list_item", "b", {"ordered": False, "marker": "unordered"}),
        ], name


def test_table_td_without_tr_structured_error(tmp_path: Path):
    errs, out = _run(tmp_path, "<table><td>x</td></table>")
    assert [e.code for e in errs] == ["no_extracted_elements"]
    assert errs[0].details["warnings"][0]["code"] == "html_no_content"
    assert not out.exists()
