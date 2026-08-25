r"""pipeline text 空文件族与 html img 容器内
（Round 1647）。

新角度：R1646 锁 caption/figcap——**text 空/
纯空白、img 进 li/td 的容器行为**零覆盖：

- **text_no_content（第 7 个家族警告码）**：
  空与纯空白 .txt → no_extracted_elements，
  嵌套 warning code='text_no_content'
- **li 内 img 破坏 list_item**：img 独立成
  image，剩余文本成普通 paragraph（非
  list_item）
- **td 内 img 静默丢弃**：单元格成空 '|  |'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _txt(tmp_path, text):
    p = tmp_path / "d.txt"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="text")


def _html(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    return doc


def test_text_no_content_family(tmp_path):
    for text in ("", "   \n\n  \t\n"):
        doc, errors = _txt(tmp_path, text)
        assert doc is None
        assert [e.code for e in errors] == [
            "no_extracted_elements"]
        w = errors[0].details["warnings"]
        assert [x["code"] for x in w] == [
            "text_no_content"]
        assert w[0]["reason"] == (
            "文本文件未提取到任何 element"
            "（空文件或仅含空白）")


def test_img_in_li_breaks_list_item(tmp_path):
    doc = _html(
        tmp_path,
        "<ul><li><img src='a.png' alt='IA'> text"
        "</li></ul>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("image", None, {"alt": "IA"}),
        ("paragraph", "text", {})]


def test_img_in_td_dropped(tmp_path):
    doc = _html(
        tmp_path,
        "<table><tr><td><img src='b.png' alt='IB'>"
        "</td></tr></table>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "|  |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]
