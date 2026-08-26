r"""pipeline 标题内联处理：md 全 raw 与
html 解码剥除（Round 1750）。

新角度：R1749 锁 image 细节——**md 标题
内容 100% raw（**粗体**/`代码`/实体/竖线/
链接全保留，&amp; 不解码）；html 标题实体
解码（'A & B'）且内联标签剥除（'T x y'）**
零覆盖——同一语义两家解析器相反策略：

- **md '## T **b** `c`' 等 4 例**：content
  原样含标记
- **md '## A &amp; B'**：实体不解码
- **html '&lt;h2&gt;A &amp; B&lt;/h2&gt;' 与
  'T <b>x</b> y'**：解码+剥除
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text, parser):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name=parser)


def test_md_heading_inline_raw(tmp_path):
    for text, want in [
        ("## T **b** `c`\n", "T **b** `c`"),
        ("## a | b\n", "a | b"),
        ("## [t](u)\n", "[t](u)"),
        ("## T *i* _u_ ~~s~~\n", "T *i* _u_ ~~s~~"),
    ]:
        doc, errors = _run(
            tmp_path, "d.md", text, "markdown")
        assert errors == []
        assert [(e.type, e.content, e.metadata)
                for e in doc.elements] == [
            ("heading", want, {"level": 2})], repr(text)


def test_md_heading_entity_not_decoded(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "## A &amp; B\n", "markdown")
    assert errors == []
    assert doc.elements[0].content == "A &amp; B"


def test_html_heading_decoded_stripped(tmp_path):
    doc, errors = _run(
        tmp_path, "d.html",
        "<h2>A &amp; B</h2><h3>T <b>x</b> y</h3>",
        "html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "A & B", {"level": 2}),
        ("heading", "T x y", {"level": 3})]
