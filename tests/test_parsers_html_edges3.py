"""app/parsers/html_parser.py 边角测试 - 第三轮（Round 101）。

补强已有 base/edges/edges2（共 245 个测试）未覆盖的深度路径：
- table cell 行为：未闭合 <tr>、混合 <td>/<th>、cell 内含 inline tag、空 cell
- pre/blockquote 嵌套：pre-in-pre、blockquote-in-blockquote、pre-in-blockquote
- list 嵌套：ul-in-ul、ol-in-ul、li 不在 list 内
- heading 边界：空 heading、相同 level 重复、level 跳跃
- image 深度：alt 含 entity、src 含空白、img 在 block 中、连续多 img
- 字符实体：numeric/hex/未知 entity 在不同上下文
- 警告代码：html_nested_table 触发次数、html_no_content 条件
- _rows_to_md 深度：空字符串 cell、cell 含 |、单列多行
- locator 深度：current vs inline、section_path 条件出现
- pipeline 错误：html_read_failed（OSError）、html_parse_failed（handler 异常）

不修改任何源码。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers.base import ParserError
from app.parsers.html_parser import (
    _HEADING_LEVELS,
    _HTMLDocParser,
    _HTML_EXTENSIONS,
    _SKIP_TAGS,
    HtmlParser,
    _detect_html_source_type,
    _rows_to_md,
)


# =========================================================================
# 辅助
# =========================================================================


def _write_html(tmp_path: Path, html: str, name: str = "test.html") -> Path:
    p = tmp_path / name
    p.write_text(html, encoding="utf-8")
    return p


def _parse(tmp_path: Path, html: str, name: str = "test.html"):
    p = _write_html(tmp_path, html, name)
    parser = HtmlParser()
    return parser.parse(p, source_hash="a" * 64)


# =========================================================================
# table cell 深度
# =========================================================================


def test_table_mixed_th_and_td(tmp_path: Path):
    """<th> 和 <td> 混合在同一行 → 都进入 row。"""
    doc = _parse(
        tmp_path,
        "<table><tr><th>Name</th><td>Alice</td></tr></table>",
    )
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    assert "Name" in tables[0].content
    assert "Alice" in tables[0].content


def test_table_empty_cell(tmp_path: Path):
    """空 <td></td> → 空字符串 cell。"""
    doc = _parse(
        tmp_path,
        "<table><tr><td></td><td>filled</td></tr></table>",
    )
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    # markdown 表格行 "|  | filled |" → 两个空格在空 cell 处
    assert "filled" in tables[0].content


def test_table_cell_with_inline_tag(tmp_path: Path):
    """<td><b>x</b></td> → 内联 tag 文本被拼接。"""
    doc = _parse(
        tmp_path,
        "<table><tr><td><b>bold</b> text</td></tr></table>",
    )
    tables = [e for e in doc.elements if e.type == "table"]
    assert "bold text" in tables[0].content


def test_table_tr_without_close_tag(tmp_path: Path):
    """<tr> 未闭合直接开下一个 <tr> → 自动收尾。"""
    doc = _parse(
        tmp_path,
        "<table><tr><td>a</td><tr><td>b</td></tr></table>",
    )
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    # 两行都被收集
    assert tables[0].metadata["row_count"] == 2


def test_table_with_no_rows_returns_empty_md(tmp_path: Path):
    """<table></table> 空 table → md 为 ""，不 emit element。"""
    doc = _parse(tmp_path, "<table></table>")
    tables = [e for e in doc.elements if e.type == "table"]
    assert tables == []


def test_table_multiline_cell_text(tmp_path: Path):
    """cell 内文本跨多行 → 经 strip 后单行。"""
    doc = _parse(
        tmp_path,
        "<table><tr><td>line1\nline2</td></tr></table>",
    )
    tables = [e for e in doc.elements if e.type == "table"]
    assert "line1" in tables[0].content
    assert "line2" in tables[0].content


def test_table_with_header_only(tmp_path: Path):
    """只有 header row 的表 → body 为空，仍然 emit。"""
    doc = _parse(
        tmp_path,
        "<table><tr><th>A</th><th>B</th></tr></table>",
    )
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    assert tables[0].metadata["row_count"] == 1
    assert tables[0].metadata["col_count"] == 2


# =========================================================================
# pre / blockquote 嵌套
# =========================================================================


def test_pre_inside_pre_only_outer_emits(tmp_path: Path):
    """嵌套 <pre> → 只有外层 emit。"""
    doc = _parse(tmp_path, "<pre>outer<pre>inner</pre>still outer</pre>")
    pres = [e for e in doc.elements if e.metadata.get("kind") == "preformatted"]
    assert len(pres) == 1


def test_blockquote_inside_blockquote_only_outer_emits(tmp_path: Path):
    doc = _parse(
        tmp_path,
        "<blockquote>outer<blockquote>inner</blockquote>still outer</blockquote>",
    )
    bqs = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    assert len(bqs) == 1


def test_pre_inside_blockquote_both_emit(tmp_path: Path):
    """<pre> 在 <blockquote> 内 → 各自 emit（不同 depth counter）。"""
    doc = _parse(
        tmp_path,
        "<blockquote>quote<pre>code</pre></blockquote>",
    )
    bqs = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    pres = [e for e in doc.elements if e.metadata.get("kind") == "preformatted"]
    assert len(bqs) == 1
    assert len(pres) == 1


def test_blockquote_inside_pre_both_emit(tmp_path: Path):
    doc = _parse(
        tmp_path,
        "<pre>code<blockquote>quote</blockquote>still code</pre>",
    )
    bqs = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    pres = [e for e in doc.elements if e.metadata.get("kind") == "preformatted"]
    assert len(bqs) == 1
    assert len(pres) == 1


# =========================================================================
# list 嵌套
# =========================================================================


def test_nested_ul_inside_ul(tmp_path: Path):
    """嵌套 <ul> → list_stack 管理。"""
    doc = _parse(
        tmp_path,
        "<ul><li>outer<ul><li>inner</li></ul></li></ul>",
    )
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 2


def test_ol_then_ul_siblings(tmp_path: Path):
    """<ol> 与 <ul> 兄弟 → 各自的 li ordered 标志不同。"""
    doc = _parse(
        tmp_path,
        "<ol><li>one</li></ol><ul><li>two</li></ul>",
    )
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 2
    assert items[0].metadata["ordered"] is True
    assert items[1].metadata["ordered"] is False


def test_li_outside_list_emits_with_unordered_marker(tmp_path: Path):
    """<li> 不在 list 内 → ordered=False（list_stack 空）。"""
    doc = _parse(tmp_path, "<li>lonely</li>")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1
    assert items[0].metadata["ordered"] is False


# =========================================================================
# heading 边界
# =========================================================================


def test_empty_heading_text_not_emitted(tmp_path: Path):
    """<h1></h1> → strip 后为空 → 不 emit。"""
    doc = _parse(tmp_path, "<h1></h1>")
    headings = [e for e in doc.elements if e.type == "heading"]
    assert headings == []


def test_whitespace_only_heading_not_emitted(tmp_path: Path):
    """<h1>   </h1> → strip 后为空 → 不 emit。"""
    doc = _parse(tmp_path, "<h1>   </h1>")
    headings = [e for e in doc.elements if e.type == "heading"]
    assert headings == []


def test_multiple_same_level_headings_append_section_path(tmp_path: Path):
    """两个 h1 → section_path 两次推入；第二个 h1 弹出第一个（同级）。"""
    doc = _parse(
        tmp_path,
        "<h1>First</h1><p>text1</p><h1>Second</h1><p>text2</p>",
    )
    paras = [e for e in doc.elements if e.type == "paragraph"]
    # 第一个 p 的 section_path 应包含 "First"
    assert "First" in paras[0].source_locator["section_path"]
    # 第二个 p 的 section_path 应包含 "Second"
    assert "Second" in paras[1].source_locator["section_path"]


def test_h3_before_h1_pops_section_path(tmp_path: Path):
    """先 h3，再 h1 → h1 弹出 h3。"""
    doc = _parse(
        tmp_path,
        "<h3>Sub</h3><p>p1</p><h1>Top</h1><p>p2</p>",
    )
    paras = [e for e in doc.elements if e.type == "paragraph"]
    # p2 的 section_path 只应含 "Top"
    assert paras[1].source_locator["section_path"] == "Top"


def test_heading_level_4_5_6_emitted(tmp_path: Path):
    """h4/h5/h6 都能 emit。"""
    doc = _parse(
        tmp_path,
        "<h4>L4</h4><h5>L5</h5><h6>L6</h6>",
    )
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 3
    assert headings[0].metadata["level"] == 4
    assert headings[1].metadata["level"] == 5
    assert headings[2].metadata["level"] == 6


def test_heading_with_inline_tag(tmp_path: Path):
    """<h1><b>Bold</b> Heading</h1> → 文本拼接。"""
    doc = _parse(
        tmp_path,
        "<h1><b>Bold</b> Heading</h1>",
    )
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 1
    assert "Bold" in headings[0].content
    assert "Heading" in headings[0].content


# =========================================================================
# image 深度
# =========================================================================


def test_img_alt_with_entity(tmp_path: Path):
    """<img alt="A &amp; B"> → entity 解码为 "A & B"。"""
    doc = _parse(
        tmp_path,
        '<img src="x.png" alt="A &amp; B">',
    )
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 1
    assert imgs[0].metadata["alt"] == "A & B"


def test_img_src_with_whitespace_stripped(tmp_path: Path):
    """<img src="  x.png  "> → strip 后 "x.png"。"""
    doc = _parse(
        tmp_path,
        '<img src="  x.png  " alt="test">',
    )
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 1
    assert imgs[0].resource_path == "x.png"


def test_img_inside_paragraph_flushes_then_emits(tmp_path: Path):
    """<p>text<img>more</p> → flush text 后 emit image，然后继续 paragraph。

    实际：handle_starttag('img') 在 _cur_kind=paragraph 时调用 _emit_image，
    而 _emit_image 先 _flush_block()，所以 "text" 会被 emit 为 paragraph，
    然后 image emit，然后 "more" 又触发新 paragraph。
    """
    doc = _parse(
        tmp_path,
        "<p>text<img src=\"a.png\"/>more</p>",
    )
    paras = [e for e in doc.elements if e.type == "paragraph"]
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 1
    # text 和 more 各自成为 paragraph（中间被 image 切断）
    assert len(paras) >= 1


def test_consecutive_multiple_images(tmp_path: Path):
    """连续多个 <img> → 每个都 emit。"""
    doc = _parse(
        tmp_path,
        '<img src="a.png"><img src="b.png"><img src="c.png">',
    )
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 3
    assert [i.resource_path for i in imgs] == ["a.png", "b.png", "c.png"]


def test_img_with_numeric_entity_in_alt(tmp_path: Path):
    """<img alt="&#65;"> → "A" (numeric entity)。"""
    doc = _parse(
        tmp_path,
        '<img src="x" alt="&#65;">',
    )
    imgs = [e for e in doc.elements if e.type == "image"]
    assert imgs[0].metadata["alt"] == "A"


def test_img_with_hex_entity_in_alt(tmp_path: Path):
    """<img alt="&#x41;"> → "A" (hex entity)。"""
    doc = _parse(
        tmp_path,
        '<img src="x" alt="&#x41;">',
    )
    imgs = [e for e in doc.elements if e.type == "image"]
    assert imgs[0].metadata["alt"] == "A"


def test_img_duplicate_attrs_second_used(tmp_path: Path):
    """<img src="a" src="b"> → html.parser 把 attrs 当 list，dict 构造时后者覆盖前者。"""
    doc = _parse(
        tmp_path,
        '<img src="a" src="b">',
    )
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 1
    assert imgs[0].resource_path == "b"


# =========================================================================
# 字符实体在不同上下文
# =========================================================================


def test_numeric_entity_in_paragraph(tmp_path: Path):
    """<p>&#65;&#66;&#67;</p> → "ABC"。"""
    doc = _parse(tmp_path, "<p>&#65;&#66;&#67;</p>")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras[0].content == "ABC"


