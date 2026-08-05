r"""app/parsers/html_parser.py 边角测试 - 第七轮（Round 185）。

补强已有 base/edges/edges2-6（共 711 测试）未覆盖的深度：
- 常量精确值：_HEADING_LEVELS、_SKIP_TAGS、_HTML_EXTENSIONS
- _detect_html_source_type：大写、未知、无后缀
- <img> 各种 attribute 组合（empty src 跳过、empty alt、url 含路径）
- <pre>/<blockquote> 嵌套 depth 计数
- <ul>/<ol> 嵌套 list_stack
- <br>、<hr>、自闭合 tag
- 表格：th/td 混合、空 cell、嵌套 table warning
- loose text → paragraph
- character entity：named/numeric hex/decimal
- section_path 跟踪：同级/高级/低级 heading
- HtmlParser 类属性、错误路径
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, Element
from app.parsers.base import Parser, ParserError
from app.parsers.html_parser import (
    _detect_html_source_type,
    _HEADING_LEVELS,
    _HTMLDocParser,
    _HTML_EXTENSIONS,
    _rows_to_md,
    _SKIP_TAGS,
    HtmlParser,
)


# =========================================================================
# 常量精确值
# =========================================================================


def test_heading_levels_exact_six_entries():
    assert len(_HEADING_LEVELS) == 6


def test_heading_levels_h1_to_h6():
    assert _HEADING_LEVELS == {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


def test_skip_tags_contains_script_style():
    assert "script" in _SKIP_TAGS
    assert "style" in _SKIP_TAGS


def test_skip_tags_contains_head_title_meta_link():
    assert "head" in _SKIP_TAGS
    assert "title" in _SKIP_TAGS
    assert "meta" in _SKIP_TAGS
    assert "link" in _SKIP_TAGS


def test_skip_tags_contains_noscript():
    assert "noscript" in _SKIP_TAGS


def test_skip_tags_count_seven():
    assert len(_SKIP_TAGS) == 7


def test_html_extensions_exact():
    assert _HTML_EXTENSIONS == (".html", ".htm")


def test_html_extensions_is_tuple():
    assert isinstance(_HTML_EXTENSIONS, tuple)


def test_heading_levels_is_dict():
    assert isinstance(_HEADING_LEVELS, dict)


def test_skip_tags_is_set():
    assert isinstance(_SKIP_TAGS, set)


# =========================================================================
# _detect_html_source_type 深度
# =========================================================================


def test_detect_html_source_type_html():
    assert _detect_html_source_type(Path("a.html")) == "html"


def test_detect_html_source_type_htm():
    assert _detect_html_source_type(Path("a.htm")) == "html"


def test_detect_html_source_type_uppercase():
    assert _detect_html_source_type(Path("a.HTML")) == "html"


def test_detect_html_source_type_mixed_case():
    assert _detect_html_source_type(Path("a.HtM")) == "html"


def test_detect_html_source_type_unknown_suffix_raises():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("a.txt"))
    assert exc.value.code == "unsupported_type"


def test_detect_html_source_type_no_suffix_raises():
    with pytest.raises(ParserError):
        _detect_html_source_type(Path("README"))


def test_detect_html_source_type_xml_raises():
    with pytest.raises(ParserError):
        _detect_html_source_type(Path("a.xml"))


def test_detect_html_source_type_error_has_suffix_detail():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("a.txt"))
    assert exc.value.details["suffix"] == ".txt"


def test_detect_html_source_type_error_message_contains_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("a.unknown"))
    assert ".unknown" in str(exc.value)


def test_detect_html_source_type_returns_str():
    assert isinstance(_detect_html_source_type(Path("a.html")), str)


# =========================================================================
# _rows_to_md 深度（html_parser.py 的本地实现）
# =========================================================================


def test_rows_to_md_empty_returns_empty():
    assert _rows_to_md([]) == ""


def test_rows_to_md_single_row():
    result = _rows_to_md([["a", "b"]])
    lines = result.split("\n")
    assert len(lines) == 2  # header + separator
    assert "a" in lines[0]
    assert "b" in lines[0]


def test_rows_to_md_multi_row():
    result = _rows_to_md([["h1", "h2"], ["v1", "v2"]])
    lines = result.split("\n")
    assert len(lines) == 3


def test_rows_to_md_pads_uneven():
    result = _rows_to_md([["h1", "h2"], ["v1"]])
    # 不会因缺列崩
    assert "v1" in result


def test_rows_to_md_pipe_at_edges():
    result = _rows_to_md([["a"]])
    for line in result.split("\n"):
        assert line.startswith("| ")
        assert line.endswith(" |")


def test_rows_to_md_separator_three_dashes():
    result = _rows_to_md([["a", "b"]])
    lines = result.split("\n")
    assert "---" in lines[1]


# =========================================================================
# HtmlParser 类属性
# =========================================================================


def test_html_parser_name_attribute():
    assert HtmlParser.name == "html"


def test_html_parser_version_attribute():
    assert HtmlParser.version == "stdlib/0.1.0"


def test_html_parser_inherits_parser():
    assert issubclass(HtmlParser, Parser)


def test_html_parser_parse_signature():
    sig = inspect.signature(HtmlParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


def test_html_parser_parse_no_defaults():
    sig = inspect.signature(HtmlParser.parse)
    for name in ("path", "source_hash"):
        assert sig.parameters[name].default is inspect.Parameter.empty


# =========================================================================
# _HTMLDocParser 类结构
# =========================================================================


def test_html_doc_parser_init_takes_document_id():
    p = _HTMLDocParser("doc1")
    assert p.document_id == "doc1"


def test_html_doc_parser_init_elements_empty():
    p = _HTMLDocParser("doc1")
    assert p.elements == []


def test_html_doc_parser_init_warnings_empty():
    p = _HTMLDocParser("doc1")
    assert p.warnings == []


def test_html_doc_parser_handles_data_method():
    p = _HTMLDocParser("doc1")
    assert callable(p.handle_data)


def test_html_doc_parser_handles_starttag_method():
    p = _HTMLDocParser("doc1")
    assert callable(p.handle_starttag)


def test_html_doc_parser_handles_endtag_method():
    p = _HTMLDocParser("doc1")
    assert callable(p.handle_endtag)


def test_html_doc_parser_handles_startendtag_method():
    p = _HTMLDocParser("doc1")
    assert callable(p.handle_startendtag)


def test_html_doc_parser_inherits_stdlib():
    from html.parser import HTMLParser as StdHTMLParser
    assert issubclass(_HTMLDocParser, StdHTMLParser)


def test_html_doc_parser_convert_charrefs_true():
    """convert_charrefs=True 让 char entity 自动转换。"""
    p = _HTMLDocParser("doc1")
    assert p.convert_charrefs is True


# =========================================================================
# <img> 处理深度
# =========================================================================


def _parse_html(text: str) -> Document:
    """Helper：直接喂 HTML 字符串。"""
    parser = HtmlParser()
    # 用 in-memory 临时文件
    import tempfile, os
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(text)
        path = f.name
    try:
        return parser.parse(path, "a" * 64)
    finally:
        os.unlink(path)


def test_parse_img_basic(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text('<html><body><img src="x.png" alt="alt"></body></html>', encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "image"
    assert doc.elements[0].resource_path == "x.png"
    assert doc.elements[0].metadata["alt"] == "alt"
    assert doc.elements[0].content is None


def test_parse_img_empty_src_skipped(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text('<html><body><img src="" alt="alt"></body></html>', encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 空 src → 不 emit
    assert doc.elements == []


def test_parse_img_whitespace_src_skipped(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text('<html><body><img src="   " alt="alt"></body></html>', encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []


def test_parse_img_missing_alt(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text('<html><body><img src="x.png"></body></html>', encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].metadata["alt"] == ""


def test_parse_img_with_url_path(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text('<html><body><img src="https://example.com/img.png"></body></html>', encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].resource_path == "https://example.com/img.png"


def test_parse_img_self_closing(tmp_path: Path):
    """自闭合 <img .../> 应该正常处理。"""
    p = tmp_path / "test.html"
    p.write_text('<html><body><img src="x.png" alt="alt"/></body></html>', encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "image"


def test_parse_img_confidence_09(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text('<html><body><img src="x.png" alt="alt"></body></html>', encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].confidence == 0.9


# =========================================================================
# <pre>/<blockquote> 深度
# =========================================================================


def test_parse_pre_basic(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><pre>code line</pre></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].metadata["kind"] == "preformatted"
    assert doc.elements[0].content == "code line"


def test_parse_pre_preserves_newlines(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><pre>line1\nline2\nline3</pre></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # pre 应保留换行
    assert "line1" in doc.elements[0].content
    assert "line2" in doc.elements[0].content
    assert "line3" in doc.elements[0].content


def test_parse_blockquote_basic(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><blockquote>quoted text</blockquote></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].metadata["kind"] == "blockquote"


def test_parse_nested_pre(tmp_path: Path):
    """嵌套 pre（不规范但需不崩）。"""
    p = tmp_path / "test.html"
    p.write_text("<html><body><pre>outer<pre>inner</pre>after</pre></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 不抛 + 至少一个 pre element
    pre_els = [el for el in doc.elements if el.metadata.get("kind") == "preformatted"]
    assert len(pre_els) >= 1


def test_parse_nested_blockquote(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><blockquote>outer<blockquote>inner</blockquote></blockquote></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 不抛
    bq_els = [el for el in doc.elements if el.metadata.get("kind") == "blockquote"]
    assert len(bq_els) >= 1


def test_parse_paragraph_inside_blockquote_ignored(tmp_path: Path):
    """<p> 在 blockquote 上下文中被忽略（不切新 block）。"""
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><blockquote><p>quote text</p></blockquote></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 1 个 blockquote element（含 quote text）
    assert len(doc.elements) == 1
    assert doc.elements[0].metadata["kind"] == "blockquote"


def test_parse_paragraph_inside_pre_ignored(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><pre><p>code line</p></pre></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 1 个 preformatted element
    assert len(doc.elements) == 1
    assert doc.elements[0].metadata["kind"] == "preformatted"


# =========================================================================
# <ul>/<ol>/<li> 深度
# =========================================================================


def test_parse_ul_basic(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><ul><li>a</li><li>b</li></ul></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2
    for el in doc.elements:
        assert el.type == "list_item"
        assert el.metadata["ordered"] is False
        assert el.metadata["marker"] == "unordered"


def test_parse_ol_basic(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><ol><li>a</li><li>b</li></ol></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    for el in doc.elements:
        assert el.metadata["ordered"] is True
        assert el.metadata["marker"] == "ordered"


def test_parse_nested_lists(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><ul><li>outer<ol><li>inner</li></ol></li></ul></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 至少 1 个 outer + 1 个 inner
    assert len(doc.elements) >= 2


def test_parse_li_directly_without_list(tmp_path: Path):
    """<li> 不在 <ul>/<ol> 中 → 默认 unordered=False。"""
    p = tmp_path / "test.html"
    p.write_text("<html><body><li>item</li></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    # list_stack 为空 → ordered=False
    assert doc.elements[0].metadata["ordered"] is False


# =========================================================================
# <br>、<hr>、自闭合
# =========================================================================


def test_parse_br_inside_paragraph_adds_space(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>line1<br>line2</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert " " in doc.elements[0].content
    assert "line1" in doc.elements[0].content
    assert "line2" in doc.elements[0].content


def test_parse_br_outside_block_no_crash(tmp_path: Path):
    """<br> 在无 active block 时不崩。"""
    p = tmp_path / "test.html"
    p.write_text("<html><body><br></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 不抛 + 无 element
    assert doc.elements == []


def test_parse_hr_flushes_block(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>text</p><hr><p>after</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 2 个 paragraph（hr 被忽略）
    paragraphs = [el for el in doc.elements if el.type == "paragraph"]
    assert len(paragraphs) == 2


def test_parse_hr_alone_no_crash(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><hr></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []


# =========================================================================
# 表格深度
# =========================================================================


def test_parse_table_basic(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><table>"
        "<tr><th>H1</th><th>H2</th></tr>"
        "<tr><td>a</td><td>b</td></tr>"
        "</table></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    table = doc.elements[0]
    assert table.type == "table"
    assert table.metadata["row_count"] == 2
    assert table.metadata["col_count"] == 2
    assert table.metadata["source"] == "html_table"


def test_parse_table_th_only(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><table>"
        "<tr><th>H1</th><th>H2</th></tr>"
        "</table></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].metadata["row_count"] == 1


def test_parse_table_empty_cells(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><table>"
        "<tr><td></td><td></td></tr>"
        "</table></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    # 空 cells 也生成 table element
    assert doc.elements[0].metadata["row_count"] == 1


def test_parse_table_empty_no_element(tmp_path: Path):
    """<table></table> 空 → md 为空 → 不 emit element。"""
    p = tmp_path / "test.html"
    p.write_text("<html><body><table></table></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []


def test_parse_nested_table_emits_warning(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><table>"
        "<tr><td>outer</td></tr>"
        "<tr><td><table><tr><td>inner</td></tr></table></td></tr>"
        "</table></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 嵌套 table 应触发 warning
    warning_codes = [w.code for w in doc.warnings]
    assert "html_nested_table" in warning_codes


def test_parse_table_confidence_09(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><table><tr><td>x</td></tr></table></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].confidence == 0.9


def test_parse_table_with_p_inside_cell(tmp_path: Path):
    """<p> 在 <td> 内 → 文本被收集到 cell。"""
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><table>"
        "<tr><td><p>cell text</p></td></tr>"
        "</table></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert "cell text" in doc.elements[0].content


# =========================================================================
# loose text → paragraph
# =========================================================================


def test_parse_loose_text_in_body(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body>just text</body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == "just text"


def test_parse_whitespace_only_text_no_element(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body>   \n\t  </body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 全空白 → 无 element + no_content warning
    assert doc.elements == []


def test_parse_mixed_loose_text_and_p(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body>loose<p>para</p>more loose</body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 至少 2 个 paragraph
    paragraphs = [el for el in doc.elements if el.type == "paragraph"]
    assert len(paragraphs) >= 2


# =========================================================================
# 字符实体深度
# =========================================================================


def test_parse_named_entity_decoded(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>&amp; &lt; &gt;</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    content = doc.elements[0].content
    assert "&" in content
    assert "<" in content
    assert ">" in content


def test_parse_numeric_decimal_entity(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>&#65;</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # &#65; → 'A'
    assert "A" in doc.elements[0].content


def test_parse_numeric_hex_entity(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>&#x41;</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # &#x41; → 'A'
    assert "A" in doc.elements[0].content


def test_parse_entity_in_heading(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><h1>&amp; Title</h1></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert "&" in doc.elements[0].content


def test_parse_entity_in_table_cell(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body><table><tr><td>&amp;</td></tr></table></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert "&" in doc.elements[0].content


# =========================================================================
# section_path 跟踪
# =========================================================================


def test_parse_section_path_tracking(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body>"
        "<h1>Chapter</h1>"
        "<p>para1</p>"
        "<h2>Section</h2>"
        "<p>para2</p>"
        "</body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    paragraphs = [el for el in doc.elements if el.type == "paragraph"]
    assert paragraphs[0].source_locator["section_path"] == "Chapter"
    assert paragraphs[1].source_locator["section_path"] == "Chapter > Section"


def test_parse_section_path_pops_on_same_level(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body>"
        "<h1>A</h1>"
        "<h2>A1</h2>"
        "<h2>A2</h2>"
        "<p>under A2</p>"
        "</body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    para = next(el for el in doc.elements if el.type == "paragraph")
    assert para.source_locator["section_path"] == "A > A2"


def test_parse_section_path_pops_on_higher_level(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body>"
        "<h1>A</h1>"
        "<h2>A1</h2>"
        "<h3>A1a</h3>"
        "<h1>B</h1>"
        "<p>under B</p>"
        "</body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    para = next(el for el in doc.elements if el.type == "paragraph")
    assert para.source_locator["section_path"] == "B"


def test_parse_section_path_in_heading_locator(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><h1>Title</h1></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    heading = doc.elements[0]
    # heading 元素本身在栈内，所以 section_path = "Title"
    assert heading.source_locator["section_path"] == "Title"


def test_parse_no_section_path_when_no_heading(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>just a paragraph</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    para = doc.elements[0]
    assert "section_path" not in para.source_locator


# =========================================================================
# 错误路径
# =========================================================================


def test_parse_missing_file_raises(tmp_path: Path):
    parser = HtmlParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(tmp_path / "missing.html", "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_unsupported_suffix_raises(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = HtmlParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "unsupported_type"


def test_parse_read_oserror_raises(tmp_path: Path, monkeypatch):
    p = tmp_path / "test.html"
    p.write_text("<p>hello</p>", encoding="utf-8")

    def fake_read_text(self, *args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    parser = HtmlParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "html_read_failed"


def test_parse_read_oserror_error_has_exception_type(tmp_path: Path, monkeypatch):
    p = tmp_path / "test.html"
    p.write_text("<p>hello</p>", encoding="utf-8")

    def fake_read_text(self, *args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    parser = HtmlParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert "exception_type" in exc.value.details


# =========================================================================
# 编码与综合
# =========================================================================


def test_parse_non_utf8_file_uses_replace(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_bytes(b"<html><body><p>\xe9\x9c</p></body></html>")  # 不完整 UTF-8
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 不抛
    assert len(doc.elements) >= 1


def test_parse_returns_document_instance(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_metadata_html_flag(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["html"] is True


def test_parse_empty_file_emits_no_content_warning(tmp_path: Path):
    p = tmp_path / "empty.html"
    p.write_text("", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []
    assert any(w.code == "html_no_content" for w in doc.warnings)


def test_parse_only_head_emits_no_content_warning(tmp_path: Path):
    p = tmp_path / "head.html"
    p.write_text("<html><head><title>T</title></head></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []
    assert any(w.code == "html_no_content" for w in doc.warnings)


def test_parse_script_style_skipped(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><head><script>var x = 1;</script>"
        "<style>body { color: red; }</style></head>"
        "<body><p>visible</p></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 只 1 个 paragraph（script/style 跳过）
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "visible"


def test_parse_complex_doc(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text(
        "<html><body>"
        "<h1>Title</h1>"
        "<p>Para one.</p>"
        "<h2>Sub</h2>"
        "<ul><li>a</li><li>b</li></ul>"
        "<pre>code</pre>"
        "<blockquote>quote</blockquote>"
        "<table><tr><th>H</th></tr><tr><td>v</td></tr></table>"
        "<img src='x.png' alt='img'>"
        "</body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    types = [el.type for el in doc.elements]
    assert "heading" in types
    assert "paragraph" in types
    assert "list_item" in types
    assert "table" in types
    assert "image" in types
    # pre + blockquote 都是 paragraph with kind
    kinds = [el.metadata.get("kind") for el in doc.elements if el.metadata.get("kind")]
    assert "preformatted" in kinds
    assert "blockquote" in kinds


def test_parse_invalid_markup_does_not_raise(tmp_path: Path):
    """不规范的 HTML（未闭合 tag、嵌套错误）不应抛 ParserError。"""
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>unclosed paragraph", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    # 不抛 + 至少有 1 element
    assert len(doc.elements) >= 1


def test_parse_idempotent(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc1 = parser.parse(p, "a" * 64)
    doc2 = parser.parse(p, "a" * 64)
    assert len(doc1.elements) == len(doc2.elements)
    assert doc1.elements[0].content == doc2.elements[0].content


def test_parse_element_ids_zero_padded(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>a</p><p>b</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    ids = [el.element_id for el in doc.elements]
    assert "::e0000" in ids[0]
    assert "::e0001" in ids[1]


def test_parse_returns_document_with_empty_chunks(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []
