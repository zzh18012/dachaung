"""app/parsers/html_parser.py 边角测试（Round 57）。

补强 tests/test_parsers_html.py（61 个测试）未覆盖的：
- 模块级常量深入（_HTML_EXTENSIONS / _HEADING_LEVELS / _SKIP_TAGS）
- _HTMLDocParser 初始化属性默认值
- _detect_html_source_type 边角（双扩展名/dotfile/混合大小写）
- _rows_to_md 边角（jagged / 多列）
- HtmlParser 实例复用
- HtmlParser 大文件 / Unicode / 混合换行
- HtmlParser 错误路径 details 完整性
- HtmlParser schema 通过
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers.html_parser import (
    HtmlParser,
    _detect_html_source_type,
    _HEADING_LEVELS,
    _HTMLDocParser,
    _HTML_EXTENSIONS,
    _rows_to_md,
    _SKIP_TAGS,
)


# ---------- 模块级常量 ----------


def test_html_extensions_constant_is_tuple():
    assert isinstance(_HTML_EXTENSIONS, tuple)


def test_html_extensions_constant_contains_html_and_htm():
    assert set(_HTML_EXTENSIONS) == {".html", ".htm"}


def test_html_extensions_lowercase_only():
    for ext in _HTML_EXTENSIONS:
        assert ext == ext.lower()


def test_heading_levels_constant_dict():
    assert isinstance(_HEADING_LEVELS, dict)


def test_heading_levels_six_levels():
    """6 个标题等级 h1-h6。"""
    assert set(_HEADING_LEVELS.keys()) == {"h1", "h2", "h3", "h4", "h5", "h6"}
    assert set(_HEADING_LEVELS.values()) == {1, 2, 3, 4, 5, 6}


def test_heading_levels_mapping_correct():
    assert _HEADING_LEVELS["h1"] == 1
    assert _HEADING_LEVELS["h6"] == 6


def test_skip_tags_constant_is_set():
    assert isinstance(_SKIP_TAGS, set)


def test_skip_tags_constant_includes_known_tags():
    """已知跳过 tag：script/style/head/title/meta/link/noscript。"""
    expected = {"script", "style", "head", "title", "meta", "link", "noscript"}
    assert expected.issubset(_SKIP_TAGS)


def test_skip_tags_constant_excludes_body_tags():
    """body tags 不应被跳过。"""
    for tag in ("p", "h1", "ul", "ol", "li", "table", "pre", "blockquote", "img"):
        assert tag not in _SKIP_TAGS


def test_html_parser_class_attributes():
    assert HtmlParser.name == "html"
    assert HtmlParser.version == "stdlib/0.1.0"


def test_html_parser_inherits_from_parser():
    from app.parsers.base import Parser
    assert issubclass(HtmlParser, Parser)


def test_html_parser_can_be_instantiated_without_args():
    p = HtmlParser()
    assert p is not None


# ---------- _HTMLDocParser 初始化 ----------


def test_html_doc_parser_init_attributes_default():
    """_HTMLDocParser 初始化时各属性应有正确默认值。"""
    p = _HTMLDocParser(document_id="d1")
    assert p.document_id == "d1"
    assert p.elements == []
    assert p.warnings == []
    assert isinstance(p.elements, list)
    assert isinstance(p.warnings, list)


def test_html_doc_parser_init_section_path_empty():
    p = _HTMLDocParser(document_id="d1")
    assert p._section_path == []
    assert p._section_levels == []


def test_html_doc_parser_init_no_current_block():
    p = _HTMLDocParser(document_id="d1")
    assert p._cur_kind is None
    assert p._cur_buffer == []


def test_html_doc_parser_init_empty_list_stacks():
    p = _HTMLDocParser(document_id="d1")
    assert p._list_stack == []
    assert p._skip_stack == []
    assert p._pre_depth == 0
    assert p._blockquote_depth == 0
    assert p._table_depth == 0


def test_html_doc_parser_init_table_state_empty():
    p = _HTMLDocParser(document_id="d1")
    assert p._table_rows_stack == []
    assert p._table_start_lines == []
    assert p._row_buffers_stack == []
    assert p._cell_buffers_stack == []


def test_html_doc_parser_inherits_from_stdlib_html_parser():
    from html.parser import HTMLParser
    assert issubclass(_HTMLDocParser, HTMLParser)


def test_html_doc_parser_has_handle_methods():
    """应有 SAX 风格的 handle 方法。"""
    p = _HTMLDocParser(document_id="d1")
    assert callable(p.handle_starttag)
    assert callable(p.handle_endtag)
    assert callable(p.handle_data)
    assert callable(p.handle_startendtag)


# ---------- _detect_html_source_type 边角 ----------


def test_detect_html_source_type_returns_str():
    result = _detect_html_source_type(Path("file.html"))
    assert isinstance(result, str)


def test_detect_html_source_type_dotfile():
    """.gitignore.html → suffix 是 '.html'。"""
    # 实际：Path(".gitignore.html").suffix 是 ".html"
    assert _detect_html_source_type(Path(".gitignore.html")) == "html"


def test_detect_html_source_type_double_extension():
    """file.tar.html → suffix 是 '.html'。"""
    assert _detect_html_source_type(Path("file.tar.html")) == "html"


def test_detect_html_source_type_mixed_case_extensions():
    assert _detect_html_source_type(Path("file.HTML")) == "html"
    assert _detect_html_source_type(Path("file.Htm")) == "html"
    assert _detect_html_source_type(Path("file.HTML")) == "html"


def test_detect_html_source_type_no_suffix_raises():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("README"))
    assert exc.value.code == "unsupported_type"


def test_detect_html_source_type_unknown_suffix_raises():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError):
        _detect_html_source_type(Path("file.unknown"))


def test_detect_html_source_type_error_message_contains_suffix():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("file.xxx"))
    assert ".xxx" in exc.value.message


def test_detect_html_source_type_no_suffix_message_has_无():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("noext"))
    assert "(无)" in exc.value.message


def test_detect_html_source_type_md_rejected():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError):
        _detect_html_source_type(Path("file.md"))


# ---------- _rows_to_md 边角补强 ----------


def test_rows_to_md_returns_str_type():
    assert isinstance(_rows_to_md([["a"]]), str)


def test_rows_to_md_jagged_rows_padded():
    """不等长行用 '' 填充。"""
    result = _rows_to_md([
        ["a", "b", "c"],
        ["x"],
    ])
    lines = result.split("\n")
    assert lines[2] == "| x |  |  |"


def test_rows_to_md_many_columns():
    result = _rows_to_md([["c1", "c2", "c3", "c4", "c5"]])
    assert "| c1 | c2 | c3 | c4 | c5 |" in result


def test_rows_to_md_single_column():
    result = _rows_to_md([["only"], ["r1"], ["r2"]])
    lines = result.split("\n")
    assert lines[0] == "| only |"
    assert lines[1] == "| --- |"


def test_rows_to_md_separator_three_dashes():
    result = _rows_to_md([["a", "b"]])
    assert "| --- | --- |" in result


# ---------- HtmlParser 实例复用 ----------


def test_html_parser_can_be_reused_across_files(tmp_path: Path):
    """同一 HtmlParser 实例可解析多个文件，结果独立。"""
    p1 = tmp_path / "a.html"
    p1.write_text("<h1>Title A</h1><p>Content A</p>", encoding="utf-8")
    p2 = tmp_path / "b.html"
    p2.write_text("<h1>Title B</h1><p>Content B</p>", encoding="utf-8")

    parser = HtmlParser()
    doc1 = parser.parse(p1, source_hash="a" * 64)
    doc2 = parser.parse(p2, source_hash="b" * 64)
    assert any("Title A" in (e.content or "") for e in doc1.elements)
    assert any("Title B" in (e.content or "") for e in doc2.elements)
    assert doc1.document_id != doc2.document_id


def test_html_parser_stateless_no_counter_leak(tmp_path: Path):
    """HtmlParser 无实例状态泄漏。"""
    p1 = tmp_path / "a.html"
    p1.write_text("<p>first</p>", encoding="utf-8")
    p2 = tmp_path / "b.html"
    p2.write_text("<p>second</p>", encoding="utf-8")

    parser = HtmlParser()
    doc1 = parser.parse(p1, source_hash="a" * 64)
    doc2 = parser.parse(p2, source_hash="b" * 64)
    # 都从 e0000 开始
    assert doc1.elements[0].element_id.endswith("::e0000")
    assert doc2.elements[0].element_id.endswith("::e0000")


def test_html_parser_sequential_element_ids_in_single_doc(tmp_path: Path):
    """单文档内 element_id 严格递增。"""
    p = tmp_path / "x.html"
    p.write_text(
        "<h1>H1</h1><p>P1</p><ul><li>L1</li></ul><blockquote>Q</blockquote>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    suffixes = [e.element_id.split("::")[-1] for e in doc.elements]
    assert suffixes == sorted(suffixes)
    assert len(set(suffixes)) == len(suffixes)


# ---------- HtmlParser 错误路径 details ----------


def test_html_parser_missing_file_error_details_has_path(tmp_path: Path):
    from app.parsers.base import ParserError
    parser = HtmlParser()
    missing = tmp_path / "nope.html"
    with pytest.raises(ParserError) as exc:
        parser.parse(missing, source_hash="a" * 64)
    assert exc.value.code == "file_not_found"
    assert "path" in exc.value.details
    assert exc.value.details["path"] == str(missing)


def test_html_parser_unsupported_extension_error_details_has_suffix(tmp_path: Path):
    from app.parsers.base import ParserError
    parser = HtmlParser()
    src = tmp_path / "x.unknown"
    src.write_text("<p>hello</p>", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        parser.parse(src, source_hash="a" * 64)
    assert exc.value.code == "unsupported_type"
    assert "suffix" in exc.value.details


# ---------- HtmlParser Document 字段 ----------


def test_html_parser_metadata_fixed_html_true(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("<p>hello</p>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata == {"html": True}


def test_html_parser_warnings_empty_when_elements_exist(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("<p>hello</p>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.warnings == []


def test_html_parser_empty_file_emits_one_warning(tmp_path: Path):
    """空 body → 1 个 warning（不是多个）。"""
    p = tmp_path / "empty.html"
    p.write_text("<html><body></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.warnings) == 1


def test_html_parser_warning_record_has_reason(tmp_path: Path):
    p = tmp_path / "empty.html"
    p.write_text("<html><body></body></html>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    w = doc.warnings[0]
    assert isinstance(w.reason, str)
    assert len(w.reason) > 0


# ---------- HtmlParser 大文件 / Unicode / 换行 ----------


def test_html_parser_large_file(tmp_path: Path):
    """大文件（1000 个段落）应稳定。"""
    p = tmp_path / "large.html"
    body = "<html><body>" + "".join(
        f"<p>Paragraph {i}</p>" for i in range(1000)
    ) + "</body></html>"
    p.write_text(body, encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 1000


def test_html_parser_unicode_content(tmp_path: Path):
    """UTF-8 多字节内容应正常解析。"""
    p = tmp_path / "x.html"
    p.write_text(
        "<h1>标题 🎉</h1><p>你好，世界</p><ul><li>列表项</li></ul>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert any("标题" in (e.content or "") for e in doc.elements)
    assert any("🎉" in (e.content or "") for e in doc.elements)
    assert any("你好" in (e.content or "") for e in doc.elements)


def test_html_parser_crlf_line_endings(tmp_path: Path):
    """CRLF 行结束符应被正确处理。"""
    p = tmp_path / "x.html"
    p.write_bytes(b"<html><body><h1>Title</h1>\r\n<p>Para</p></body></html>")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 2


def test_html_parser_mixed_line_endings(tmp_path: Path):
    """混合 LF / CRLF 行结束符。"""
    p = tmp_path / "x.html"
    p.write_bytes(b"<h1>H</h1>\n<p>P1</p>\r\n<p>P2</p>")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 3


def test_html_parser_single_byte_file(tmp_path: Path):
    """单字节文件（无 HTML 结构）→ loose text → 1 个 paragraph。"""
    p = tmp_path / "x.html"
    p.write_bytes(b"X")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 1


# ---------- HtmlParser malformed / 边角 HTML ----------


def test_html_parser_unclosed_tags_handled(tmp_path: Path):
    """未闭合 tag 应被宽容处理（HTMLParser 自动补救）。"""
    p = tmp_path / "x.html"
    p.write_text("<p>hello<p>world", encoding="utf-8")  # 没 </p>
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # 至少不崩，elements 数 > 0
    assert len(doc.elements) >= 1


def test_html_parser_self_closing_br(tmp_path: Path):
    """<br/> 自闭合 → 当空格处理。"""
    p = tmp_path / "x.html"
    p.write_text("<p>hello<br/>world</p>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert any("hello" in (e.content or "") and "world" in (e.content or "")
               for e in doc.elements)


def test_html_parser_comment_ignored(tmp_path: Path):
    """HTML 注释应被忽略。"""
    p = tmp_path / "x.html"
    p.write_text("<!-- comment --><p>visible</p>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "visible"


def test_html_parser_doctype_ignored(tmp_path: Path):
    """DOCTYPE 声明应被忽略。"""
    p = tmp_path / "x.html"
    p.write_text(
        "<!DOCTYPE html><html><body><p>visible</p></body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 1


def test_html_parser_attribute_with_quotes(tmp_path: Path):
    """img src 含引号包裹的 URL。"""
    p = tmp_path / "x.html"
    p.write_text(
        '<img src="https://example.com/path?x=1&y=2" alt="desc">',
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    img_elements = [e for e in doc.elements if e.type == "image"]
    assert len(img_elements) == 1
    assert "example.com" in (img_elements[0].resource_path or "")


def test_html_parser_nested_same_level_headings(tmp_path: Path):
    """h1 → h2 → h1 应正确处理 section_path。"""
    p = tmp_path / "x.html"
    p.write_text(
        "<h1>A</h1><h2>B</h2><h1>C</h1>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # 3 个 heading elements
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 3


# ---------- HtmlParser schema 通过 ----------


def test_html_parser_result_passes_schema(tmp_path: Path):
    """parse 出的 Document 通过 schema 校验。"""
    from app.schema import is_valid
    p = tmp_path / "x.html"
    p.write_text(
        "<html><body>"
        "<h1>Title</h1>"
        "<p>Paragraph.</p>"
        "<ul><li>item</li></ul>"
        "<pre>code line</pre>"
        "<blockquote>quote</blockquote>"
        "</body></html>",
        encoding="utf-8",
    )
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert is_valid(doc.to_dict()) is True


# ---------- HtmlParser element 字段 ----------


def test_html_parser_element_confidence_strictly_095(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("<p>hello</p>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.confidence == 0.95


def test_html_parser_element_metadata_is_dict(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("<p>hello</p>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert isinstance(el.metadata, dict)


def test_html_parser_source_locator_has_line(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("<p>hello</p>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert "line" in el.source_locator
        assert isinstance(el.source_locator["line"], int)
        assert el.source_locator["line"] >= 1


def test_html_parser_chunks_empty_by_default(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("<p>hello</p>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.chunks == []


def test_html_parser_relations_empty_by_default(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("<p>hello</p>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.relations == []


def test_html_parser_errors_empty_by_default(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("<p>hello</p>", encoding="utf-8")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.errors == []