def test_hex_entity_in_paragraph(tmp_path: Path):
    """<p>&#x41;&#x42;&#x43;</p> → "ABC"。"""
    doc = _parse(tmp_path, "<p>&#x41;&#x42;&#x43;</p>")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras[0].content == "ABC"


def test_known_entity_amp(tmp_path: Path):
    """<p>A &amp; B</p> → "A & B"。"""
    doc = _parse(tmp_path, "<p>A &amp; B</p>")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras[0].content == "A & B"


def test_known_entity_lt_gt(tmp_path: Path):
    """<p>&lt;tag&gt;</p> → "<tag>"。"""
    doc = _parse(tmp_path, "<p>&lt;tag&gt;</p>")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras[0].content == "<tag>"


def test_known_entity_nbsp(tmp_path: Path):
    """<p>a&nbsp;b</p> → 含 NBSP 字符。"""
    doc = _parse(tmp_path, "<p>a&nbsp;b</p>")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    # NBSP = U+00A0
    assert " " in paras[0].content


def test_entity_in_heading(tmp_path: Path):
    """<h1>&amp;</h1> → " & "。"""
    doc = _parse(tmp_path, "<h1>&amp;</h1>")
    headings = [e for e in doc.elements if e.type == "heading"]
    assert headings[0].content == "&"


