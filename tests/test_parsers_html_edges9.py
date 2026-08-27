r"""app/parsers/html_parser.py 边角测试 - 第九轮（Round 1361）。

补强 edges-edges8（共 808+ 测试）未覆盖的深度（probe 实证）：
- rowspan/colspan 完全忽略——cell 按出现顺序填格，不位移不合并
- <dl>/<dt>/<dd> 塌成单个 paragraph（无分隔符连接）
- 字符实体面——&amp;/&lt;/&#65; 转换、&unknown; 字面保留
- <pre> 内联标签剥壳——<b> 标签消失文本直连、换行保留
- 嵌套 <blockquote> 压平——单 paragraph 'quote inner after'
- <hr> 静默跳过
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser


def _parse(html: str):
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "d.html").write_text(html, encoding="utf-8")
        sha = compute_file_hash(tp / "d.html")
        return HtmlParser().parse(tp / "d.html", sha)


def _wrap(body: str) -> str:
    return "<html><body>\n%s\n</body></html>" % body


# ---------- rowspan 忽略 ----------

ROWSPAN = _wrap(
    "<table>\n<tr><th>H1</th><th>H2</th></tr>\n"
    "<tr><td rowspan=\"2\">span</td><td>b</td></tr>\n"
    "<tr><td>c</td><td>d</td></tr>\n</table>")


def test_rowspan_row_count_three():
    doc = _parse(ROWSPAN)
    t = [e for e in doc.elements if e.type == "table"][0]
    assert t.metadata["row_count"] == 3


def test_rowspan_cells_fill_by_position():
    doc = _parse(ROWSPAN)
    t = [e for e in doc.elements if e.type == "table"][0]
    assert t.content == ("| H1 | H2 |\n| --- | --- |\n"
                         "| span | b |\n| c | d |")


def test_rowspan_no_warning():
    assert _parse(ROWSPAN).warnings == []


def test_rowspan_col_count_two():
    doc = _parse(ROWSPAN)
    t = [e for e in doc.elements if e.type == "table"][0]
    assert t.metadata["col_count"] == 2


def test_colspan_ignored_too():
    doc = _parse(_wrap(
        "<table>\n<tr><td colspan=\"3\">wide</td></tr>\n"
        "<tr><td>a</td><td>b</td></tr>\n</table>"))
    t = [e for e in doc.elements if e.type == "table"][0]
    assert t.content == ("| wide |  |\n| --- | --- |\n"
                         "| a | b |")
    assert t.metadata["col_count"] == 2


def test_ragged_rows_padded():
    doc = _parse(_wrap(
        "<table>\n<tr><td>a</td><td>b</td><td>c</td></tr>\n"
        "<tr><td>x</td></tr>\n</table>"))
    t = [e for e in doc.elements if e.type == "table"][0]
    assert t.content.endswith("| x |  |  |")


# ---------- dl 塌缩 ----------

DL = _wrap("<dl><dt>term</dt><dd>def</dd></dl>")


def test_dl_single_paragraph():
    doc = _parse(DL)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "termdef"


def test_dl_no_list_items():
    doc = _parse(DL)
    assert [e for e in doc.elements
            if e.type == "list_item"] == []


def test_dl_no_definition_type():
    doc = _parse(DL)
    assert all(e.type != "definition"
               for e in doc.elements)


def test_dl_multi_terms_concat():
    doc = _parse(_wrap(
        "<dl><dt>a</dt><dt>b</dt><dd>c</dd></dl>"))
    paras = [e for e in doc.elements
             if e.type == "paragraph"]
    assert paras[0].content == "abc"


# ---------- 字符实体 ----------

ENT = _wrap("<p>A &lt;b&gt; bold &#65; entity "
            "&unknown; kept</p>")


def test_entity_lt_gt_converted():
    doc = _parse(ENT)
    p = doc.elements[0]
    assert "<b>" in p.content


def test_entity_numeric_65_is_A():
    doc = _parse(ENT)
    p = doc.elements[0]
    assert "&#65;" not in p.content
    assert "A entity" in p.content


def test_entity_unknown_kept_literal():
    doc = _parse(ENT)
    p = doc.elements[0]
    assert "&unknown;" in p.content


def test_entity_amp_in_heading_flows_section():
    doc = _parse(_wrap("<h1>Title &amp; More</h1>"))
    h = doc.elements[0]
    assert h.content == "Title & More"
    assert h.source_locator["section_path"] == \
        "Title & More"


def test_entity_amp_in_para():
    doc = _parse(_wrap("<p>a &amp; b</p>"))
    assert doc.elements[0].content == "a & b"


# ---------- pre 内联标签剥壳 ----------

PRE = _wrap("<pre>line1\n<b>bold in pre</b>\nline3</pre>")


def test_pre_inner_tag_stripped():
    doc = _parse(PRE)
    p = doc.elements[0]
    assert "<b>" not in p.content
    assert "bold in pre" in p.content


def test_pre_newlines_preserved():
    doc = _parse(PRE)
    assert doc.elements[0].content == \
        "line1\nbold in pre\nline3"


def test_pre_kind_metadata():
    doc = _parse(PRE)
    assert doc.elements[0].metadata["kind"] == \
        "preformatted"


def test_pre_is_paragraph_type():
    doc = _parse(PRE)
    assert doc.elements[0].type == "paragraph"


# ---------- 嵌套 blockquote 压平 ----------

BQ = _wrap("<blockquote>quote <blockquote>inner"
           "</blockquote> after</blockquote>")


def test_nested_blockquote_single_para():
    doc = _parse(BQ)
    paras = [e for e in doc.elements
             if e.type == "paragraph"]
    assert len(paras) == 1


def test_nested_blockquote_flattened_text():
    doc = _parse(BQ)
    assert doc.elements[0].content == \
        "quote inner after"


def test_nested_blockquote_kind():
    doc = _parse(BQ)
    assert doc.elements[0].metadata["kind"] == \
        "blockquote"


def test_nested_blockquote_no_warning():
    assert _parse(BQ).warnings == []


# ---------- hr 静默跳过 ----------

def test_hr_no_element():
    doc = _parse(_wrap("<p>before</p>\n<hr>\n<p>after</p>"))
    types = [e.type for e in doc.elements]
    assert "thematic_break" not in types
    assert types == ["paragraph", "paragraph"]


def test_hr_no_warning():
    assert _parse(_wrap("<p>x</p><hr>")).warnings == []


# ---------- img 细节 ----------

def test_img_empty_alt_kept():
    doc = _parse(_wrap('<img src="pic.png" alt="">'))
    img = doc.elements[0]
    assert img.metadata["alt"] == ""


def test_img_resource_path():
    doc = _parse(_wrap('<img src="pic.png" alt="">'))
    assert doc.elements[0].resource_path == "pic.png"


def test_img_content_none():
    doc = _parse(_wrap('<img src="pic.png" alt="">'))
    assert doc.elements[0].content is None


# ---------- 组合板结构 ----------

FULL = _wrap(
    "<h1>Title &amp; More</h1>\n"
    "<p>A &lt;b&gt; bold &#65; entity &unknown; kept</p>\n"
    "<table>\n<tr><th>H1</th><th>H2</th></tr>\n"
    "<tr><td rowspan=\"2\">span</td><td>b</td></tr>\n"
    "<tr><td>c</td><td>d</td></tr>\n</table>\n"
    "<dl><dt>term</dt><dd>def</dd></dl>\n"
    '<img src="pic.png" alt="">\n<hr>\n'
    "<pre>line1\n<b>bold in pre</b>\nline3</pre>\n"
    "<blockquote>quote <blockquote>inner"
    "</blockquote> after</blockquote>")


def test_full_doc_element_types():
    doc = _parse(FULL)
    assert [e.type for e in doc.elements] == [
        "heading", "paragraph", "table",
        "paragraph", "image", "paragraph",
        "paragraph"]


def test_full_doc_no_warnings():
    assert _parse(FULL).warnings == []


def test_full_doc_parser_identity():
    doc = _parse(FULL)
    assert doc.parser_name == "html"
    assert doc.parser_version == "stdlib/0.1.0"
    assert doc.source_type == "html"


def test_full_doc_all_sections_titled():
    doc = _parse(FULL)
    for e in doc.elements:
        assert e.source_locator["section_path"] == \
            "Title & More"


def test_full_doc_element_ids_zero_padded():
    doc = _parse(FULL)
    ids = [e.element_id for e in doc.elements]
    assert all("::e" in i for i in ids)
    assert ids == sorted(ids)
