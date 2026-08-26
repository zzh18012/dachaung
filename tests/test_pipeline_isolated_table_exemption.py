r"""pipeline 真表格豁免 max_chars：strategy
isolated_table 永不切分（Round 1772）。

新角度：R1771 锁超限标题——**md/html 真
表格（≥2 列）无论多长永不切分：1725 字符
单 chunk、strategy 'isolated_table'；R1725
所谓"表格切分"实为 1 列退化段落（元素
metadata {} 无 table 标记）——修正此前
认知**零覆盖：

- **'| a |' 1 列**：paragraph（metadata
  {}）——R1725 案例真身
- **2 列 1725 字符 md 表**：单 chunk
  strategy 'isolated_table'
- **html 122 行表**：同样 isolated_table
  单块不切
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_one_col_is_paragraph_not_table(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "| a |\n| --- |\n| " + "w " * 500 + " |\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.metadata) for e in doc.elements] == [
        ("paragraph", {})]


def test_real_table_never_split_md(tmp_path):
    rows = ["| h1 | h2 |", "| --- | --- |"] + [
        f"| v{i} | w{i} |" for i in range(120)]
    p = tmp_path / "d.md"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.type for e in doc.elements] == ["table"]
    assert [(len(c.text), c.metadata)
            for c in doc.chunks] == [
        (1725, {"strategy": "isolated_table",
                "max_chars": 800, "char_count": 1725})]


def test_real_table_never_split_html(tmp_path):
    trs = "".join(
        f"<tr><td>v{i}</td><td>w{i}</td></tr>"
        for i in range(120))
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><th>h1</th><th>h2</th></tr>"
        + trs + "</table>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [e.type for e in doc.elements] == ["table"]
    assert len(doc.chunks) == 1
    assert doc.chunks[0].metadata["strategy"] == (
        "isolated_table")
    assert len(doc.chunks[0].text) == 1725