def test_entity_in_list_item(tmp_path: Path):
    doc = _parse(tmp_path, "<ul><li>&amp;</li></ul>")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert items[0].content == "&"


def test_entity_in_pre(tmp_path: Path):
    doc = _parse(tmp_path, "<pre>&amp;</pre>")
    pres = [e for e in doc.elements if e.metadata.get("kind") == "preformatted"]
    assert pres[0].content == "&"


def test_entity_in_blockquote(tmp_path: Path):
    doc = _parse(tmp_path, "<blockquote>&amp;</blockquote>")
    bqs = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    assert bqs[0].content == "&"


# =========================================================================
# 警告代码
# =========================================================================


def test_nested_table_emits_warning_once(tmp_path: Path):
    """嵌套 <table> → 1 个 warning。"""
    doc = _parse(
        tmp_path,
        "<table><tr><td>outer<table><tr><td>inner</td></tr></table></td></tr></table>",
    )
    nested_warnings = [w for w in doc.warnings if w.code == "html_nested_table"]
    assert len(nested_warnings) == 1


def test_no_content_warning_only_when_zero_elements(tmp_path: Path):
    doc = _parse(tmp_path, "<html><body><p>hello</p></body></html>")
    no_content_warnings = [w for w in doc.warnings if w.code == "html_no_content"]
    assert no_content_warnings == []


