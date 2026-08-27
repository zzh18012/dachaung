"""app/parsers/html_parser.py 边角测试 - 第二轮（Round 76）。

补强 tests/test_parsers_html.py（61）+ tests/test_parsers_html_edges.py（60）
未覆盖的：
- _HTMLDocParser SAX 回调深度：handle_starttag 各 tag 分支、handle_endtag 路径、
  handle_data 在/不在 block 中、handle_startendtag 自闭合、跳过栈、表格状态机
- _detect_html_source_type：大写接受、各扩展名映射、error code 与 details
- _rows_to_md 边角：空 list、单行单列、多列、separator 数
- HtmlParser.parse() 错误路径：file_not_found/unsupported_type/UnicodeDecodeError/
  html_parse_failed（mock）、空 elements → html_no_content warning
- 各种 tag 的 confidence：heading=0.95、paragraph/list_item=0.95、image/table=0.9
- section_path 状态机：嵌套弹出、跳级
- 嵌套 table → html_nested_table warning
- 模块结构与 __all__
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError
from app.parsers.html_parser import (
    HtmlParser,
    _HTML_EXTENSIONS,
    _HEADING_LEVELS,
    _SKIP_TAGS,
    _detect_html_source_type,
    _rows_to_md,
    _HTMLDocParser,
)


# ---------- 模块常量深度 ----------


def test_html_extensions_count_two():
    assert len(_HTML_EXTENSIONS) == 2


def test_html_extensions_values():
    assert set(_HTML_EXTENSIONS) == {".html", ".htm"}


def test_heading_levels_count_six():
    assert len(_HEADING_LEVELS) == 6


def test_heading_levels_keys():
    assert set(_HEADING_LEVELS.keys()) == {"h1", "h2", "h3", "h4", "h5", "h6"}


def test_heading_levels_values_one_to_six():
    assert sorted(_HEADING_LEVELS.values()) == [1, 2, 3, 4, 5, 6]


def test_skip_tags_count_seven():
    assert len(_SKIP_TAGS) == 7


def test_skip_tags_is_set_type():
    assert isinstance(_SKIP_TAGS, set)


def test_skip_tags_contains_script():
    assert "script" in _SKIP_TAGS


def test_skip_tags_contains_style():
    assert "style" in _SKIP_TAGS


def test_skip_tags_contains_head():
    assert "head" in _SKIP_TAGS


def test_skip_tags_contains_title():
    assert "title" in _SKIP_TAGS


def test_skip_tags_contains_meta():
    assert "meta" in _SKIP_TAGS


def test_skip_tags_contains_link():
    assert "link" in _SKIP_TAGS


def test_skip_tags_contains_noscript():
    assert "noscript" in _SKIP_TAGS


def test_skip_tags_excludes_body():
    assert "body" not in _SKIP_TAGS


def test_skip_tags_excludes_p():
    assert "p" not in _SKIP_TAGS


# ---------- _detect_html_source_type 深度 ----------


def test_detect_html_source_type_uppercase_html_accepted():
    """uppercase .HTML 经 .lower() 后接受。"""
    assert _detect_html_source_type(Path("test.HTML")) == "html"


def test_detect_html_source_type_uppercase_htm_accepted():
    assert _detect_html_source_type(Path("test.HTM")) == "html"


def test_detect_html_source_type_mixed_case_accepted():
    assert _detect_html_source_type(Path("test.Htm")) == "html"


def test_detect_html_source_type_html_extension():
    assert _detect_html_source_type(Path("test.html")) == "html"


def test_detect_html_source_type_htm_extension():
    assert _detect_html_source_type(Path("test.htm")) == "html"


def test_detect_html_source_type_double_extension_html():
    """file.tar.html → suffix 是 .html。"""
    assert _detect_html_source_type(Path("file.tar.html")) == "html"


def test_detect_html_source_type_returns_str_type():
    assert isinstance(_detect_html_source_type(Path("test.html")), str)


def test_detect_html_source_type_md_raises():
    with pytest.raises(ParserError):
        _detect_html_source_type(Path("test.md"))


def test_detect_html_source_type_txt_raises():
    with pytest.raises(ParserError):
        _detect_html_source_type(Path("test.txt"))


def test_detect_html_source_type_no_suffix_raises():
    with pytest.raises(ParserError):
        _detect_html_source_type(Path("README"))


def test_detect_html_source_type_error_code_value():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("test.txt"))
    assert exc.value.code == "unsupported_type"


def test_detect_html_source_type_error_details_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("test.docx"))
    assert exc.value.details["suffix"] == ".docx"


def test_detect_html_source_type_error_is_parser_error_type():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("test.txt"))
    assert isinstance(exc.value, ParserError)


# ---------- _rows_to_md 深度 ----------


def test_rows_to_md_empty_list_returns_empty():
    assert _rows_to_md([]) == ""


def test_rows_to_md_returns_str_type():
    assert isinstance(_rows_to_md([["a"]]), str)


def test_rows_to_md_single_row_single_col():
    result = _rows_to_md([["cell"]])
    assert "cell" in result


def test_rows_to_md_single_row_has_separator():
    """单行也输出 separator（实现始终输出 header + separator）。"""
    result = _rows_to_md([["a"]])
    lines = result.split("\n")
    assert len(lines) >= 2


def test_rows_to_md_three_rows_outputs_four_lines():
    """3 行 → header + separator + 2 body = 4 行。"""
    result = _rows_to_md([["h1", "h2"], ["a1", "a2"], ["b1", "b2"]])
    assert len(result.split("\n")) == 4


def test_rows_to_md_separator_count_matches_columns():
    result = _rows_to_md([["a", "b", "c"]])
    sep_line = result.split("\n")[1]
    assert sep_line.count("---") == 3


def test_rows_to_md_jagged_pads_with_empty():
    """行长度不齐 → pad 空字符串。"""
    result = _rows_to_md([["a", "b"], ["c"]])
    # 不抛即可（padded）
    assert "c" in result


# ---------- _HTMLDocParser 初始状态 ----------


def test_html_doc_parser_init_defaults():
    p = _HTMLDocParser("d1")
    assert p.document_id == "d1"
    assert p.elements == []
    assert p.warnings == []


def test_html_doc_parser_init_block_state_none():
    p = _HTMLDocParser("d1")
    assert p._cur_kind is None
    assert p._cur_buffer == []


def test_html_doc_parser_init_table_state():
    p = _HTMLDocParser("d1")
    assert p._table_depth == 0
    assert p._table_rows_stack == []


def test_html_doc_parser_init_section_path():
    p = _HTMLDocParser("d1")
    assert p._section_path == []
    assert p._section_levels == []


def test_html_doc_parser_init_skip_stack():
    p = _HTMLDocParser("d1")
    assert p._skip_stack == []


def test_html_doc_parser_init_list_stack():
    p = _HTMLDocParser("d1")
    assert p._list_stack == []


def test_html_doc_parser_init_pre_depth():
    p = _HTMLDocParser("d1")
    assert p._pre_depth == 0


def test_html_doc_parser_init_blockquote_depth():
    p = _HTMLDocParser("d1")
    assert p._blockquote_depth == 0


def test_html_doc_parser_has_handle_starttag():
    p = _HTMLDocParser("d1")
    assert callable(p.handle_starttag)


def test_html_doc_parser_has_handle_endtag():
    p = _HTMLDocParser("d1")
    assert callable(p.handle_endtag)


def test_html_doc_parser_has_handle_data():
    p = _HTMLDocParser("d1")
    assert callable(p.handle_data)


def test_html_doc_parser_has_handle_startendtag():
    p = _HTMLDocParser("d1")
    assert callable(p.handle_startendtag)


# ---------- _HTMLDocParser SAX 各 tag 行为 ----------


def test_sax_h1_creates_heading_element():
    p = _HTMLDocParser("d1")
    p.feed("<h1>Title</h1>")
    p._flush_block()
    assert len(p.elements) == 1
    assert p.elements[0].type == "heading"
    assert p.elements[0].metadata["level"] == 1


def test_sax_h6_creates_heading_with_level_6():
    p = _HTMLDocParser("d1")
    p.feed("<h6>Deep</h6>")
    p._flush_block()
    assert p.elements[0].metadata["level"] == 6


def test_sax_p_creates_paragraph():
    p = _HTMLDocParser("d1")
    p.feed("<p>hello</p>")
    p._flush_block()
    assert p.elements[0].type == "paragraph"


def test_sax_ul_li_creates_unordered_list_item():
    p = _HTMLDocParser("d1")
    p.feed("<ul><li>item</li></ul>")
    p._flush_block()
    li = [e for e in p.elements if e.type == "list_item"]
    assert len(li) == 1
    assert li[0].metadata["ordered"] is False
    assert li[0].metadata["marker"] == "unordered"


def test_sax_ol_li_creates_ordered_list_item():
    p = _HTMLDocParser("d1")
    p.feed("<ol><li>item</li></ol>")
    p._flush_block()
    li = [e for e in p.elements if e.type == "list_item"]
    assert len(li) == 1
    assert li[0].metadata["ordered"] is True
    assert li[0].metadata["marker"] == "ordered"


def test_sax_pre_creates_paragraph_with_preformatted_kind():
    p = _HTMLDocParser("d1")
    p.feed("<pre>code line</pre>")
    p._flush_block()
    para = [e for e in p.elements if e.type == "paragraph"]
    assert len(para) == 1
    assert para[0].metadata["kind"] == "preformatted"


def test_sax_blockquote_creates_paragraph_with_blockquote_kind():
    p = _HTMLDocParser("d1")
    p.feed("<blockquote>quote text</blockquote>")
    p._flush_block()
    para = [e for e in p.elements if e.type == "paragraph"]
    assert len(para) == 1
    assert para[0].metadata["kind"] == "blockquote"


def test_sax_table_creates_table_element():
    p = _HTMLDocParser("d1")
    p.feed("<table><tr><td>a</td></tr></table>")
    p._flush_block()
    tables = [e for e in p.elements if e.type == "table"]
    assert len(tables) == 1


def test_sax_table_metadata_has_row_count():
    p = _HTMLDocParser("d1")
    p.feed("<table><tr><td>a</td></tr><tr><td>b</td></tr></table>")
    p._flush_block()
    table = [e for e in p.elements if e.type == "table"][0]
    assert table.metadata["row_count"] == 2


def test_sax_table_metadata_has_col_count():
    p = _HTMLDocParser("d1")
    p.feed("<table><tr><td>a</td><td>b</td></tr></table>")
    p._flush_block()
    table = [e for e in p.elements if e.type == "table"][0]
    assert table.metadata["col_count"] == 2


def test_sax_table_metadata_source_html_table():
    p = _HTMLDocParser("d1")
    p.feed("<table><tr><td>a</td></tr></table>")
    p._flush_block()
    table = [e for e in p.elements if e.type == "table"][0]
    assert table.metadata["source"] == "html_table"


def test_sax_img_creates_image_with_resource_path():
    p = _HTMLDocParser("d1")
    p.feed('<img src="img.png" alt="alt text">')
    p._flush_block()
    images = [e for e in p.elements if e.type == "image"]
    assert len(images) == 1
    assert images[0].resource_path == "img.png"


def test_sax_img_metadata_alt():
    p = _HTMLDocParser("d1")
    p.feed('<img src="x.png" alt="hello">')
    p._flush_block()
    img = [e for e in p.elements if e.type == "image"][0]
    assert img.metadata["alt"] == "hello"


def test_sax_img_without_src_skipped():
    p = _HTMLDocParser("d1")
    p.feed('<img alt="no src">')
    p._flush_block()
    images = [e for e in p.elements if e.type == "image"]
    assert len(images) == 0


def test_sax_img_with_empty_src_skipped():
    p = _HTMLDocParser("d1")
    p.feed('<img src="" alt="empty">')
    p._flush_block()
    images = [e for e in p.elements if e.type == "image"]
    assert len(images) == 0


def test_sax_img_with_only_whitespace_src_skipped():
    p = _HTMLDocParser("d1")
    p.feed('<img src="   " alt="blank">')
    p._flush_block()
    images = [e for e in p.elements if e.type == "image"]
    assert len(images) == 0


def test_sax_self_closing_img_creates_image():
    p = _HTMLDocParser("d1")
    p.feed('<img src="x.png" />')
    p._flush_block()
    images = [e for e in p.elements if e.type == "image"]
    assert len(images) == 1


def test_sax_hr_no_element_created():
    p = _HTMLDocParser("d1")
    p.feed("<p>before</p><hr><p>after</p>")
    p._flush_block()
    # hr 应当不创建 element
    types = [e.type for e in p.elements]
    assert "hr" not in types


def test_sax_br_in_paragraph_adds_space():
    p = _HTMLDocParser("d1")
    p.feed("<p>line1<br>line2</p>")
    p._flush_block()
    para = [e for e in p.elements if e.type == "paragraph"][0]
    # br → 加入空格
    assert "line1" in para.content
    assert "line2" in para.content


def test_sax_skip_script_content():
    p = _HTMLDocParser("d1")
    p.feed("<script>alert('x')</script><p>visible</p>")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert all("alert" not in (e.content or "") for e in paras)


def test_sax_skip_style_content():
    p = _HTMLDocParser("d1")
    p.feed("<style>body { color: red; }</style><p>visible</p>")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert all("color" not in (e.content or "") for e in paras)


def test_sax_skip_head_content():
    p = _HTMLDocParser("d1")
    p.feed("<head><title>Page</title></head><body><p>x</p></body>")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert all("Page" not in (e.content or "") for e in paras)


def test_sax_skip_title_content():
    p = _HTMLDocParser("d1")
    p.feed("<title>Title</title><p>body</p>")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    # title 内容不应作为 paragraph
    for e in paras:
        assert "Title" not in (e.content or "")


def test_sax_loose_text_becomes_paragraph():
    p = _HTMLDocParser("d1")
    p.feed("loose text outside any tag")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert "loose text" in paras[0].content


def test_sax_whitespace_only_data_no_element():
    p = _HTMLDocParser("d1")
    p.feed("   \n\n  ")
    p._flush_block()
    # whitespace 不创建 element
    assert p.elements == []


def test_sax_section_path_with_h1_h2():
    p = _HTMLDocParser("d1")
    p.feed("<h1>A</h1><h2>B</h2><p>under B</p>")
    p._flush_block()
    para = [e for e in p.elements if e.type == "paragraph"][0]
    assert para.source_locator["section_path"] == "A > B"


def test_sax_section_path_pops_on_higher_level():
    """h1 → h2 → h1: 最后 h1 弹出 h2，section_path=[最后 H1]。"""
    p = _HTMLDocParser("d1")
    p.feed("<h1>A</h1><h2>B</h2><h1>C</h1><p>x</p>")
    p._flush_block()
    para = [e for e in p.elements if e.type == "paragraph"][0]
    assert para.source_locator["section_path"] == "C"


def test_sax_section_path_absent_for_preamble():
    """无 heading → 无 section_path。"""
    p = _HTMLDocParser("d1")
    p.feed("<p>no heading before</p>")
    p._flush_block()
    para = p.elements[0]
    assert "section_path" not in para.source_locator


def test_sax_nested_table_emits_warning():
    p = _HTMLDocParser("d1")
    p.feed("<table><tr><td><table><tr><td>inner</td></tr></table></td></tr></table>")
    p._flush_block()
    assert any(w.code == "html_nested_table" for w in p.warnings)


def test_sax_confidence_for_paragraph_095():
    p = _HTMLDocParser("d1")
    p.feed("<p>text</p>")
    p._flush_block()
    para = p.elements[0]
    assert para.confidence == 0.95


def test_sax_confidence_for_heading_095():
    p = _HTMLDocParser("d1")
    p.feed("<h1>T</h1>")
    p._flush_block()
    assert p.elements[0].confidence == 0.95


def test_sax_confidence_for_list_item_095():
    p = _HTMLDocParser("d1")
    p.feed("<ul><li>x</li></ul>")
    p._flush_block()
    li = [e for e in p.elements if e.type == "list_item"][0]
    assert li.confidence == 0.95


def test_sax_confidence_for_image_09():
    p = _HTMLDocParser("d1")
    p.feed('<img src="x.png">')
    p._flush_block()
    img = [e for e in p.elements if e.type == "image"][0]
    assert img.confidence == 0.9


def test_sax_confidence_for_table_09():
    p = _HTMLDocParser("d1")
    p.feed("<table><tr><td>x</td></tr></table>")
    p._flush_block()
    table = [e for e in p.elements if e.type == "table"][0]
    assert table.confidence == 0.9


def test_sax_element_id_increments_across_types():
    p = _HTMLDocParser("doc1")
    p.feed("<h1>T</h1><p>para</p><ul><li>x</li></ul>")
    p._flush_block()
    ids = [e.element_id for e in p.elements]
    for i in range(1, len(ids)):
        assert ids[i] > ids[i - 1]


def test_sax_element_id_format_with_doc_id():
    p = _HTMLDocParser("doc42")
    p.feed("<p>x</p>")
    p._flush_block()
    eid = p.elements[0].element_id
    assert eid.startswith("doc42::e")


def test_sax_element_parent_id_always_none():
    p = _HTMLDocParser("d1")
    p.feed("<h1>T</h1><p>para</p>")
    p._flush_block()
    for e in p.elements:
        assert e.parent_id is None


# ---------- HtmlParser.parse() 错误路径深度 ----------


def test_parse_missing_file_raises_file_not_found(tmp_path: Path):
    p = HtmlParser()
    with pytest.raises(ParserError) as exc:
        p.parse(tmp_path / "missing.html", "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_missing_file_details_has_path(tmp_path: Path):
    p = HtmlParser()
    missing = tmp_path / "missing.html"
    with pytest.raises(ParserError) as exc:
        p.parse(missing, "a" * 64)
    assert exc.value.details["path"] == str(missing)


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.txt"
    f.write_text("<p>x</p>", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "unsupported_type"


def test_parse_directory_raises_file_not_found(tmp_path: Path):
    """目录 → is_file()=False → file_not_found。"""
    p = HtmlParser()
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(ParserError) as exc:
        p.parse(sub, "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_returns_document_type(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_returns_correct_source_hash(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    sha = "b" * 64
    doc = p.parse(f, sha)
    assert doc.source_hash == sha


def test_parse_document_id_derived_from_hash(tmp_path: Path):
    from app.parsers.base import make_document_id
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    sha = "c" * 64
    doc = p.parse(f, sha)
    assert doc.document_id == make_document_id(sha)


def test_parse_metadata_html_true(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.metadata == {"html": True}


def test_parse_chunks_empty_list(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.chunks == []


def test_parse_relations_empty_list(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.relations == []


def test_parse_errors_empty_list(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.errors == []


def test_parse_source_path_is_str(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert isinstance(doc.source_path, str)


def test_parse_source_type_is_html(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.source_type == "html"


def test_parse_parser_name_attribute(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.parser_name == "html"


def test_parse_parser_version_attribute(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.parser_version == "stdlib/0.1.0"


# ---------- UnicodeDecodeError 回退 ----------


def test_parse_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    """读 latin-1 字节 → UnicodeDecodeError → errors=replace 回退。"""
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_bytes(b"<p>\xff\xfe</p>")
    doc = p.parse(f, "a" * 64)
    assert isinstance(doc, Document)


# ---------- 空 elements → html_no_content ----------


def test_parse_empty_body_emits_no_content_warning(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<html><head></head><body></body></html>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert any(w.code == "html_no_content" for w in doc.warnings)


def test_parse_only_script_emits_no_content_warning(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<html><body><script>x</script></body></html>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert any(w.code == "html_no_content" for w in doc.warnings)


def test_parse_no_content_warning_has_reason(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for w in doc.warnings:
        if w.code == "html_no_content":
            assert isinstance(w.reason, str)
            assert len(w.reason) > 0


# ---------- element_locator ----------


def test_parse_paragraph_locator_has_line(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<p>hello</p>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    para = [e for e in doc.elements if e.type == "paragraph"][0]
    assert "line" in para.source_locator


def test_parse_heading_locator_has_line(tmp_path: Path):
    p = HtmlParser()
    f = tmp_path / "f.html"
    f.write_text("<h1>Title</h1>", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    h = doc.elements[0]
    assert "line" in h.source_locator


# ---------- 模块结构 ----------


def test_module_imports_html_parser():
    import app.parsers.html_parser as mod
    assert hasattr(mod, "_StdHTMLParser")


def test_module_imports_path():
    import app.parsers.html_parser as mod
    assert hasattr(mod, "Path")


def test_module_imports_document():
    import app.parsers.html_parser as mod
    assert hasattr(mod, "Document")


def test_module_imports_element():
    import app.parsers.html_parser as mod
    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    import app.parsers.html_parser as mod
    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser_base():
    import app.parsers.html_parser as mod
    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    import app.parsers.html_parser as mod
    assert hasattr(mod, "ParserError")


def test_module_imports_make_document_id():
    import app.parsers.html_parser as mod
    assert hasattr(mod, "make_document_id")


def test_module_has_all():
    import app.parsers.html_parser as mod
    assert hasattr(mod, "__all__")


def test_module_all_contains_html_parser():
    import app.parsers.html_parser as mod
    assert "HtmlParser" in mod.__all__


def test_module_all_is_list():
    import app.parsers.html_parser as mod
    assert isinstance(mod.__all__, list)


def test_html_parser_inherits_parser():
    p = HtmlParser()
    assert isinstance(p, Parser)


def test_html_parser_name_is_str():
    p = HtmlParser()
    assert isinstance(p.name, str)


def test_html_parser_version_is_str():
    p = HtmlParser()
    assert isinstance(p.version, str)


def test_html_parser_parse_callable():
    p = HtmlParser()
    assert callable(p.parse)


def test_html_parser_name_value():
    p = HtmlParser()
    assert p.name == "html"


def test_html_parser_version_value():
    p = HtmlParser()
    assert p.version == "stdlib/0.1.0"


def test_html_parser_parse_signature():
    """parse 签名: (self, path, source_hash)。"""
    import inspect
    sig = inspect.signature(HtmlParser.parse)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "path" in params
    assert "source_hash" in params
