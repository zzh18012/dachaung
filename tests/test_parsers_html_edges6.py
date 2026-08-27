r"""app/parsers/html_parser.py 边角测试 - 第六轮（Round 163）。

补强已有 base/edges/edges2-5（共 597 测试）未覆盖的深度：
- _HTML_EXTENSIONS 与 _HEADING_LEVELS / _SKIP_TAGS 精确性
- _detect_html_source_type details 精确
- _rows_to_md 边界（empty/单行/uneven/超宽/Unicode）
- _HTMLDocParser 内部状态（initial / 跳过栈 / section stack）
- handle_startendtag 自闭合分支
- handle_endtag 各 tag 分支
- handle_data loose text 与 table cell 累积
- _emit_image 触发 flush
- 嵌套 table 触发 warning
- HtmlParser.parse() 错误路径与 metadata
- 模块结构与签名
- 综合行为
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
    _SKIP_TAGS,
    HtmlParser,
    _detect_html_source_type,
    _rows_to_md,
)


# 共用：64-char hex source_hash
_H = "a" * 64
_H2 = "b" * 64


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# =========================================================================
# 常量精确性
# =========================================================================


def test_html_extensions_exact():
    assert _HTML_EXTENSIONS == (".html", ".htm")


def test_html_extensions_is_tuple():
    assert isinstance(_HTML_EXTENSIONS, tuple)


def test_html_extensions_lowercase():
    for ext in _HTML_EXTENSIONS:
        assert ext == ext.lower()


def test_html_extensions_starts_with_dot():
    for ext in _HTML_EXTENSIONS:
        assert ext.startswith(".")


def test_heading_levels_exact_six_entries():
    assert _HEADING_LEVELS == {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


def test_heading_levels_is_dict():
    assert isinstance(_HEADING_LEVELS, dict)


def test_heading_levels_values_are_int():
    for k, v in _HEADING_LEVELS.items():
        assert isinstance(v, int)
        assert 1 <= v <= 6


def test_skip_tags_exact():
    assert _SKIP_TAGS == {"script", "style", "head", "title", "meta", "link", "noscript"}


def test_skip_tags_is_set():
    assert isinstance(_SKIP_TAGS, set)


def test_skip_tags_all_lowercase():
    for t in _SKIP_TAGS:
        assert t == t.lower()


# =========================================================================
# _detect_html_source_type details
# =========================================================================


def test_detect_html_source_type_html_returns_html():
    assert _detect_html_source_type(Path("foo.html")) == "html"


def test_detect_html_source_type_htm_returns_html():
    assert _detect_html_source_type(Path("foo.htm")) == "html"


def test_detect_html_source_type_uppercase_html_returns_html():
    assert _detect_html_source_type(Path("foo.HTML")) == "html"


def test_detect_html_source_type_uppercase_htm_returns_html():
    assert _detect_html_source_type(Path("foo.HTM")) == "html"


def test_detect_html_source_type_txt_raises():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("foo.txt"))
    assert exc.value.code == "unsupported_type"


def test_detect_html_source_type_no_suffix_raises():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("foo"))
    assert exc.value.details == {"suffix": ""}


def test_detect_html_source_type_txt_details_has_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("foo.txt"))
    assert exc.value.details == {"suffix": ".txt"}


def test_detect_html_source_type_message_mentions_html_htm():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("foo.txt"))
    msg = exc.value.message
    assert ".html" in msg
    assert ".htm" in msg


# =========================================================================
# _rows_to_md 边界
# =========================================================================


def test_rows_to_md_empty_returns_empty_string():
    assert _rows_to_md([]) == ""


def test_rows_to_md_single_row_header_only():
    out = _rows_to_md([["a", "b"]])
    lines = out.split("\n")
    assert len(lines) == 2  # header + separator
    assert lines[0] == "| a | b |"
    assert lines[1] == "| --- | --- |"


def test_rows_to_md_two_rows():
    out = _rows_to_md([["a", "b"], ["1", "2"]])
    lines = out.split("\n")
    assert len(lines) == 3


def test_rows_to_md_pads_uneven():
    out = _rows_to_md([["a", "b", "c"], ["1", "2"]])
    lines = out.split("\n")
    assert lines[2] == "| 1 | 2 |  |"


def test_rows_to_md_max_width_uses_max():
    out = _rows_to_md([["a"], ["1", "2", "3"]])
    lines = out.split("\n")
    assert lines[0] == "| a |  |  |"


def test_rows_to_md_unicode():
    out = _rows_to_md([["中", "文"]])
    assert "中" in out
    assert "文" in out


def test_rows_to_md_empty_cells():
    out = _rows_to_md([["", ""]])
    assert out == "|  |  |\n| --- | --- |"


def test_rows_to_md_separator_format():
    out = _rows_to_md([["a", "b", "c"]])
    lines = out.split("\n")
    assert lines[1] == "| --- | --- | --- |"


# =========================================================================
# _HTMLDocParser 初始状态
# =========================================================================


def test_html_doc_parser_initial_state():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    assert p.document_id == "doc"
    assert p.elements == []
    assert p.warnings == []
    assert p._cur_kind is None
    assert p._cur_buffer == []
    assert p._cur_start_line == 0
    assert p._cur_level == 0
    assert p._cur_ordered is False
    assert p._list_stack == []
    assert p._pre_depth == 0
    assert p._blockquote_depth == 0
    assert p._section_path == []
    assert p._section_levels == []
    assert p._table_depth == 0
    assert p._table_rows_stack == []
    assert p._table_start_lines == []
    assert p._row_buffers_stack == []
    assert p._cell_buffers_stack == []
    assert p._skip_stack == []


def test_html_doc_parser_inherits_stdlib():
    from html.parser import HTMLParser as _StdHTMLParser
    from app.parsers.html_parser import _HTMLDocParser
    assert issubclass(_HTMLDocParser, _StdHTMLParser)


def test_html_doc_parser_convert_charrefs_true():
    """convert_charrefs=True 默认。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    assert p.convert_charrefs is True