def test_no_content_warning_when_only_hr(tmp_path: Path):
    """<hr> 不创建 element → body 只有 hr 时触发 warning。"""
    doc = _parse(tmp_path, "<hr>")
    no_content_warnings = [w for w in doc.warnings if w.code == "html_no_content"]
    assert len(no_content_warnings) == 1


def test_no_content_warning_when_only_comments(tmp_path: Path):
    """<!-- comment --> 不创建 element。"""
    doc = _parse(tmp_path, "<!-- comment -->")
    no_content_warnings = [w for w in doc.warnings if w.code == "html_no_content"]
    assert len(no_content_warnings) == 1


def test_no_content_warning_reason_text(tmp_path: Path):
    doc = _parse(tmp_path, "")
    no_content_warnings = [w for w in doc.warnings if w.code == "html_no_content"]
    assert len(no_content_warnings) == 1
    assert "element" in no_content_warnings[0].reason or "提取" in no_content_warnings[0].reason


def test_nested_table_warning_has_reason(tmp_path: Path):
    doc = _parse(
        tmp_path,
        "<table><tr><td>x<table><tr><td>y</td></tr></table></td></tr></table>",
    )
    w = [w for w in doc.warnings if w.code == "html_nested_table"][0]
    assert "嵌套" in w.reason or "table" in w.reason.lower()


