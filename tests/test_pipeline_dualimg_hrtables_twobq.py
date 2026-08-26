r"""pipeline 同段双 img、hr 分隔双表与两个
引用段（Round 1729）。

新角度：R1728 锁 NBSP 分隔——**同 `<p>`
内两个 `<img>` 出两个 image 元素、html
`<hr>` 正确分隔两张表、'> q1\\n\\n> q2'
两段合 1 chunk**零覆盖：

- **`<p><img a><img b></p>`**：image a.png
  + image b.png（顺序保留，p 消失）
- **table + hr + table**：两张独立表
- **'> q1\\n\\n> q2'**：两个 blockquote
  段落合 1 chunk
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "markdown")


def test_two_imgs_in_one_p(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<p><img src="a.png" alt="A">'
        '<img src="b.png" alt="B"></p>', "d.html")
    assert errors == []
    assert [(e.type, e.resource_path, e.metadata)
            for e in doc.elements] == [
        ("image", "a.png", {"alt": "A"}),
        ("image", "b.png", {"alt": "B"})]


def test_hr_between_tables(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td>a</td></tr></table><hr>"
        "<table><tr><td>b</td></tr></table>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"}),
        ("table", "| b |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_two_bq_paragraphs_merge_chunk(tmp_path):
    doc, errors = _run(tmp_path, "> q1\n\n> q2\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "q1", {"kind": "blockquote"}),
        ("paragraph", "q2", {"kind": "blockquote"})]
    assert len(doc.chunks) == 1