def test_html_doc_parser_has_sax_methods():
    from app.parsers.html_parser import _HTMLDocParser
    for m in ("handle_starttag", "handle_endtag", "handle_data", "handle_startendtag"):
        assert hasattr(_HTMLDocParser, m)


def test_html_doc_parser_has_internal_helpers():
    from app.parsers.html_parser import _HTMLDocParser
    for m in (
        "_flush_block",
        "_reset_block",
        "_start_block",
        "_make_locator_for_current",
        "_make_locator_for_inline",
        "_emit_image",
        "_handle_table_inner_start",
        "_handle_table_inner_end",
    ):
        assert hasattr(_HTMLDocParser, m)


# =========================================================================
# _HTMLDocParser - 标题/段落/列表基本流程
# =========================================================================


def test_html_doc_parser_h1_emits_heading_with_level_1():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<h1>Title</h1>")
    p._flush_block()
    headings = [e for e in p.elements if e.type == "heading"]
    assert len(headings) == 1
    assert headings[0].metadata["level"] == 1
    assert headings[0].content == "Title"


def test_html_doc_parser_h6_emits_heading_with_level_6():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<h6>Small Title</h6>")
    p._flush_block()
    headings = [e for e in p.elements if e.type == "heading"]
    assert headings[0].metadata["level"] == 6


def test_html_doc_parser_section_path_after_h1_h2():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<h1>A</h1><h2>B</h2><p>text</p>")
    p._flush_block()
    para = [e for e in p.elements if e.type == "paragraph"][0]
    assert para.source_locator["section_path"] == "A > B"


def test_html_doc_parser_section_path_pop_on_higher_heading():
    """h1 > h2 > h3, 再出现 h2 应弹掉 h3。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<h1>A</h1><h2>B</h2><h3>C</h3><h2>D</h2><p>text</p>")
    p._flush_block()
    para = [e for e in p.elements if e.type == "paragraph"][0]
    assert para.source_locator["section_path"] == "A > D"


def test_html_doc_parser_p_emits_paragraph():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<p>hello</p>")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "hello"
    # 普通 paragraph 没有 kind
    assert "kind" not in paras[0].metadata


def test_html_doc_parser_loose_text_emits_paragraph():
    """<body> 下的 loose text 也成 paragraph。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("loose text")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "loose text"


def test_html_doc_parser_whitespace_only_data_ignored():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("   \n\t  ")
    p._flush_block()
    assert p.elements == []


def test_html_doc_parser_ul_li_emits_unordered_list_item():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<ul><li>item</li></ul>")
    p._flush_block()
    items = [e for e in p.elements if e.type == "list_item"]
    assert len(items) == 1
    assert items[0].metadata["ordered"] is False
    assert items[0].metadata["marker"] == "unordered"


def test_html_doc_parser_ol_li_emits_ordered_list_item():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<ol><li>item</li></ol>")
    p._flush_block()
    items = [e for e in p.elements if e.type == "list_item"]
    assert items[0].metadata["ordered"] is True
    assert items[0].metadata["marker"] == "ordered"


def test_html_doc_parser_pre_emits_preformatted():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<pre>code line</pre>")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].metadata["kind"] == "preformatted"
    assert paras[0].content == "code line"


def test_html_doc_parser_blockquote_emits_blockquote_kind():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<blockquote>quoted text</blockquote>")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].metadata["kind"] == "blockquote"


def test_html_doc_parser_nested_pre_increments_depth():
    """<pre><pre>inner</pre></pre> — 内层被忽略（不重复 start_block）。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<pre>outer<pre>inner</pre></pre>")
    p._flush_block()
    # 外层 pre 仍然产出 1 个 paragraph
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert len(paras) == 1


def test_html_doc_parser_nested_blockquote_increments_depth():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<blockquote>outer<blockquote>inner</blockquote></blockquote>")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert len(paras) == 1


# =========================================================================
# 图片 / hr / br
# =========================================================================


def test_html_doc_parser_img_with_src_and_alt():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed('<img src="http://example.com/x.png" alt="my alt">')
    p._flush_block()
    images = [e for e in p.elements if e.type == "image"]
    assert len(images) == 1
    assert images[0].resource_path == "http://example.com/x.png"
    assert images[0].metadata["alt"] == "my alt"
    assert images[0].content is None


def test_html_doc_parser_img_no_src_skipped():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed('<img alt="no src">')
    p._flush_block()
    images = [e for e in p.elements if e.type == "image"]
    assert len(images) == 0


def test_html_doc_parser_img_empty_src_skipped():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed('<img src="" alt="empty">')
    p._flush_block()
    images = [e for e in p.elements if e.type == "image"]
    assert len(images) == 0


def test_html_doc_parser_img_src_only():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed('<img src="url">')
    p._flush_block()
    images = [e for e in p.elements if e.type == "image"]
    assert len(images) == 1
    assert images[0].metadata["alt"] == ""


def test_html_doc_parser_startendtag_img_self_closing():
    """<img/> 自闭合走 handle_startendtag。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed('<img src="url1"/>')
    p._flush_block()
    images = [e for e in p.elements if e.type == "image"]
    assert len(images) == 1


def test_html_doc_parser_hr_does_not_emit():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<p>before</p><hr><p>after</p>")
    p._flush_block()
    # hr 自身不产 element
    types = [e.type for e in p.elements]
    assert types.count("paragraph") == 2


def test_html_doc_parser_br_inside_paragraph_adds_space():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<p>line1<br>line2</p>")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert len(paras) == 1
    # br → 空格（可能被 strip 后消失，但内容应同时含 line1/line2）
    assert "line1" in paras[0].content
    assert "line2" in paras[0].content


# =========================================================================
# 跳过栈
# =========================================================================


def test_html_doc_parser_skips_script_content():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<script>var x = 1;</script>")
    p._flush_block()
    assert p.elements == []


def test_html_doc_parser_skips_style_content():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<style>body { color: red; }</style>")
    p._flush_block()
    assert p.elements == []


def test_html_doc_parser_skips_head_content():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<head><title>title</title></head>")
    p._flush_block()
    assert p.elements == []


def test_html_doc_parser_skips_meta_link_noscript():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed('<meta charset="utf-8"><link rel="x"><noscript>fallback</noscript>')
    p._flush_block()
    assert p.elements == []


def test_html_doc_parser_nested_same_skip_tag():
    """<script> 内的 <script> 文本被当作 CDATA（html.parser 行为），
    第一个 </script> 关闭外层 → 之后文本变 loose paragraph。
    这不是真正嵌套，验证 html.parser 实际行为。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<script>outer<script>inner</script>still skip</script>")
    p._flush_block()
    # 第一个 </script> 关闭外层，"still skip" 作为 loose paragraph 产 element
    # 第二个 </script> 是孤儿 endtag，无效果
    assert len(p.elements) == 1
    assert p.elements[0].content == "still skip"


def test_html_doc_parser_skip_then_normal_text_emits():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<script>x</script><p>visible</p>")
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "visible"


# =========================================================================
# 表格
# =========================================================================


def test_html_doc_parser_basic_table():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<table><tr><td>a</td><td>b</td></tr></table>")
    p._flush_block()
    tables = [e for e in p.elements if e.type == "table"]
    assert len(tables) == 1
    assert tables[0].metadata["row_count"] == 1
    assert tables[0].metadata["col_count"] == 2
    assert tables[0].metadata["source"] == "html_table"


def test_html_doc_parser_table_with_header_and_body():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed(
        "<table>"
        "<tr><th>H1</th><th>H2</th></tr>"
        "<tr><td>1</td><td>2</td></tr>"
        "</table>"
    )
    p._flush_block()
    tables = [e for e in p.elements if e.type == "table"]
    assert tables[0].metadata["row_count"] == 2


def test_html_doc_parser_nested_table_emits_warning():
    """嵌套 table 触发 html_nested_table warning。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed(
        "<table><tr><td>outer</td>"
        "<td><table><tr><td>inner</td></tr></table></td>"
        "</tr></table>"
    )
    p._flush_block()
    nested_warnings = [w for w in p.warnings if w.code == "html_nested_table"]
    assert len(nested_warnings) >= 1


def test_html_doc_parser_table_empty_no_element():
    """空 table（无 <tr>）→ rows 空 → _rows_to_md 返回 ""，不产 element。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<table></table>")
    p._flush_block()
    tables = [e for e in p.elements if e.type == "table"]
    assert len(tables) == 0


def test_html_doc_parser_table_col_count_max():
    """col_count = 各 row 最长。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed(
        "<table>"
        "<tr><td>a</td></tr>"
        "<tr><td>b</td><td>c</td><td>d</td></tr>"
        "</table>"
    )
    p._flush_block()
    tables = [e for e in p.elements if e.type == "table"]
    assert tables[0].metadata["col_count"] == 3


def test_html_doc_parser_table_text_in_cells_aggregated():
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<table><tr><td>hello world</td></tr></table>")
    p._flush_block()
    tables = [e for e in p.elements if e.type == "table"]
    assert "hello" in tables[0].content
    assert "world" in tables[0].content


# =========================================================================
# HtmlParser 类属性与 parse()
# =========================================================================


def test_html_parser_name_value():
    assert HtmlParser.name == "html"


def test_html_parser_version_value():
    assert HtmlParser.version == "stdlib/0.1.0"


def test_html_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(HtmlParser, Parser)


def test_html_parser_init_no_args():
    p = HtmlParser()
    assert p is not None


def test_parse_nonexistent_file_raises(tmp_path: Path):
    p = tmp_path / "missing.html"
    with pytest.raises(ParserError) as exc:
        HtmlParser().parse(p, _H)
    assert exc.value.code == "file_not_found"
    assert str(p) in exc.value.message


def test_parse_nonexistent_file_details(tmp_path: Path):
    p = tmp_path / "missing.html"
    with pytest.raises(ParserError) as exc:
        HtmlParser().parse(p, _H)
    assert exc.value.details == {"path": str(p)}


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = _write(tmp_path, "foo.txt", "hello")
    with pytest.raises(ParserError) as exc:
        HtmlParser().parse(p, _H)
    assert exc.value.code == "unsupported_type"


def test_parse_returns_document(tmp_path: Path):
    p = _write(tmp_path, "test.html", "<p>hello</p>")
    doc = HtmlParser().parse(p, _H)
    assert isinstance(doc, Document)


def test_parse_uses_make_document_id(tmp_path: Path):
    from app.parsers.base import make_document_id
    p = _write(tmp_path, "test.html", "<p>hello</p>")
    doc = HtmlParser().parse(p, _H)
    assert doc.document_id == make_document_id(_H)


def test_parse_metadata_has_html_true(tmp_path: Path):
    p = _write(tmp_path, "test.html", "<p>hello</p>")
    doc = HtmlParser().parse(p, _H)
    assert doc.metadata == {"html": True}


def test_parse_source_type_html(tmp_path: Path):
    p = _write(tmp_path, "test.html", "<p>hello</p>")
    doc = HtmlParser().parse(p, _H)
    assert doc.source_type == "html"


def test_parse_source_path_is_str(tmp_path: Path):
    p = _write(tmp_path, "test.html", "<p>hello</p>")
    doc = HtmlParser().parse(p, _H)
    assert isinstance(doc.source_path, str)
    assert doc.source_path == str(p)


def test_parse_source_hash_propagated(tmp_path: Path):
    p = _write(tmp_path, "test.html", "<p>hello</p>")
    doc = HtmlParser().parse(p, _H)
    assert doc.source_hash == _H


def test_parse_parser_name_propagated(tmp_path: Path):
    p = _write(tmp_path, "test.html", "<p>hello</p>")
    doc = HtmlParser().parse(p, _H)
    assert doc.parser_name == "html"


def test_parse_parser_version_propagated(tmp_path: Path):
    p = _write(tmp_path, "test.html", "<p>hello</p>")
    doc = HtmlParser().parse(p, _H)
    assert doc.parser_version == "stdlib/0.1.0"


def test_parse_empty_relations_chunks_errors(tmp_path: Path):
    p = _write(tmp_path, "test.html", "<p>hello</p>")
    doc = HtmlParser().parse(p, _H)
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []


def test_parse_empty_body_emits_no_content_warning(tmp_path: Path):
    """空 body → 无 element → html_no_content warning。"""
    p = _write(tmp_path, "empty.html", "<html><head><title>x</title></head><body></body></html>")
    doc = HtmlParser().parse(p, _H)
    assert any(w.code == "html_no_content" for w in doc.warnings)


def test_parse_script_only_emits_no_content_warning(tmp_path: Path):
    p = _write(tmp_path, "x.html", "<html><body><script>var x=1;</script></body></html>")
    doc = HtmlParser().parse(p, _H)
    assert any(w.code == "html_no_content" for w in doc.warnings)


def test_parse_htm_extension_works(tmp_path: Path):
    p = _write(tmp_path, "test.htm", "<p>hi</p>")
    doc = HtmlParser().parse(p, _H)
    assert doc.source_type == "html"


# =========================================================================
# 综合行为
# =========================================================================