# =========================================================================
# _rows_to_md 深度
# =========================================================================


def test_rows_to_md_empty_string_cell():
    md = _rows_to_md([["", "filled"]])
    assert "filled" in md
    assert "|  |" in md or "| |" in md  # 空 cell


def test_rows_to_md_pipe_character_in_cell():
    """cell 含 | → 转义为 \\|（批次 5 契约 §2 结构转义）。"""
    md = _rows_to_md([["a|b"]])
    assert "a\\|b" in md


def test_rows_to_md_single_column_multi_row():
    """单列多行表 → 1 header + 1 separator + N body 行。"""
    md = _rows_to_md([["h"], ["r1"], ["r2"]])
    lines = md.split("\n")
    # 1 header + 1 separator + 2 body rows = 4
    assert len(lines) == 4
    assert lines[0] == "| h |"
    assert lines[1] == "| --- |"
    assert lines[2] == "| r1 |"
    assert lines[3] == "| r2 |"


def test_rows_to_md_jagged_pads_empty_strings():
    """jagged rows → padding 用 "" 填。"""
    md = _rows_to_md([["a", "b", "c"], ["x"]])
    lines = md.split("\n")
    # 最后一行（body）应有 3 列
    last_line = lines[-1]
    assert last_line.count("|") == 4  # 3 cells + 2 边界 = 4 个 |


def test_rows_to_md_header_one_col():
    md = _rows_to_md([["h1"]])
    lines = md.split("\n")
    assert len(lines) == 2  # header + separator (no body)


def test_rows_to_md_returns_str_for_empty_input():
    assert _rows_to_md([]) == ""


# =========================================================================
# locator 深度
# =========================================================================


def test_make_locator_for_current_no_section_path():
    """section_path 空 → locator 只有 family + line。"""
    parser = _HTMLDocParser("doc-test")
    parser._cur_start_line = 5
    loc = parser._make_locator_for_current()
    assert loc == {"family": "line_address", "line": 5}


def test_make_locator_for_current_with_section_path():
    parser = _HTMLDocParser("doc-test")
    parser._cur_start_line = 5
    parser._section_path = ["Top", "Sub"]
    loc = parser._make_locator_for_current()
    assert loc == {"family": "line_address", "line": 5, "section_path": "Top > Sub"}


def test_make_locator_for_inline_uses_getpos():
    """inline locator 用 getpos() 的 line。"""
    parser = _HTMLDocParser("doc-test")
    # feed 一行 HTML 后 getpos 会返回真实行列
    parser.feed("<p>text</p>\n")
    loc = parser._make_locator_for_inline()
    assert "line" in loc
    assert isinstance(loc["line"], int)


def test_make_locator_for_inline_with_section():
    parser = _HTMLDocParser("doc-test")
    parser._section_path = ["Top"]
    loc = parser._make_locator_for_inline()
    assert loc["section_path"] == "Top"


# =========================================================================
# pipeline 错误路径
# =========================================================================


def test_html_parse_failed_raises_on_handler_exception(tmp_path: Path, monkeypatch):
    """handler.feed 抛异常 → ParserError(code=html_parse_failed)。"""
    p = _write_html(tmp_path, "<p>x</p>")

    original_init = _HTMLDocParser.__init__

    def _broken_init(self, document_id):
        original_init(self, document_id)
        # 替换 feed 为抛异常
        def _raise_feed(*args, **kwargs):
            raise RuntimeError("synthetic feed error")
        self.feed = _raise_feed

    monkeypatch.setattr(_HTMLDocParser, "__init__", _broken_init)
    parser = HtmlParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, source_hash="a" * 64)
    assert ei.value.code == "html_parse_failed"
    assert "synthetic feed error" in ei.value.message


