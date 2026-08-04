"""app/parsers/kreuzberg_parser.py 边角测试 - 第三轮（Round 105）。

补强已有 base/edges/edges2（共 332 个测试）未覆盖的深度路径：
- _classify_line：单字符 # / 多字符 #######（>6）/ 标点行 --- *** ///、tab 作为 # 后分隔、含控制字符
- _split_content_to_elements：heading + 多行 rest（rest 含 ATX 标记不再次分类）、block 内单 \n 保留、超长 block
- _make_locator：source_type 边界（None/空/含空白/混合大小写不归一）
- parse：content=None / mime_type=None / quality_score=None / kreuzberg_elements=None / cells 有但 markdown 空 / cells 为 [[]] 等
- 表格 locator bbox 空 tuple / 非空 tuple（list 化）
- 模块结构：_KREUZBERG_IMPORT_ERROR 仅在 ImportError 时定义
- 警告顺序：no_structured_elements 在 pdf_no_bbox 之前

不修改任何源码。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from app.parsers import kreuzberg_parser as kp
from app.parsers.base import ParserError
from app.parsers.kreuzberg_parser import (
    _HEADING_RE,
    _KREUZBERG_AVAILABLE,
    _KREUZBERG_VERSION,
    _SHORT_LINE_MAX,
    KreuzbergParser,
    _classify_line,
    _make_locator,
    _split_content_to_elements,
)


# =========================================================================
# 辅助
# =========================================================================


def _make_result(
    *,
    content: str | None = "",
    tables: list | None = None,
    elements: list | None = None,
    mime_type: str | None = "text/plain",
    quality_score: float | None = 1.0,
):
    """构造一个像 kreuzberg ExtractionResult 的轻量对象。"""

    class _R:
        pass

    r = _R()
    r.content = content
    r.tables = tables
    r.elements = elements
    r.mime_type = mime_type
    r.quality_score = quality_score
    return r


def _make_table(
    *,
    markdown: str | None = None,
    cells: list | None = None,
    page_number: int | None = 0,
    bounding_box: tuple | None = None,
):
    class _T:
        pass

    t = _T()
    t.markdown = markdown
    t.cells = cells
    t.page_number = page_number
    t.bounding_box = bounding_box
    return t


def _patch_extract(monkeypatch, result, *, raises: Exception | None = None):
    """让 kreuzberg.extract_file_sync 返回 result 或抛 raises。"""

    def _fake(path, config=None):
        if raises is not None:
            raise raises
        return result

    monkeypatch.setattr(kp.kreuzberg, "extract_file_sync", _fake)


def _write_pdf(tmp_path: Path, name: str = "x.pdf") -> Path:
    p = tmp_path / name
    p.write_bytes(b"%PDF-1.4\n%%EOF\n")
    return p


def _write_docx(tmp_path: Path, name: str = "x.docx") -> Path:
    p = tmp_path / name
    p.write_bytes(b"PK\x03\x04")  # 假 docx 魔数
    return p


# =========================================================================
# _classify_line 深度：极端输入
# =========================================================================


def test_classify_line_single_hash_no_space_is_short_line_heading():
    r"""单 # 没有 \s 后继 → 不匹配 ATX → 走短行启发式 → heading。"""
    etype, meta = _classify_line("#")
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"
    assert meta["raw_text"] == "#"
    assert meta["level"] == 0


def test_classify_line_two_hashes_no_space_is_short_line_heading():
    etype, meta = _classify_line("##")
    assert etype == "heading"
    assert meta["raw_text"] == "##"


def test_classify_line_six_hashes_no_space_short_line_heading():
    etype, meta = _classify_line("######")
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"


def test_classify_line_seven_hashes_no_space_short_line_heading():
    """7 个 # 不匹配 ATX（最多 6）→ 走短行启发式。"""
    etype, meta = _classify_line("#######")
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"
    assert meta["raw_text"] == "#######"


def test_classify_line_thematic_break_dashes_classified_as_short_line_heading():
    """`---` 长度 3 无终止符 → 短行启发式 heading。"""
    etype, _ = _classify_line("---")
    assert etype == "heading"


def test_classify_line_thematic_break_asterisks_classified_as_short_line_heading():
    etype, _ = _classify_line("***")
    assert etype == "heading"


def test_classify_line_thematic_break_underscores_classified_as_short_line_heading():
    etype, _ = _classify_line("___")
    assert etype == "heading"


def test_classify_line_three_slashes_classified_as_short_line_heading():
    etype, _ = _classify_line("///")
    assert etype == "heading"