def test_parse_idempotent_same_file(tmp_path: Path):
    p = _write(tmp_path, "test.html", "<h1>T</h1><p>hello</p>")
    d1 = HtmlParser().parse(p, _H)
    d2 = HtmlParser().parse(p, _H)
    assert d1.document_id == d2.document_id
    assert len(d1.elements) == len(d2.elements)


def test_parse_different_hash_different_doc_id(tmp_path: Path):
    p = _write(tmp_path, "test.html", "<p>hi</p>")
    d1 = HtmlParser().parse(p, _H)
    d2 = HtmlParser().parse(p, _H2)
    assert d1.document_id != d2.document_id


def test_parse_complex_document(tmp_path: Path):
    content = """<html><body>
<h1>Main Title</h1>
<h2>Section</h2>
<p>Paragraph 1.</p>
<ul><li>item 1</li><li>item 2</li></ul>
<ol><li>ordered 1</li></ol>
<blockquote>quote text</blockquote>
<pre>code here</pre>
<table>
<tr><th>H1</th><th>H2</th></tr>
<tr><td>1</td><td>2</td></tr>
</table>
<img src="image.png" alt="pic">
</body></html>"""
    p = _write(tmp_path, "complex.html", content)
    doc = HtmlParser().parse(p, _H)
    types = {e.type for e in doc.elements}
    assert "heading" in types
    assert "paragraph" in types
    assert "list_item" in types
    assert "table" in types
    assert "image" in types
    # 检查 preformatted / blockquote kind
    kinds = [e.metadata.get("kind") for e in doc.elements]
    assert "preformatted" in kinds
    assert "blockquote" in kinds


def test_parse_char_entity_converted(tmp_path: Path):
    """&amp; &lt; &gt; 自动转换。"""
    p = _write(tmp_path, "x.html", "<p>a &amp; b &lt; c &gt; d</p>")
    doc = HtmlParser().parse(p, _H)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert "&" in paras[0].content
    assert "<" in paras[0].content
    assert ">" in paras[0].content


def test_parse_numeric_char_entity_converted(tmp_path: Path):
    """&#65; → 'A'。"""
    p = _write(tmp_path, "x.html", "<p>&#65;&#66;&#67;</p>")
    doc = HtmlParser().parse(p, _H)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert "ABC" in paras[0].content


def test_parse_invalid_markup_does_not_raise(tmp_path: Path):
    """未闭合 tag 也不应抛（html.parser 容错）。"""
    p = _write(tmp_path, "x.html", "<p>unclosed paragraph")
    doc = HtmlParser().parse(p, _H)
    # 应至少产 1 个 element（loose text 或 paragraph）
    assert len(doc.elements) >= 1


# =========================================================================
# element_id 与 confidence
# =========================================================================


def test_html_doc_parser_element_id_zero_padded(tmp_path: Path):
    p = _write(tmp_path, "x.html", "<p>a</p><p>b</p>")
    doc = HtmlParser().parse(p, _H)
    ids = [e.element_id for e in doc.elements]
    assert ids[0].endswith("::e0000")
    assert ids[1].endswith("::e0001")


def test_html_doc_parser_heading_confidence_095(tmp_path: Path):
    p = _write(tmp_path, "x.html", "<h1>T</h1>")
    doc = HtmlParser().parse(p, _H)
    h = [e for e in doc.elements if e.type == "heading"][0]
    assert h.confidence == 0.95


def test_html_doc_parser_table_confidence_09(tmp_path: Path):
    """table 的 confidence 是 0.9（不是 0.95）。"""
    p = _write(tmp_path, "x.html", "<table><tr><td>x</td></tr></table>")
    doc = HtmlParser().parse(p, _H)
    t = [e for e in doc.elements if e.type == "table"][0]
    assert t.confidence == 0.9