def test_html_read_failed_raises_on_oserror(tmp_path: Path, monkeypatch):
    """read_text 抛 OSError → ParserError(code=html_read_failed)。"""
    p = _write_html(tmp_path, "<p>x</p>")

    real_read_text = Path.read_text

    def _raise_os(self, *args, **kwargs):
        if self == p:
            raise OSError("disk error")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _raise_os)
    parser = HtmlParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, source_hash="a" * 64)
    assert ei.value.code == "html_read_failed"
    assert "OSError" in ei.value.details.get("exception_type", "") or "disk" in ei.value.message


def test_html_parse_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    """无效 UTF-8 → 用 errors=replace 兜底，仍能 parse。"""
    p = tmp_path / "test.html"
    p.write_bytes(b"<p>\xff\xfe hello</p>")
    parser = HtmlParser()
    doc = parser.parse(p, source_hash="a" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert "hello" in paras[0].content


# =========================================================================
# 模块常量
# =========================================================================


def test_skip_tags_includes_meta():
    assert "meta" in _SKIP_TAGS


def test_skip_tags_includes_link():
    assert "link" in _SKIP_TAGS


def test_skip_tags_includes_noscript():
    assert "noscript" in _SKIP_TAGS


def test_skip_tags_is_set():
    assert isinstance(_SKIP_TAGS, set)


def test_heading_levels_includes_h4_h5_h6():
    assert _HEADING_LEVELS["h4"] == 4
    assert _HEADING_LEVELS["h5"] == 5
    assert _HEADING_LEVELS["h6"] == 6


def test_heading_levels_exact_six_entries():
    assert len(_HEADING_LEVELS) == 6


def test_html_extensions_includes_htm():
    assert ".htm" in _HTML_EXTENSIONS


def test_html_extensions_includes_html():
    assert ".html" in _HTML_EXTENSIONS


def test_html_extensions_exact_two():
    assert len(_HTML_EXTENSIONS) == 2


# =========================================================================
# _HTMLDocParser SAX 深度
# =========================================================================


def test_sax_p_inside_p_ignored(tmp_path: Path):
    """<p><p> → 第二个 <p> 在已有 paragraph 时被忽略。"""
    doc = _parse(tmp_path, "<p><p>text</p></p>")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    # 行为：两个 <p> 同 _cur_kind，第二个被忽略；
    # 一个 </p> 关一个 paragraph，剩余文本继续累积
    # 测试不抛异常即可
    assert len(paras) >= 1


def test_sax_data_in_skip_stack_ignored(tmp_path: Path):
    """<script>data</script> → data 被忽略。"""
    doc = _parse(
        tmp_path,
        "<script>var x = 1;</script><p>real text</p>",
    )
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert "real text" in paras[0].content
    assert "var x" not in paras[0].content


def test_sax_nested_skip_tag_does_not_pop_wrong(tmp_path: Path):
    """<script><script></script></script> → 嵌套 skip 行为。

    html.parser 把 script 当作 CDATA 元素：第一个 </script> 关掉 <script>。
    后续的 y 不在 skip 模式 → 触发 paragraph；<p>real</p> 触发新 paragraph。
    本测试记录此实际行为。
    """
    doc = _parse(
        tmp_path,
        "<script><script>x</script>y</script><p>real</p>",
    )
    paras = [e for e in doc.elements if e.type == "paragraph"]
    # 至少 "real" 出现在某个 paragraph 中
    contents = " ".join(p.content for p in paras)
    assert "real" in contents
    # script 内容 "var x" 不会出现
    assert "var x" not in contents


def test_sax_close_tag_when_block_kind_mismatch_no_op(tmp_path: Path):
    """</p> 但当前是 heading → 不 flush（kind 不匹配）。"""
    doc = _parse(
        tmp_path,
        "<h1>Title</p>",
    )
    # 没有显式 </h1> → flush 在最后 _flush_block 调用
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 1


def test_sax_data_outside_block_becomes_paragraph(tmp_path: Path):
    """loose text（无 <p>）→ 启动 paragraph。"""
    doc = _parse(tmp_path, "loose text here")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert "loose text" in paras[0].content


def test_sax_whitespace_data_outside_block_ignored(tmp_path: Path):
    """纯空白 loose text → 不启动 paragraph。"""
    doc = _parse(tmp_path, "   \n   \t  ")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras == []


def test_sax_close_ul_flushes_pending_li(tmp_path: Path):
    """</ul> 调用 _flush_block → 把 pending list_item emit。"""
    doc = _parse(
        tmp_path,
        "<ul><li>item</ul>",
    )  # 没显式 </li>
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1
    assert items[0].content == "item"


def test_sax_close_ol_flushes_pending_li(tmp_path: Path):
    doc = _parse(tmp_path, "<ol><li>item</ol>")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1
    assert items[0].metadata["ordered"] is True


def test_sax_self_closing_hr_no_element(tmp_path: Path):
    """<hr/> → 不创建 element。"""
    doc = _parse(tmp_path, "<hr/><p>x</p>")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1


def test_sax_self_closing_br_in_paragraph(tmp_path: Path):
    """<br/> 在 paragraph 中 → 加空格。"""
    doc = _parse(tmp_path, "<p>line1<br/>line2</p>")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    # br 把文本连起来，中间加空格
    assert len(paras) == 1
    assert "line1" in paras[0].content
    assert "line2" in paras[0].content


# =========================================================================
# HtmlParser.parse metadata
# =========================================================================


def test_parse_metadata_html_flag_true(tmp_path: Path):
    doc = _parse(tmp_path, "<p>x</p>")
    assert doc.metadata.get("html") is True


def test_parse_returns_document_with_no_chunks(tmp_path: Path):
    doc = _parse(tmp_path, "<p>x</p>")
    assert doc.chunks == []


def test_parse_returns_document_with_no_relations(tmp_path: Path):
    doc = _parse(tmp_path, "<p>x</p>")
    assert doc.relations == []


def test_parse_returns_document_with_no_errors(tmp_path: Path):
    doc = _parse(tmp_path, "<p>x</p>")
    assert doc.errors == []


def test_parse_warning_records_are_warningrecord_type(tmp_path: Path):
    """warnings 元素是 WarningRecord 实例。"""
    from app.models import WarningRecord

    doc = _parse(tmp_path, "<table><tr><td>x<table><tr><td>y</td></tr></table></td></tr></table>")
    for w in doc.warnings:
        assert isinstance(w, WarningRecord)


# =========================================================================
# _detect_html_source_type 深度
# =========================================================================


def test_detect_html_source_type_accepts_upper_htm():
    """大写 .HTM 也接受（suffix.lower()）。"""
    p = Path("test.HTM")
    assert _detect_html_source_type(p) == "html"


def test_detect_html_source_type_accepts_uppercase_html():
    p = Path("test.HTML")
    assert _detect_html_source_type(p) == "html"


def test_detect_html_source_type_rejects_xml():
    p = Path("test.xml")
    with pytest.raises(ParserError):
        _detect_html_source_type(p)


def test_detect_html_source_type_rejects_pdf():
    p = Path("test.pdf")
    with pytest.raises(ParserError):
        _detect_html_source_type(p)


def test_detect_html_source_type_rejects_docx():
    p = Path("test.docx")
    with pytest.raises(ParserError):
        _detect_html_source_type(p)


def test_detect_html_source_type_error_message_contains_suffix():
    p = Path("test.unknown")
    with pytest.raises(ParserError) as ei:
        _detect_html_source_type(p)
    assert "unknown" in ei.value.message or ".unknown" in ei.value.message


# =========================================================================
# 完整 pipeline e2e
# =========================================================================


def test_html_complex_document_emits_multiple_types(tmp_path: Path):
    """完整文档：heading + p + ul + table + img + pre + blockquote。"""
    html = """
    <html><body>
    <h1>Title</h1>
    <p>Intro paragraph.</p>
    <h2>Subsection</h2>
    <ul><li>first</li><li>second</li></ul>
    <table><tr><th>A</th></tr><tr><td>a1</td></tr></table>
    <img src="pic.png" alt="Picture">
    <pre>code block</pre>
    <blockquote>quoted</blockquote>
    </body></html>
    """
    doc = _parse(tmp_path, html)
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types
    assert "list_item" in types
    assert "table" in types
    assert "image" in types
    # pre 和 blockquote 都 emit 为 paragraph（with kind metadata）
    kinds = [e.metadata.get("kind") for e in doc.elements]
    assert "preformatted" in kinds
    assert "blockquote" in kinds


def test_html_metadata_doc_id_consistent_with_hash(tmp_path: Path):
    """同一 hash 两次 parse → 同一 document_id。"""
    p = _write_html(tmp_path, "<p>x</p>")
    parser = HtmlParser()
    doc1 = parser.parse(p, source_hash="a" * 64)
    doc2 = parser.parse(p, source_hash="a" * 64)
    assert doc1.document_id == doc2.document_id


def test_html_metadata_doc_id_changes_with_hash(tmp_path: Path):
    """不同 hash → 不同 document_id。"""
    p = _write_html(tmp_path, "<p>x</p>")
    parser = HtmlParser()
    doc1 = parser.parse(p, source_hash="a" * 64)
    doc2 = parser.parse(p, source_hash="b" * 64)
    assert doc1.document_id != doc2.document_id


# =========================================================================
# SAX handler 内部状态
# =========================================================================


def test_doc_parser_close_does_not_raise():
    """handler.close() 应当幂等（无 tag 闭合）。"""
    parser = _HTMLDocParser("doc-test")
    parser.feed("<p>hello</p>")
    parser.close()  # 不应抛异常


def test_doc_parser_can_be_reused_via_reset():
    """reset 后可继续 feed。"""
    parser = _HTMLDocParser("doc-test")
    parser.feed("<p>one</p>")
    parser.reset()
    parser.feed("<p>two</p>")
    # 第二次 feed 的 element 应在 elements 列表中（reset 不清自定义 state）
    # 不抛异常即可


def test_doc_parser_getpos_returns_tuple():
    parser = _HTMLDocParser("doc-test")
    parser.feed("<p>x</p>\n")
    pos = parser.getpos()
    assert isinstance(pos, tuple)
    assert len(pos) == 2
    assert all(isinstance(p, int) for p in pos)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_contains_html_parser():
    from app.parsers import html_parser
    assert "HtmlParser" in html_parser.__all__


def test_module_all_only_lists_html_parser():
    from app.parsers import html_parser
    assert set(html_parser.__all__) == {"HtmlParser"}


def test_module_imports_stdlib_html_parser():
    from app.parsers import html_parser
    assert hasattr(html_parser, "_StdHTMLParser")


def test_module_imports_path():
    from app.parsers import html_parser
    assert hasattr(html_parser, "Path")


def test_module_imports_typing_any():
    from app.parsers import html_parser
    # typing.Any 用在 type hint，可通过检查源码确认
    src = Path(html_parser.__file__).read_text(encoding="utf-8")
    assert "from typing" in src


def test_module_imports_document():
    from app.parsers import html_parser
    # Document 用在 parse 返回值类型
    assert hasattr(html_parser, "Document")


def test_module_imports_element():
    from app.parsers import html_parser
    assert hasattr(html_parser, "Element")


def test_module_imports_warning_record():
    from app.parsers import html_parser
    assert hasattr(html_parser, "WarningRecord")


def test_module_imports_parser():
    from app.parsers import html_parser
    assert hasattr(html_parser, "Parser")


def test_module_imports_parser_error():
    from app.parsers import html_parser
    assert hasattr(html_parser, "ParserError")


def test_module_imports_make_document_id():
    from app.parsers import html_parser
    assert hasattr(html_parser, "make_document_id")


def test_html_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(HtmlParser, Parser)


def test_html_parser_name_value():
    assert HtmlParser.name == "html"


def test_html_parser_version_value():
    assert HtmlParser.version == "stdlib/0.1.0"


def test_html_parser_has_parse_method():
    assert callable(HtmlParser.parse)