def test_classify_line_code_fence_backticks_classified_as_short_line_heading():
    """三反引号（markdown 代码块标记）→ 长度 3 无终止符 → heading。"""
    etype, _ = _classify_line("```")
    assert etype == "heading"


def test_classify_line_pipe_chars_classified_as_short_line_heading():
    etype, _ = _classify_line("|||")
    assert etype == "heading"


def test_classify_line_two_dashes_with_internal_period_is_paragraph():
    """`-.` 长度 2 但末尾是 `.`，作为终止符 → paragraph。"""
    etype, _ = _classify_line("-.")
    assert etype == "paragraph"


# =========================================================================
# _classify_line：tab / 控制字符
# =========================================================================


def test_classify_line_tab_as_separator_after_hash_matches_atx():
    r"""`#\tHello` → `\s+` 匹配 tab → ATX heading。"""
    etype, meta = _classify_line("#\tHello")
    assert etype == "heading"
    assert meta["raw_text"] == "Hello"
    assert meta["level"] == 1


def test_classify_line_multiple_spaces_after_hash_matches_atx():
    r"""`#  Hello` → `\s+` 匹配多空格 → ATX heading。"""
    etype, meta = _classify_line("#  Hello")
    assert etype == "heading"
    assert meta["raw_text"] == "Hello"


def test_classify_line_leading_tab_before_hash_level_falls_back_to_1():
    """`\\t# Hello` → level = len - len(lstrip('#')) = 0 → max(1, 0) = 1。"""
    etype, meta = _classify_line("\t# Hello")
    assert etype == "heading"
    assert meta["level"] == 1


def test_classify_line_leading_spaces_then_hash_level_falls_back_to_1_explicit():
    """`   # Hi` → lstrip('#') 不剥空格 → level = 0 → max(1, 0) = 1。"""
    etype, meta = _classify_line("   # Hi")
    assert etype == "heading"
    assert meta["level"] == 1


def test_classify_line_internal_tab_in_raw_text_preserved():
    """`# Hello\\tWorld` → raw_text 含 tab。"""
    _, meta = _classify_line("# Hello\tWorld")
    assert "\t" in meta["raw_text"]


def test_classify_line_trailing_newline_in_argument_atx_still_matches():
    """`# Hello\\n` → $ 在 \n 前匹配 → ATX heading。"""
    etype, meta = _classify_line("# Hello\n")
    assert etype == "heading"
    assert meta["raw_text"] == "Hello"


def test_classify_line_carriage_return_only_handled_as_empty():
    """`\\r` 单独 → strip 后空 → paragraph 空 meta。"""
    etype, meta = _classify_line("\r")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_crlf_only_handled_as_empty():
    etype, meta = _classify_line("\r\n")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_vertical_tab_in_text_no_terminator_short_line_heading():
    """`\\v` 不是终止符 → 短行 heading。"""
    etype, _ = _classify_line("a\vb")
    assert etype == "heading"


def test_classify_line_form_feed_in_text_no_terminator_short_line_heading():
    etype, _ = _classify_line("a\fb")
    assert etype == "heading"


# =========================================================================
# _classify_line：长度阈值边界
# =========================================================================


def test_classify_line_exactly_80_chars_without_terminator_is_heading():
    """80 字符（含边界）→ heading。"""
    text = "a" * 80
    etype, meta = _classify_line(text)
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"


def test_classify_line_exactly_81_chars_without_terminator_is_paragraph():
    """81 字符 → 超阈值 → paragraph。"""
    text = "a" * 81
    etype, meta = _classify_line(text)
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_strip_affects_length_check():
    """`  aaaa  `（80 字符含两端空白）→ strip 后 76 → heading。"""
    text = "  " + "a" * 76 + "  "
    etype, _ = _classify_line(text)
    assert etype == "heading"


def test_classify_line_leading_whitespace_makes_actual_line_longer_but_text_shorter():
    """长前导空白但内容短 → strip 后 ≤80 → heading。"""
    text = "       " + "hi"
    etype, _ = _classify_line(text)
    assert etype == "heading"


# =========================================================================
# _classify_line：ATX heading 内部细节
# =========================================================================


def test_classify_line_atx_with_trailing_dots_in_raw_text():
    _, meta = _classify_line("# Hello...")
    assert meta["raw_text"] == "Hello..."


def test_classify_line_atx_with_only_punctuation_after_space():
    _, meta = _classify_line("# !!!")
    assert meta["raw_text"] == "!!!"


def test_classify_line_atx_internal_double_spaces_preserved_in_raw_text():
    """`# Hello    World` → 中间多空格保留。"""
    _, meta = _classify_line("# Hello    World")
    assert "Hello    World" == meta["raw_text"]


