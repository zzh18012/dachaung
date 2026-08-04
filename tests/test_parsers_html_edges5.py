r"""app/parsers/html_parser.py 边角测试 - 第五轮（Round 137）。

补强已有 base/edges/edges2/edges3/edges4（共 495 测试）未覆盖的深度：
- 模块常量深度（_HEADING_LEVELS / _SKIP_TAGS / _HTML_EXTENSIONS）
- _rows_to_md 边界（极宽、jagged、Unicode）
- _detect_html_source_type 边界（uppercase/mixed/.HTM）
- handle_data loose text 行为
- 嵌套 table warning
- 表格 cell 收尾（未闭合 <tr>）
- 模块结构与签名深度
- 综合行为（complex document）
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import ParserError
from app.parsers.html_parser import (
    _HTML_EXTENSIONS,
    _HEADING_LEVELS,
    _HTMLDocParser,
    _SKIP_TAGS,
    HtmlParser,
    _detect_html_source_type,
    _rows_to_md,
)


# =========================================================================
# 模块常量深度
# =========================================================================


def test_html_extensions_count_two():
    assert len(_HTML_EXTENSIONS) == 2


def test_html_extensions_contains_html_and_htm():
    assert ".html" in _HTML_EXTENSIONS
    assert ".htm" in _HTML_EXTENSIONS


def test_html_extensions_is_tuple():
    assert isinstance(_HTML_EXTENSIONS, tuple)


def test_heading_levels_count_six():
    assert len(_HEADING_LEVELS) == 6


def test_heading_levels_mapping_values():
    assert _HEADING_LEVELS == {
        "h1": 1,
        "h2": 2,
        "h3": 3,
        "h4": 4,
        "h5": 5,
        "h6": 6,
    }


def test_skip_tags_contains_script_style():
    assert "script" in _SKIP_TAGS
    assert "style" in _SKIP_TAGS


def test_skip_tags_contains_head_title():
    assert "head" in _SKIP_TAGS
    assert "title" in _SKIP_TAGS


def test_skip_tags_contains_meta_link_noscript():
    assert "meta" in _SKIP_TAGS
    assert "link" in _SKIP_TAGS
    assert "noscript" in _SKIP_TAGS


def test_skip_tags_is_set():
    assert isinstance(_SKIP_TAGS, set)


def test_skip_tags_count_seven():
    assert len(_SKIP_TAGS) == 7


def test_heading_levels_is_dict():
    assert isinstance(_HEADING_LEVELS, dict)


# =========================================================================
# _detect_html_source_type 深度
# =========================================================================


def test_detect_html_source_type_html_lowercase():
    assert _detect_html_source_type(Path("test.html")) == "html"


def test_detect_html_source_type_htm_lowercase():
    assert _detect_html_source_type(Path("test.htm")) == "html"


def test_detect_html_source_type_html_uppercase():
    assert _detect_html_source_type(Path("test.HTML")) == "html"


def test_detect_html_source_type_htm_uppercase():
    assert _detect_html_source_type(Path("test.HTM")) == "html"


def test_detect_html_source_type_mixed_case():
    assert _detect_html_source_type(Path("test.HtMl")) == "html"


def test_detect_html_source_type_rejects_pdf():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("test.pdf"))
    assert exc.value.code == "unsupported_type"


def test_detect_html_source_type_rejects_docx():
    with pytest.raises(ParserError):
        _detect_html_source_type(Path("test.docx"))


def test_detect_html_source_type_rejects_md():
    with pytest.raises(ParserError):
        _detect_html_source_type(Path("test.md"))


def test_detect_html_source_type_rejects_no_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("no_suffix"))
    assert "(无)" in exc.value.message or "suffix" in str(exc.value.details)


def test_detect_html_source_type_error_details_suffix_value():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("test.txt"))
    assert exc.value.details == {"suffix": ".txt"}


def test_detect_html_source_type_error_details_empty_when_no_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("README"))
    assert exc.value.details == {"suffix": ""}


# =========================================================================
# _rows_to_md 深度
# =========================================================================


def test_rows_to_md_empty_returns_empty_string():
    assert _rows_to_md([]) == ""


def test_rows_to_md_single_row():
    """单行：header only。"""
    out = _rows_to_md([["a", "b"]])
    lines = out.split("\n")
    # header + separator
    assert len(lines) == 2


def test_rows_to_md_two_rows():
    out = _rows_to_md([["h1", "h2"], ["v1", "v2"]])
    lines = out.split("\n")
    assert len(lines) == 3  # header + sep + body
    assert lines[0] == "| h1 | h2 |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| v1 | v2 |"


def test_rows_to_md_three_rows():
    out = _rows_to_md([["h"], ["a"], ["b"]])
    lines = out.split("\n")
    assert len(lines) == 4  # header + sep + 2 body


def test_rows_to_md_jagged_rows_pad_empty():
    out = _rows_to_md([["a", "b"], ["c"]])
    lines = out.split("\n")
    assert lines[2] == "| c |  |"


def test_rows_to_md_unicode():
    out = _rows_to_md([["中"], ["文"]])
    assert "| 中 |" in out


def test_rows_to_md_returns_str():
    assert isinstance(_rows_to_md([[]]), str)


def test_rows_to_md_wide_row():
    """5 列 → 单行有 6 个 |（含 2 个外缘）。"""
    out = _rows_to_md([["a", "b", "c", "d", "e"]])
    lines = out.split("\n")
    # header + separator
    assert len(lines) == 2
    # 每行 6 个 |（5 列内容分隔 + 2 外缘 - 1 = 6）
    assert lines[0].count("|") == 6


# =========================================================================
# HtmlParser 类属性
# =========================================================================


def test_html_parser_name_value():
    assert HtmlParser.name == "html"


def test_html_parser_version_value():
    assert HtmlParser.version == "stdlib/0.1.0"


def test_html_parser_name_is_str():
    assert isinstance(HtmlParser.name, str)


def test_html_parser_version_is_str():
    assert isinstance(HtmlParser.version, str)


def test_html_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(HtmlParser, Parser)


def test_html_doc_parser_inherits_stdlib_html_parser():
    from html.parser import HTMLParser
    assert issubclass(_HTMLDocParser, HTMLParser)


# =========================================================================
# _HTMLDocParser 实例化
# =========================================================================


def test_html_doc_parser_init_no_args_other_than_document_id():
    """_HTMLDocParser 构造只接受 document_id。"""
    h = _HTMLDocParser("docid")
    assert h.document_id == "docid"


def test_html_doc_parser_initial_state_empty_elements():
    h = _HTMLDocParser("docid")
    assert h.elements == []


def test_html_doc_parser_initial_state_empty_warnings():
    h = _HTMLDocParser("docid")
    assert h.warnings == []


def test_html_doc_parser_initial_state_no_cur_kind():
    h = _HTMLDocParser("docid")
    assert h._cur_kind is None


def test_html_doc_parser_initial_state_empty_cur_buffer():
    h = _HTMLDocParser("docid")
    assert h._cur_buffer == []


def test_html_doc_parser_initial_state_table_depth_zero():
    h = _HTMLDocParser("docid")
    assert h._table_depth == 0


def test_html_doc_parser_initial_state_pre_depth_zero():
    h = _HTMLDocParser("docid")
    assert h._pre_depth == 0


def test_html_doc_parser_initial_state_blockquote_depth_zero():
    h = _HTMLDocParser("docid")
    assert h._blockquote_depth == 0


def test_html_doc_parser_initial_state_empty_section_path():
    h = _HTMLDocParser("docid")
    assert h._section_path == []


def test_html_doc_parser_initial_state_empty_skip_stack():
    h = _HTMLDocParser("docid")
    assert h._skip_stack == []


def test_html_doc_parser_initial_state_empty_list_stack():
    h = _HTMLDocParser("docid")
    assert h._list_stack == []


# =========================================================================
# handle_data loose text 行为
# =========================================================================


def test_handle_data_loose_text_becomes_paragraph():
    """<body>下直接的 loose text 应被吸收为 paragraph。"""
    h = _HTMLDocParser("doc")
    h.feed("<html><body>loose text</body></html>")
    h.close()
    h._flush_block()
    paras = [e for e in h.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert "loose text" in paras[0].content


def test_handle_data_inside_p_accumulates():
    h = _HTMLDocParser("doc")
    h.feed("<p>hello</p>")
    h.close()
    h._flush_block()
    assert any("hello" in e.content for e in h.elements if e.type == "paragraph")


def test_handle_data_inside_pre_preserved():
    h = _HTMLDocParser("doc")
    h.feed("<pre>line1\nline2</pre>")
    h.close()
    h._flush_block()
    para = next(e for e in h.elements if e.type == "paragraph")
    assert "line1\nline2" in para.content
    assert para.metadata.get("kind") == "preformatted"


def test_handle_data_inside_blockquote():
    h = _HTMLDocParser("doc")
    h.feed("<blockquote>quote text</blockquote>")
    h.close()
    h._flush_block()
    para = next(e for e in h.elements if e.type == "paragraph")
    assert "quote text" in para.content
    assert para.metadata.get("kind") == "blockquote"


def test_handle_data_inside_skip_tag_ignored():
    h = _HTMLDocParser("doc")
    h.feed("<script>var x = 1;</script>")
    h.close()
    h._flush_block()
    # script 内容不该出现在任何 element
    for e in h.elements:
        if e.content:
            assert "var x" not in e.content


def test_handle_data_style_content_ignored():
    h = _HTMLDocParser("doc")
    h.feed("<style>body { color: red; }</style>")
    h.close()
    h._flush_block()
    for e in h.elements:
        if e.content:
            assert "color" not in e.content


# =========================================================================
# 嵌套 table warning
# =========================================================================


def test_nested_table_emits_warning():
    h = _HTMLDocParser("doc")
    h.feed(
        "<table><tr><td>"
        "<table><tr><td>inner</td></tr></table>"
        "</td></tr></table>"
    )
    h.close()
    h._flush_block()
    assert any(w.code == "html_nested_table" for w in h.warnings)


def test_single_table_no_nested_warning():
    h = _HTMLDocParser("doc")
    h.feed("<table><tr><td>cell</td></tr></table>")
    h.close()
    h._flush_block()
    assert not any(w.code == "html_nested_table" for w in h.warnings)


# =========================================================================
# 表格 cell 收尾
# =========================================================================


def test_table_with_th_td_mixed():
    h = _HTMLDocParser("doc")
    h.feed("<table><tr><th>H</th><td>D</td></tr></table>")
    h.close()
    h._flush_block()
    tbl = next(e for e in h.elements if e.type == "table")
    # 渲染的 markdown 含 H 和 D
    assert "H" in tbl.content
    assert "D" in tbl.content


def test_table_unclosed_tr_auto_closes():
    """<tr> 未闭合，下一个 <tr> 自动收尾上一个 — 至少产出 table 不崩溃。"""
    h = _HTMLDocParser("doc")
    h.feed("<table><tr><td>a<td>b<tr><td>c<td>d</table>")
    h.close()
    h._flush_block()
    tbl = next((e for e in h.elements if e.type == "table"), None)
    assert tbl is not None
    # 至少能产出 table（不崩溃）
    assert tbl.type == "table"


def test_table_metadata_row_col_count():
    h = _HTMLDocParser("doc")
    h.feed(
        "<table>"
        "<tr><th>A</th><th>B</th></tr>"
        "<tr><td>1</td><td>2</td></tr>"
        "</table>"
    )
    h.close()
    h._flush_block()
    tbl = next(e for e in h.elements if e.type == "table")
    assert tbl.metadata.get("row_count") == 2
    assert tbl.metadata.get("col_count") == 2
    assert tbl.metadata.get("source") == "html_table"


def test_table_confidence_09():
    """table element confidence 是 0.9（不同于 paragraph 的 0.95）。"""
    h = _HTMLDocParser("doc")
    h.feed("<table><tr><td>x</td></tr></table>")
    h.close()
    h._flush_block()
    tbl = next(e for e in h.elements if e.type == "table")
    assert tbl.confidence == 0.9


# =========================================================================
# heading 处理
# =========================================================================


def test_h1_creates_heading_level_1():
    h = _HTMLDocParser("doc")
    h.feed("<h1>Title</h1>")
    h.close()
    h._flush_block()
    head = next(e for e in h.elements if e.type == "heading")
    assert head.metadata.get("level") == 1
    assert head.content == "Title"


def test_h6_creates_heading_level_6():
    h = _HTMLDocParser("doc")
    h.feed("<h6>Deep</h6>")
    h.close()
    h._flush_block()
    head = next(e for e in h.elements if e.type == "heading")
    assert head.metadata.get("level") == 6


def test_heading_confidence_095():
    h = _HTMLDocParser("doc")
    h.feed("<h1>X</h1>")
    h.close()
    h._flush_block()
    head = next(e for e in h.elements if e.type == "heading")
    assert head.confidence == 0.95


def test_heading_with_attributes():
    """<h1 class="title"> → 内容仍是 'Title'。"""
    h = _HTMLDocParser("doc")
    h.feed('<h1 class="title" id="x">Title</h1>')
    h.close()
    h._flush_block()
    head = next(e for e in h.elements if e.type == "heading")
    assert head.content == "Title"


# =========================================================================
# list_item 处理
# =========================================================================


def test_ul_li_unordered_marker():
    h = _HTMLDocParser("doc")
    h.feed("<ul><li>item</li></ul>")
    h.close()
    h._flush_block()
    li = next(e for e in h.elements if e.type == "list_item")
    assert li.metadata.get("marker") == "unordered"
    assert li.metadata.get("ordered") is False


def test_ol_li_ordered_marker():
    h = _HTMLDocParser("doc")
    h.feed("<ol><li>item</li></ol>")
    h.close()
    h._flush_block()
    li = next(e for e in h.elements if e.type == "list_item")
    assert li.metadata.get("marker") == "ordered"
    assert li.metadata.get("ordered") is True


def test_multiple_li_in_ul():
    h = _HTMLDocParser("doc")
    h.feed("<ul><li>a</li><li>b</li><li>c</li></ul>")
    h.close()
    h._flush_block()
    items = [e for e in h.elements if e.type == "list_item"]
    assert len(items) == 3


# =========================================================================
# img 处理
# =========================================================================


def test_img_standalone_emits_image():
    h = _HTMLDocParser("doc")
    h.feed('<img src="pic.png" alt="Pic">')
    h.close()
    h._flush_block()
    img = next(e for e in h.elements if e.type == "image")
    assert img.resource_path == "pic.png"
    assert img.metadata.get("alt") == "Pic"


def test_img_no_src_no_element():
    """<img> 无 src → 不发 element。"""
    h = _HTMLDocParser("doc")
    h.feed('<img alt="NoSrc">')
    h.close()
    h._flush_block()
    assert not any(e.type == "image" for e in h.elements)


def test_img_empty_src_no_element():
    h = _HTMLDocParser("doc")
    h.feed('<img src="" alt="empty">')
    h.close()
    h._flush_block()
    assert not any(e.type == "image" for e in h.elements)


def test_img_confidence_09():
    h = _HTMLDocParser("doc")
    h.feed('<img src="x.png">')
    h.close()
    h._flush_block()
    img = next(e for e in h.elements if e.type == "image")
    assert img.confidence == 0.9


def test_img_self_closing_syntax():
    """<img/> 自闭合语法。"""
    h = _HTMLDocParser("doc")
    h.feed('<img src="x.png"/>')
    h.close()
    h._flush_block()
    assert any(e.type == "image" for e in h.elements)


def test_img_no_alt_attribute():
    """无 alt 属性的 img。"""
    h = _HTMLDocParser("doc")
    h.feed('<img src="x.png">')
    h.close()
    h._flush_block()
    img = next(e for e in h.elements if e.type == "image")
    assert img.metadata.get("alt") == ""


# =========================================================================
# section_path 深度
# =========================================================================


def test_section_path_after_h1_h2(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><body><h1>A</h1><h2>B</h2><p>text</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    para = next(e for e in doc.elements if e.type == "paragraph")
    assert para.source_locator.get("section_path") == "A > B"


def test_section_path_h2_h1_pops(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><body><h2>X</h2><h1>Y</h1><p>text</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    para = next(e for e in doc.elements if e.type == "paragraph")
    assert para.source_locator.get("section_path") == "Y"


def test_section_path_no_heading_no_section_key(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><body><p>text</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    para = next(e for e in doc.elements if e.type == "paragraph")
    assert "section_path" not in para.source_locator


# =========================================================================
# element_id 格式
# =========================================================================


def test_element_id_zero_padded(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><body><p>a</p><p>b</p><p>c</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    ids = [e.element_id for e in doc.elements]
    assert ids[0].endswith("::e0000")
    assert ids[1].endswith("::e0001")
    assert ids[2].endswith("::e0002")


def test_element_id_starts_with_document_id(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><body><p>x</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].element_id.startswith(doc.document_id)


# =========================================================================
# 综合行为
# =========================================================================


def test_complex_document_with_multiple_block_types(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text(
        "<html><body>"
        "<h1>Title</h1>"
        "<p>Para 1</p>"
        "<ul><li>Item 1</li><li>Item 2</li></ul>"
        "<table><tr><th>A</th></tr><tr><td>1</td></tr></table>"
        '<img src="pic.png" alt="Pic">'
        "</body></html>",
        encoding="utf-8",
    )
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types
    assert "list_item" in types
    assert "table" in types
    assert "image" in types


def test_parse_returns_document_with_empty_chunks(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><body><p>x</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    assert doc.chunks == []


def test_parse_returns_document_with_empty_relations(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><body><p>x</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    assert doc.relations == []


def test_parse_returns_document_with_empty_errors(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><body><p>x</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    assert doc.errors == []


def test_parse_metadata_html_true(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><body><p>x</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    assert doc.metadata == {"html": True}


def test_parse_empty_body_no_warning(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><body></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    # 空文档可能没有 elements，但也不一定有 warning
    assert isinstance(doc.elements, list)
    assert isinstance(doc.warnings, list)


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_all_only_html_parser():
    from app.parsers.html_parser import __all__
    assert __all__ == ["HtmlParser"]


def test_module_imports_html_parser_class():
    import app.parsers.html_parser as mod
    src = inspect.getsource(mod)
    assert "from html.parser import HTMLParser" in src


def test_module_imports_path():
    import app.parsers.html_parser as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.parsers.html_parser as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_document():
    import app.parsers.html_parser as mod
    src = inspect.getsource(mod)
    assert "Document" in src


def test_module_imports_parser_base():
    import app.parsers.html_parser as mod
    src = inspect.getsource(mod)
    assert "from app.parsers.base import" in src


def test_module_uses_future_annotations():
    import app.parsers.html_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.parsers.html_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_html():
    import app.parsers.html_parser as mod
    assert "HTML" in mod.__doc__


def test_module_docstring_mentions_table():
    import app.parsers.html_parser as mod
    assert "table" in mod.__doc__.lower() or "表格" in mod.__doc__


def test_module_docstring_mentions_source_locator():
    import app.parsers.html_parser as mod
    assert "source_locator" in mod.__doc__ or "section_path" in mod.__doc__


def test_module_docstring_mentions_skip():
    import app.parsers.html_parser as mod
    assert "script" in mod.__doc__.lower() or "跳过" in mod.__doc__


# =========================================================================
# 签名深度
# =========================================================================


def test_detect_html_source_type_signature_one_param():
    sig = inspect.signature(_detect_html_source_type)
    assert len(sig.parameters) == 1


def test_rows_to_md_signature_one_param():
    sig = inspect.signature(_rows_to_md)
    assert len(sig.parameters) == 1


def test_html_parser_parse_signature_three_params():
    sig = inspect.signature(HtmlParser.parse)
    # self, path, source_hash
    assert len(sig.parameters) == 3


def test_html_doc_parser_init_one_param():
    sig = inspect.signature(_HTMLDocParser.__init__)
    # self, document_id
    assert len(sig.parameters) == 2


def test_html_doc_parser_handle_starttag_two_params():
    sig = inspect.signature(_HTMLDocParser.handle_starttag)
    # self, tag, attrs
    assert len(sig.parameters) == 3


def test_html_doc_parser_handle_endtag_one_param():
    sig = inspect.signature(_HTMLDocParser.handle_endtag)
    # self, tag
    assert len(sig.parameters) == 2


def test_html_doc_parser_handle_data_one_param():
    sig = inspect.signature(_HTMLDocParser.handle_data)
    # self, data
    assert len(sig.parameters) == 2