def test_html_doc_parser_image_confidence_09(tmp_path: Path):
    """image 的 confidence 是 0.9。"""
    p = _write(tmp_path, "x.html", '<img src="url">')
    doc = HtmlParser().parse(p, _H)
    img = [e for e in doc.elements if e.type == "image"][0]
    assert img.confidence == 0.9


# =========================================================================
# 模块结构与签名
# =========================================================================


def test_module_all_exact():
    import app.parsers.html_parser as mod
    assert mod.__all__ == ["HtmlParser"]


def test_module_all_is_list():
    import app.parsers.html_parser as mod
    assert isinstance(mod.__all__, list)


def test_module_uses_future_annotations():
    import app.parsers.html_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_imports_stdlib_html_parser():
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


def test_module_docstring_present():
    import app.parsers.html_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_supported_tags():
    import app.parsers.html_parser as mod
    doc = mod.__doc__
    assert "h1" in doc.lower() or "h2" in doc.lower()


def test_module_docstring_mentions_unsupported():
    """docstring 提及"嵌套 table"等不支持的功能。"""
    import app.parsers.html_parser as mod
    doc = mod.__doc__
    assert "嵌套" in doc or "nested" in doc.lower()


def test_html_parser_parse_signature():
    sig = inspect.signature(HtmlParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


def test_html_parser_parse_params_no_defaults():
    sig = inspect.signature(HtmlParser.parse)
    for p in sig.parameters.values():
        if p.name == "self":
            continue
        assert p.default is inspect.Parameter.empty


def test_html_parser_parse_return_annotation_document():
    sig = inspect.signature(HtmlParser.parse)
    assert "Document" in str(sig.return_annotation)


def test_detect_html_source_type_signature():
    sig = inspect.signature(_detect_html_source_type)
    assert set(sig.parameters) == {"path"}


def test_detect_html_source_type_return_annotation_str():
    sig = inspect.signature(_detect_html_source_type)
    assert "str" in str(sig.return_annotation)


def test_rows_to_md_signature():
    sig = inspect.signature(_rows_to_md)
    assert set(sig.parameters) == {"rows"}


def test_rows_to_md_return_annotation_str():
    sig = inspect.signature(_rows_to_md)
    assert "str" in str(sig.return_annotation)


# =========================================================================
# _HTMLDocParser close 行为
# =========================================================================


def test_html_doc_parser_close_does_not_raise():
    """close() 调用 stdlib 内部清理，不应抛异常。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<p>text")
    p.close()


def test_html_doc_parser_flush_idempotent():
    """连续 flush 不应产 duplicate element。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<p>text</p>")
    p._flush_block()
    n1 = len(p.elements)
    p._flush_block()
    n2 = len(p.elements)
    assert n1 == n2


def test_html_doc_parser_flush_when_no_block_returns():
    """无 active block 时 flush 直接返回。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p._flush_block()
    assert p.elements == []


def test_html_doc_parser_flush_empty_block_no_element():
    """active block 但内容为空 → 不产 element。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<p>   </p>")  # 仅空白
    p._flush_block()
    paras = [e for e in p.elements if e.type == "paragraph"]
    assert len(paras) == 0


# =========================================================================
# locator 行为
# =========================================================================


def test_html_doc_parser_heading_locator_has_line_no_section_in_heading():
    """heading element 的 locator.line 是 start_line；section_path 已包含自身。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<h1>T</h1>")
    p._flush_block()
    h = [e for e in p.elements if e.type == "heading"][0]
    assert "line" in h.source_locator
    assert "section_path" in h.source_locator
    assert h.source_locator["section_path"] == "T"


def test_html_doc_parser_no_section_path_when_no_heading():
    """无 heading → locator 不含 section_path。"""
    from app.parsers.html_parser import _HTMLDocParser
    p = _HTMLDocParser("doc")
    p.feed("<p>text</p>")
    p._flush_block()
    para = [e for e in p.elements if e.type == "paragraph"][0]
    assert "section_path" not in para.source_locator