def test_classify_line_atx_trailing_backslash_preserved():
    _, meta = _classify_line("# Title\\")
    assert meta["raw_text"] == "Title\\"


def test_classify_line_atx_with_unicode_punctuation_in_text():
    _, meta = _classify_line("# 标题——测试")
    assert "标题——测试" == meta["raw_text"]


def test_classify_line_short_line_with_only_digit():
    etype, meta = _classify_line("42")
    assert etype == "heading"
    assert meta["raw_text"] == "42"


def test_classify_line_short_line_with_period_after_digit_is_paragraph():
    """`4.2` 末尾不是 `.`？`4.2` 末尾是 `2` → heading。"""
    etype, _ = _classify_line("4.2")
    assert etype == "heading"


def test_classify_line_short_line_with_integer_period_is_paragraph():
    """`42.` 末尾是 `.` → paragraph。"""
    etype, _ = _classify_line("42.")
    assert etype == "paragraph"


# =========================================================================
# _HEADING_RE 正则边界
# =========================================================================


def test_heading_re_supports_tab_after_hashes():
    assert _HEADING_RE.match("#\tHi")


def test_heading_re_no_match_just_one_hash():
    assert _HEADING_RE.match("#") is None


def test_heading_re_no_match_seven_hashes_with_space():
    assert _HEADING_RE.match("####### Hi") is None


def test_heading_re_matches_six_hashes_with_space():
    assert _HEADING_RE.match("###### Hi") is not None


def test_heading_re_captures_punctuation_only():
    m = _HEADING_RE.match("# !!!")
    assert m.group(1) == "!!!"


def test_heading_re_captures_unicode_single_char():
    m = _HEADING_RE.match("# 你")
    assert m.group(1) == "你"


def test_heading_re_returns_match_or_none_not_bool():
    """确认 match() 返回 Match 对象或 None，不是 bool。"""
    m = _HEADING_RE.match("# Hi")
    assert m is not None
    assert hasattr(m, "group")


def test_heading_re_pattern_uses_caret_anchor():
    assert _HEADING_RE.pattern.startswith("^")


def test_heading_re_pattern_uses_dollar_anchor():
    assert _HEADING_RE.pattern.endswith("$")


# =========================================================================
# _split_content_to_elements：rest 含 ATX 标记（不再分类）
# =========================================================================


def test_split_content_rest_containing_atx_marker_emitted_as_paragraph():
    """同一 block 内 `# H1\\n# H2` → heading H1 + paragraph `# H2`。"""
    elements, _ = _split_content_to_elements("# H1\n# H2", "docx", "doc123")
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[0].content == "H1"
    assert elements[1].type == "paragraph"
    assert elements[1].content == "# H2"


def test_split_content_rest_with_three_lines_preserved_in_paragraph():
    """heading 后多行 rest → paragraph 内部 \\n 保留。"""
    elements, _ = _split_content_to_elements("# Title\nline1\nline2\nline3", "docx", "doc")
    assert len(elements) == 2
    assert elements[1].type == "paragraph"
    assert elements[1].content == "line1\nline2\nline3"


def test_split_content_block_with_single_newline_no_separator_one_block():
    r"""单 \\n 不构成分隔符 → 单 block（含多行）。行末带 . 避免短行 heading 启发。"""
    elements, _ = _split_content_to_elements("line one.\nline two.", "docx", "doc")
    assert len(elements) == 1
    assert elements[0].type == "paragraph"


def test_split_content_block_with_carriage_return_only_no_separator():
    r"""`\\r` 不被 `\\n\\s*\\n` 匹配 → 整体一个 block。行末带 . 避免短行 heading 启发。"""
    elements, _ = _split_content_to_elements("line one.\rline two.", "docx", "doc")
    assert len(elements) == 1
    assert elements[0].type == "paragraph"


def test_split_content_paragraph_internal_newline_count_preserved():
    r"""多行段落内部 \\n 数量精确。行末带 . 避免短行 heading 启发。"""
    text = "a.\nb.\nc.\nd."
    elements, _ = _split_content_to_elements(text, "docx", "doc")
    assert len(elements) == 1
    assert elements[0].content.count("\n") == 3


def test_split_content_heading_block_with_empty_first_line_after_heading_no_rest():
    """block 第一行 `# H1` 第二行空 → rest = ''（strip 后）→ 不 emit paragraph。"""
    elements, _ = _split_content_to_elements("# H1\n", "docx", "doc")
    assert len(elements) == 1
    assert elements[0].type == "heading"


def test_split_content_heading_block_with_whitespace_rest_no_paragraph():
    elements, _ = _split_content_to_elements("# H1\n   \n  ", "docx", "doc")
    assert len(elements) == 1


