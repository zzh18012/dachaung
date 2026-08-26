r"""pipeline html 超限 pre/bq 切分与纯图
零 chunk（Round 1778）。

新角度：R1777 锁 ipynb 同谱——**html pre
900 与 bq 900 都走
'long_paragraph_sentence_split'（bq 首
块 forced_char）；html 纯图文档 chunks
[]（与 md 一致）**零覆盖：

- **'&lt;pre&gt;'字×900**：800+100
- **bq 好×900**：800 forced_char+100
- **两 img 无文**：2 elements、
  chunks []、无错误无警告
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_pre_oversize_split(tmp_path):
    doc, errors = _run(
        tmp_path, "<pre>" + "字" * 900 + "</pre>")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (800, "long_paragraph_sentence_split"),
        (100, "long_paragraph_sentence_split")]


def test_bq_oversize_split(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<blockquote><p>" + "好" * 900
        + "</p></blockquote>")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"],
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (800, "long_paragraph_sentence_split",
         "forced_char"),
        (100, "long_paragraph_sentence_split", None)]


def test_html_image_only_empty_chunks(tmp_path):
    doc, errors = _run(
        tmp_path, '<img src="a.png"><img src="b.png">')
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "image", "image"]
    assert doc.chunks == []
    assert doc.warnings == []