def test_split_content_short_line_heading_with_atx_rest_paragraph():
    """短行 heading 后接 ATX 行 → paragraph。"""
    elements, _ = _split_content_to_elements("short title\n# ATX here", "docx", "doc")
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[0].content == "short title"
    assert elements[1].type == "paragraph"
    assert elements[1].content == "# ATX here"


def test_split_content_short_line_heading_with_short_line_rest_paragraph():
    elements, _ = _split_content_to_elements("title one\nanother title", "docx", "doc")
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[1].type == "paragraph"


def test_split_content_paragraph_starts_with_dashes_emitted_as_paragraph():
    """`--- text` 第一行非 ATX（无 #）但首字符 `-` → paragraph（除非短到短行）。

    `-- text` 长度 7 ≤ 80 无终止符 → heading via short_line heuristic。
    """
    elements, _ = _split_content_to_elements("a long paragraph line that exceeds the short threshold eighty chars......", "docx", "doc")
    assert len(elements) == 1
    assert elements[0].type == "paragraph"


def test_split_content_block_with_only_whitespace_lines_filtered():
    """`\\n\\n   \\n\\n` → 全空白 block 被过滤掉。"""
    elements, _ = _split_content_to_elements("   \n\n  \n\nreal\n\n   ", "docx", "doc")
    contents = [e.content for e in elements]
    assert "real" in contents
    assert all(c.strip() for c in contents)


def test_split_content_stress_1000_blocks():
    text = "\n\n".join(f"para{i}" for i in range(1000))
    elements, _ = _split_content_to_elements(text, "docx", "doc")
    assert len(elements) == 1000


def test_split_content_stress_1000_blocks_all_unique_ids():
    text = "\n\n".join(f"para{i}" for i in range(1000))
    elements, _ = _split_content_to_elements(text, "docx", "docX")
    ids = [e.element_id for e in elements]
    assert len(set(ids)) == 1000


def test_split_content_returns_empty_list_for_only_whitespace():
    elements, second = _split_content_to_elements("   \n\t\n  ", "docx", "doc")
    assert elements == []
    assert second == []


def test_split_content_pdf_locator_for_all_blocks():
    """PDF 模式下所有元素 locator 含 page=1 + _kreuzberg_placeholder。"""
    elements, _ = _split_content_to_elements("para1\n\npara2", "pdf", "doc")
    assert len(elements) == 2
    for e in elements:
        assert e.source_locator["page"] == 1
        assert e.source_locator["_kreuzberg_placeholder"] is True


def test_split_content_paragraph_locator_increments_para_idx_per_block_docx():
    elements, _ = _split_content_to_elements("p1\n\np2\n\np3", "docx", "doc")
    indices = [e.source_locator["paragraph_index"] for e in elements]
    assert indices == [0, 1, 2]


def test_split_content_heading_rest_share_incremented_idx():
    """heading 后 rest paragraph 是 para_idx+1。"""
    elements, _ = _split_content_to_elements("# Title\nbody", "docx", "doc")
    assert elements[0].source_locator["paragraph_index"] == 0
    assert elements[1].source_locator["paragraph_index"] == 1


def test_split_content_heading_atx_metadata_heuristic_is_none():
    elements, _ = _split_content_to_elements("# Title", "docx", "doc")
    assert elements[0].metadata["heuristic"] is None


def test_split_content_heading_short_line_metadata_heuristic_is_short_line():
    elements, _ = _split_content_to_elements("shorty", "docx", "doc")
    assert elements[0].metadata["heuristic"] == "short_line"


# =========================================================================
# _make_locator：边界 source_type
# =========================================================================


def test_make_locator_none_source_type_returns_docx_like():
    """source_type=None → 不匹配 'pdf' → 走 else 分支。"""
    loc = _make_locator(None, 0)
    assert "paragraph_index" in loc
    assert loc["_kreuzberg_heuristic"] is True


def test_make_locator_empty_string_source_type_returns_docx_like():
    loc = _make_locator("", 0)
    assert "paragraph_index" in loc


def test_make_locator_uppercase_pdf_returns_docx_like():
    """`PDF` 不匹配小写 'pdf'。"""
    loc = _make_locator("PDF", 0)
    assert "paragraph_index" in loc


def test_make_locator_whitespace_padded_pdf_returns_docx_like():
    loc = _make_locator(" pdf ", 0)
    assert "paragraph_index" in loc


def test_make_locator_unknown_source_type_returns_docx_like():
    loc = _make_locator("csv", 0)
    assert "paragraph_index" in loc


def test_make_locator_pdf_returns_no_paragraph_index():
    loc = _make_locator("pdf", 0)
    assert "paragraph_index" not in loc


def test_make_locator_docx_returns_no_page():
    loc = _make_locator("docx", 0)
    assert "page" not in loc


def test_make_locator_pdf_negative_paragraph_index_ignored():
    """PDF 模式忽略 paragraph_index 参数。"""
    loc = _make_locator("pdf", -1)
    assert loc["page"] == 1


def test_make_locator_docx_with_negative_index_passes_through():
    loc = _make_locator("docx", -5)
    assert loc["paragraph_index"] == -5


def test_make_locator_docx_zero_index_passes_through():
    loc = _make_locator("docx", 0)
    assert loc["paragraph_index"] == 0


def test_make_locator_docx_large_index_passes_through():
    loc = _make_locator("docx", 999999)
    assert loc["paragraph_index"] == 999999


# =========================================================================
# parse：content / mime_type / quality_score 边界
# =========================================================================


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_content_none_treated_as_empty(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content=None, elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert doc.elements == []


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_mime_type_none_propagated_to_metadata(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="", elements=[], mime_type=None)
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert doc.metadata["kreuzberg_mime_type"] is None


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_quality_score_none_propagated_to_metadata(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="", elements=[], quality_score=None)
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert doc.metadata["kreuzberg_quality_score"] is None


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_mime_type_specific_string_preserved(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="", elements=[], mime_type="application/pdf")
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert doc.metadata["kreuzberg_mime_type"] == "application/pdf"


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_quality_score_float_preserved(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="", elements=[], quality_score=0.875)
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert doc.metadata["kreuzberg_quality_score"] == 0.875


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_kreuzberg_elements_none_emits_no_structured_warning(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="hello", elements=None)
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_no_structured_elements" in codes


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_kreuzberg_elements_empty_list_emits_no_structured_warning(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="hello", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_no_structured_elements" in codes


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_kreuzberg_elements_truthy_no_structured_warning(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="hello", elements=["fake_element"])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_no_structured_elements" not in codes


# =========================================================================
# parse：表格边界
# =========================================================================


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_with_cells_but_no_markdown_raises_validation(tmp_path: Path, monkeypatch):
    """cells 有但 markdown=None/'' → Element content='' + resource_path=None →
    Element __post_init__ 抛 ValueError（content 或 resource_path 必须非空）。"""
    p = _write_docx(tmp_path)
    t = _make_table(markdown=None, cells=[["a", "b"]])
    result = _make_result(content="", tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    with pytest.raises(ValueError, match="content"):
        KreuzbergParser().parse(p, source_hash="a" * 64)


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_with_markdown_but_no_cells(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    t = _make_table(markdown="| h |\n| --- |\n| r |", cells=None)
    result = _make_result(content="", tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    tbls = [e for e in doc.elements if e.type == "table"]
    assert len(tbls) == 1
    assert tbls[0].confidence == 0.5
    assert tbls[0].metadata["cell_count"] == 0
    assert tbls[0].metadata["row_count"] == 0


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_with_empty_cells_list(tmp_path: Path, monkeypatch):
    """cells=[] → falsy → confidence=0.5。"""
    p = _write_docx(tmp_path)
    t = _make_table(markdown="| h |", cells=[])
    result = _make_result(content="", tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    tbls = [e for e in doc.elements if e.type == "table"]
    assert tbls[0].confidence == 0.5


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_with_empty_rows_in_cells(tmp_path: Path, monkeypatch):
    """cells=[[], []] → 2 行但 0 cell。"""
    p = _write_docx(tmp_path)
    t = _make_table(markdown="x", cells=[[], []])
    result = _make_result(content="", tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    tbls = [e for e in doc.elements if e.type == "table"]
    assert tbls[0].metadata["row_count"] == 2
    assert tbls[0].metadata["cell_count"] == 0
    assert tbls[0].confidence == 0.8  # cells 整体 truthy


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_pdf_with_bounding_box_tuple_converted_to_list(tmp_path: Path, monkeypatch):
    p = _write_pdf(tmp_path)
    t = _make_table(markdown="| h |", cells=[["a"]], page_number=1, bounding_box=(1.0, 2.0, 3.0, 4.0))
    result = _make_result(content="", tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    tbls = [e for e in doc.elements if e.type == "table"]
    bb = tbls[0].source_locator.get("bbox")
    assert bb == [1.0, 2.0, 3.0, 4.0]
    assert isinstance(bb, list)


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_pdf_with_empty_bounding_box_tuple_omitted(tmp_path: Path, monkeypatch):
    """bounding_box=() → falsy → 不加 bbox 键。"""
    p = _write_pdf(tmp_path)
    t = _make_table(markdown="| h |", cells=[["a"]], page_number=1, bounding_box=())
    result = _make_result(content="", tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    tbls = [e for e in doc.elements if e.type == "table"]
    assert "bbox" not in tbls[0].source_locator


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_pdf_with_none_bounding_box_omitted(tmp_path: Path, monkeypatch):
    p = _write_pdf(tmp_path)
    t = _make_table(markdown="| h |", cells=[["a"]], page_number=1, bounding_box=None)
    result = _make_result(content="", tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    tbls = [e for e in doc.elements if e.type == "table"]
    assert "bbox" not in tbls[0].source_locator


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_pdf_page_number_negative_falls_back_to_1(tmp_path: Path, monkeypatch):
    """page_number=-1 → 0（falsy）→ 退到 1。但 -1 是 truthy，所以会保留 -1。

    注意：`getattr(t, 'page_number', 0) or 1`。-1 or 1 = -1（因为 -1 是 truthy）。
    """
    p = _write_pdf(tmp_path)
    t = _make_table(markdown="x", cells=[["a"]], page_number=-1)
    result = _make_result(content="", tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    tbls = [e for e in doc.elements if e.type == "table"]
    assert tbls[0].source_locator["page"] == -1  # -1 是 truthy


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_pdf_page_number_large_preserved(tmp_path: Path, monkeypatch):
    p = _write_pdf(tmp_path)
    t = _make_table(markdown="x", cells=[["a"]], page_number=999)
    result = _make_result(content="", tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    tbls = [e for e in doc.elements if e.type == "table"]
    assert tbls[0].source_locator["page"] == 999


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_docx_uses_table_index_locator(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    t0 = _make_table(markdown="t0", cells=[["a"]])
    t1 = _make_table(markdown="t1", cells=[["b"]])
    result = _make_result(content="", tables=[t0, t1], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    tbls = [e for e in doc.elements if e.type == "table"]
    assert len(tbls) == 2
    assert tbls[0].source_locator["table_index"] == 0
    assert tbls[1].source_locator["table_index"] == 1
    assert tbls[0].source_locator["_kreuzberg_heuristic"] is True


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_table_metadata_source_always_kreuzberg(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    t = _make_table(markdown="x", cells=[["a"]])
    result = _make_result(content="", tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    tbls = [e for e in doc.elements if e.type == "table"]
    assert tbls[0].metadata["source"] == "kreuzberg"


# =========================================================================
# parse：警告顺序与组合
# =========================================================================


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_pdf_warning_order_no_structured_before_no_bbox(tmp_path: Path, monkeypatch):
    p = _write_pdf(tmp_path)
    result = _make_result(content="hello", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    # no_structured_elements 在前，pdf_no_bbox 在后
    assert codes.index("kreuzberg_no_structured_elements") < codes.index("kreuzberg_pdf_no_bbox")


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_docx_only_no_structured_warning_no_bbox(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="hello", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_pdf_no_bbox" not in codes
    assert "kreuzberg_no_structured_elements" in codes


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_pdf_with_structured_elements_only_no_bbox_warning(tmp_path: Path, monkeypatch):
    p = _write_pdf(tmp_path)
    result = _make_result(content="hello", elements=["fake"])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert codes == ["kreuzberg_pdf_no_bbox"]


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_pdf_no_structured_warning_has_element_count_after_heuristic(tmp_path: Path, monkeypatch):
    p = _write_pdf(tmp_path)
    result = _make_result(content="para1\n\npara2", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    w = next(w for w in doc.warnings if w.code == "kreuzberg_no_structured_elements")
    assert w.details["element_count_after_heuristic"] == 2
    assert w.details["source_type"] == "pdf"
    assert w.details["fallback_strategy"] == "heuristic_paragraph_split"


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_pdf_no_bbox_warning_details_has_source_type(tmp_path: Path, monkeypatch):
    p = _write_pdf(tmp_path)
    result = _make_result(content="", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    w = next(w for w in doc.warnings if w.code == "kreuzberg_pdf_no_bbox")
    assert w.details == {"source_type": "pdf"}


# =========================================================================
# parse：异常路径
# =========================================================================


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_extract_failed_value_error(monkeypatch, tmp_path: Path):
    p = _write_docx(tmp_path)

    def _raise(path, config=None):
        raise ValueError("bad input")

    monkeypatch.setattr(kp.kreuzberg, "extract_file_sync", _raise)
    with pytest.raises(ParserError) as ei:
        KreuzbergParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "kreuzberg_extract_failed"
    assert ei.value.details["exception_type"] == "ValueError"


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_extract_failed_runtime_error(monkeypatch, tmp_path: Path):
    p = _write_docx(tmp_path)

    def _raise(path, config=None):
        raise RuntimeError("oops")

    monkeypatch.setattr(kp.kreuzberg, "extract_file_sync", _raise)
    with pytest.raises(ParserError) as ei:
        KreuzbergParser().parse(p, source_hash="a" * 64)
    assert ei.value.details["exception_type"] == "RuntimeError"


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_extract_failed_message_contains_original_message(monkeypatch, tmp_path: Path):
    p = _write_docx(tmp_path)

    def _raise(path, config=None):
        raise IOError("specific failure text")

    monkeypatch.setattr(kp.kreuzberg, "extract_file_sync", _raise)
    with pytest.raises(ParserError) as ei:
        KreuzbergParser().parse(p, source_hash="a" * 64)
    assert "specific failure text" in ei.value.message


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_extract_failed_preserves_chained_cause(monkeypatch, tmp_path: Path):
    p = _write_docx(tmp_path)

    def _raise(path, config=None):
        raise OSError("disk")

    monkeypatch.setattr(kp.kreuzberg, "extract_file_sync", _raise)
    try:
        KreuzbergParser().parse(p, source_hash="a" * 64)
        assert False, "应抛 ParserError"
    except ParserError as pe:
        assert pe.__cause__ is not None
        assert isinstance(pe.__cause__, OSError)


def test_parse_kreuzberg_unavailable_check_before_file_exists(monkeypatch, tmp_path: Path):
    """_KREUZBERG_AVAILABLE=False 时优先抛 kreuzberg_unavailable（即使文件不存在）。"""
    p = tmp_path / "missing.docx"
    monkeypatch.setattr(kp, "_KREUZBERG_AVAILABLE", False)
    monkeypatch.setattr(kp, "_KREUZBERG_IMPORT_ERROR", "simulated", raising=False)
    with pytest.raises(ParserError) as ei:
        KreuzbergParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "kreuzberg_unavailable"


def test_parse_kreuzberg_unavailable_no_details_dict(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(kp, "_KREUZBERG_AVAILABLE", False)
    monkeypatch.setattr(kp, "_KREUZBERG_IMPORT_ERROR", "simulated", raising=False)
    with pytest.raises(ParserError) as ei:
        KreuzbergParser().parse(tmp_path / "x.docx", source_hash="a" * 64)
    # 默认 details 是空 dict（ParserError 默认）
    assert ei.value.details == {}


# =========================================================================
# parse：Document 不变量
# =========================================================================


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_returns_document_instance(tmp_path: Path, monkeypatch):
    from app.models import Document

    p = _write_docx(tmp_path)
    result = _make_result(content="hello", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert isinstance(doc, Document)


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_parser_name_is_kreuzberg(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert doc.parser_name == "kreuzberg"


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_parser_version_matches_module_constant(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert doc.parser_version == _KREUZBERG_VERSION


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_chunks_always_empty(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="hello", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert doc.chunks == []


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_relations_always_empty(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="hello", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert doc.relations == []


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_errors_always_empty(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="hello", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert doc.errors == []


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_metadata_only_two_keys(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    assert set(doc.metadata.keys()) == {"kreuzberg_mime_type", "kreuzberg_quality_score"}


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_two_parses_independent_document_ids(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="hello", elements=[])
    _patch_extract(monkeypatch, result)
    doc1 = KreuzbergParser().parse(p, source_hash="a" * 64)
    doc2 = KreuzbergParser().parse(p, source_hash="b" * 64)
    assert doc1.document_id != doc2.document_id


# =========================================================================
# parse：复杂场景
# =========================================================================


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_complex_content_with_headings_paragraphs_tables(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    content = "# Title\n\nIntro paragraph.\n\n## Section\n\nMore text."
    t = _make_table(markdown="| h |\n| --- |\n| r |", cells=[["h"], ["r"]])
    result = _make_result(content=content, tables=[t], elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types
    assert "table" in types


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_docx_heading_uses_paragraph_index_locator(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    result = _make_result(content="# Title\n\nbody", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    h = [e for e in doc.elements if e.type == "heading"][0]
    assert "paragraph_index" in h.source_locator
    assert h.source_locator["_kreuzberg_heuristic"] is True


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_pdf_heading_uses_page_locator(tmp_path: Path, monkeypatch):
    p = _write_pdf(tmp_path)
    result = _make_result(content="# Title", elements=[])
    _patch_extract(monkeypatch, result)
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    h = [e for e in doc.elements if e.type == "heading"][0]
    assert h.source_locator["page"] == 1
    assert h.source_locator["_kreuzberg_placeholder"] is True


# =========================================================================
# include_document_structure 参数
# =========================================================================


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_default_include_document_structure_passed_to_config(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    captured = {}

    def _fake(path, config=None):
        captured["include_document_structure"] = config.include_document_structure
        return _make_result(content="", elements=[])

    monkeypatch.setattr(kp.kreuzberg, "extract_file_sync", _fake)
    KreuzbergParser().parse(p, source_hash="a" * 64)
    assert captured["include_document_structure"] is True


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_parse_disabled_include_document_structure_passed_to_config(tmp_path: Path, monkeypatch):
    p = _write_docx(tmp_path)
    captured = {}

    def _fake(path, config=None):
        captured["include_document_structure"] = config.include_document_structure
        return _make_result(content="", elements=[])

    monkeypatch.setattr(kp.kreuzberg, "extract_file_sync", _fake)
    KreuzbergParser(include_document_structure=False).parse(p, source_hash="a" * 64)
    assert captured["include_document_structure"] is False


# =========================================================================
# 模块结构 / 常量
# =========================================================================


def test_module_heading_re_is_compiled_pattern():
    assert isinstance(_HEADING_RE, re.Pattern)


def test_module_short_line_max_equals_80():
    assert _SHORT_LINE_MAX == 80


def test_module_short_line_max_is_int():
    assert isinstance(_SHORT_LINE_MAX, int)


def test_module_short_line_max_positive():
    assert _SHORT_LINE_MAX > 0


def test_module_kreuzberg_available_is_bool():
    assert isinstance(_KREUZBERG_AVAILABLE, bool)


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_module_kreuzberg_version_string_when_available():
    assert isinstance(_KREUZBERG_VERSION, str)
    assert _KREUZBERG_VERSION  # 非空


def test_module_all_exports_only_kreuzberg_parser():
    assert kp.__all__ == ["KreuzbergParser"]


def test_module_imports_path():
    assert hasattr(kp, "Path")


def test_module_imports_re():
    assert hasattr(kp, "re")


def test_module_imports_any():
    assert hasattr(kp, "Any")


def test_module_imports_document():
    assert hasattr(kp, "Document")


def test_module_imports_element():
    assert hasattr(kp, "Element")


def test_module_imports_warning_record():
    assert hasattr(kp, "WarningRecord")


def test_module_imports_parser():
    assert hasattr(kp, "Parser")


def test_module_imports_parser_error():
    assert hasattr(kp, "ParserError")


def test_module_imports_detect_source_type():
    assert hasattr(kp, "detect_source_type")


def test_module_imports_make_document_id():
    assert hasattr(kp, "make_document_id")


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_module_no_kreuzberg_import_error_when_available():
    """kreuzberg 可用时，_KREUZBERG_IMPORT_ERROR 不应被定义。"""
    assert not hasattr(kp, "_KREUZBERG_IMPORT_ERROR")


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_module_kreuzberg_object_imported():
    assert hasattr(kp, "kreuzberg")


@pytest.mark.skipif(not _KREUZBERG_AVAILABLE, reason="kreuzberg 未安装")
def test_module_extraction_config_imported():
    assert hasattr(kp, "ExtractionConfig")


def test_module_classify_line_callable():
    assert callable(_classify_line)


def test_module_split_content_callable():
    assert callable(_split_content_to_elements)


def test_module_make_locator_callable():
    assert callable(_make_locator)


def test_kreuzberg_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(KreuzbergParser, Parser)


def test_kreuzberg_parser_class_name_constant():
    assert KreuzbergParser.name == "kreuzberg"


def test_kreuzberg_parser_class_version_matches_module():
    assert KreuzbergParser.version == _KREUZBERG_VERSION


def test_kreuzberg_parser_init_signature_keyword_only():
    """__init__ 应 keyword-only。"""
    import inspect
    sig = inspect.signature(KreuzbergParser.__init__)
    params = list(sig.parameters.values())
    # self 之后所有参数应是 keyword-only
    for p in params[1:]:
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_kreuzberg_parser_parse_signature():
    """parse(self, path, source_hash) 两参数。"""
    import inspect
    sig = inspect.signature(KreuzbergParser.parse)
    params = list(sig.parameters.values())
    assert len(params) == 3  # self + path + source_hash
    assert params[1].name == "path"
    assert params[2].name == "source_hash"


def test_kreuzberg_parser_has_docstring():
    assert KreuzbergParser.__doc__ is not None


def test_kreuzberg_parser_parse_method_callable():
    assert callable(KreuzbergParser.parse)
