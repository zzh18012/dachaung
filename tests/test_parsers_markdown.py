"""Markdown parser 的单元测试 + 端到端 pipeline 测试。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.models import Document
from app.parsers import ParserError
from app.parsers.markdown_parser import MarkdownParser


VENV_PYTHON = str(
    Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PYTHON = VENV_PYTHON if Path(VENV_PYTHON).is_file() else sys.executable


def _write_md(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------- 基础：单块解析 ----------


def test_atx_heading_levels(tmp_path: Path):
    md = "# H1\n\n## H2\n\n### H3\n\n#### H4\n\n##### H5\n\n###### H6\n"
    p = _write_md(tmp_path, "h.md", md)
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    assert doc.source_type == "markdown"
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 6
    assert [h.metadata["level"] for h in headings] == [1, 2, 3, 4, 5, 6]
    assert [h.content for h in headings] == ["H1", "H2", "H3", "H4", "H5", "H6"]


def test_atx_heading_closing_hashes_stripped(tmp_path: Path):
    """ATX 标题尾部允许闭合 ###。"""
    p = _write_md(tmp_path, "x.md", "# Title #\n")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    h = doc.elements[0]
    assert h.type == "heading"
    assert h.content == "Title"


def test_paragraph_multiple_lines_merged(tmp_path: Path):
    """无空行分隔的连续文本合并为一个段落（CommonMark 行为）。"""
    md = "Line one.\nLine two.\nLine three.\n"
    p = _write_md(tmp_path, "p.md", md)
    doc = MarkdownParser().parse(p, source_hash="b" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert "Line one." in paras[0].content
    assert "Line three." in paras[0].content
    # 换行保留
    assert "\n" in paras[0].content


def test_blank_line_separates_paragraphs(tmp_path: Path):
    md = "First paragraph.\n\nSecond paragraph.\n"
    p = _write_md(tmp_path, "pp.md", md)
    doc = MarkdownParser().parse(p, source_hash="c" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 2
    assert paras[0].content == "First paragraph."
    assert paras[1].content == "Second paragraph."


def test_unordered_list_items(tmp_path: Path):
    md = "- apple\n* banana\n+ cherry\n"
    p = _write_md(tmp_path, "ul.md", md)
    doc = MarkdownParser().parse(p, source_hash="d" * 64)
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 3
    assert [it.content for it in items] == ["apple", "banana", "cherry"]
    assert all(it.metadata["ordered"] is False for it in items)


def test_ordered_list_items(tmp_path: Path):
    md = "1. first\n2. second\n3. third\n"
    p = _write_md(tmp_path, "ol.md", md)
    doc = MarkdownParser().parse(p, source_hash="e" * 64)
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 3
    assert [it.content for it in items] == ["first", "second", "third"]
    assert all(it.metadata["ordered"] is True for it in items)


def test_mixed_ordered_unordered(tmp_path: Path):
    md = "- a\n1. b\n- c\n"
    p = _write_md(tmp_path, "mix.md", md)
    doc = MarkdownParser().parse(p, source_hash="f" * 64)
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 3
    assert items[0].metadata["ordered"] is False
    assert items[1].metadata["ordered"] is True
    assert items[2].metadata["ordered"] is False


def test_fenced_code_block_backtick(tmp_path: Path):
    md = "```python\nprint('hi')\nx = 1\n```\n"
    p = _write_md(tmp_path, "code.md", md)
    doc = MarkdownParser().parse(p, source_hash="10" * 32)
    code = [e for e in doc.elements if e.metadata.get("kind") == "code_block"]
    assert len(code) == 1
    assert "print('hi')" in code[0].content
    assert "x = 1" in code[0].content
    assert code[0].metadata["language"] == "python"


def test_fenced_code_block_tilde(tmp_path: Path):
    md = "~~~\nraw code\n~~~\n"
    p = _write_md(tmp_path, "code2.md", md)
    doc = MarkdownParser().parse(p, source_hash="11" * 32)
    code = [e for e in doc.elements if e.metadata.get("kind") == "code_block"]
    assert len(code) == 1
    assert code[0].content == "raw code"
    assert code[0].metadata["language"] == ""


def test_blockquote_merged(tmp_path: Path):
    md = "> first line\n> second line\n> third line\n"
    p = _write_md(tmp_path, "q.md", md)
    doc = MarkdownParser().parse(p, source_hash="12" * 32)
    bqs = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    assert len(bqs) == 1
    assert "first line" in bqs[0].content
    assert "third line" in bqs[0].content


def test_pipe_table(tmp_path: Path):
    md = "| Name | Age |\n| --- | --- |\n| Alice | 30 |\n| Bob | 25 |\n"
    p = _write_md(tmp_path, "t.md", md)
    doc = MarkdownParser().parse(p, source_hash="13" * 32)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    t = tables[0]
    assert "Name" in t.content and "Age" in t.content
    assert "Alice" in t.content and "Bob" in t.content
    assert t.metadata["row_count"] == 3
    assert t.metadata["col_count"] == 2


def test_standalone_image_line(tmp_path: Path):
    md = "![alt text](images/diagram.png)\n"
    p = _write_md(tmp_path, "img.md", md)
    doc = MarkdownParser().parse(p, source_hash="14" * 32)
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 1
    assert imgs[0].resource_path == "images/diagram.png"
    assert imgs[0].metadata["alt"] == "alt text"


def test_thematic_break_skipped(tmp_path: Path):
    """---/***/___ 单独成行：忽略，不产生 element。"""
    md = "para before\n\n---\n\npara after\n"
    p = _write_md(tmp_path, "tb.md", md)
    doc = MarkdownParser().parse(p, source_hash="15" * 32)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 2
    assert paras[0].content == "para before"
    assert paras[1].content == "para after"


# ---------- source_locator ----------


def test_section_path_tracking(tmp_path: Path):
    """section_path 跟踪 ATX 标题层级；同级或更高级标题弹出栈。"""
    md = (
        "# Chapter\n"
        "Intro paragraph.\n"
        "## Section A\n"
        "Text in A.\n"
        "## Section B\n"
        "Text in B.\n"
        "# Chapter 2\n"
        "Text in ch2.\n"
    )
    p = _write_md(tmp_path, "sec.md", md)
    doc = MarkdownParser().parse(p, source_hash="16" * 32)
    # 验证 section_path 演化
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras[0].source_locator["section_path"] == "Chapter"
    assert paras[1].source_locator["section_path"] == "Chapter > Section A"
    assert paras[2].source_locator["section_path"] == "Chapter > Section B"
    # 第二个 H1 弹出所有 H2，section_path 仅含 "Chapter 2"
    assert paras[3].source_locator["section_path"] == "Chapter 2"


def test_line_numbers_are_1_indexed(tmp_path: Path):
    md = "\n\n# Title\n\nPara.\n"
    p = _write_md(tmp_path, "lines.md", md)
    doc = MarkdownParser().parse(p, source_hash="17" * 32)
    heading = doc.elements[0]
    # 第 3 行（1-indexed）
    assert heading.source_locator["line"] == 3
    # paragraph 在第 5 行
    para = doc.elements[1]
    assert para.source_locator["line"] == 5


def test_section_path_absent_for_preamble(tmp_path: Path):
    """标题之前的元素没有 section_path 键。"""
    md = "Preamble paragraph.\n\n# First heading\n"
    p = _write_md(tmp_path, "pre.md", md)
    doc = MarkdownParser().parse(p, source_hash="18" * 32)
    para = doc.elements[0]
    assert para.source_locator["line"] == 1
    assert "section_path" not in para.source_locator


# ---------- 错误路径 ----------


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        MarkdownParser().parse(tmp_path / "nope.md", source_hash="x" * 64)
    assert exc.value.code == "file_not_found"


def test_unsupported_extension_raises(tmp_path: Path):
    p = _write_md(tmp_path, "x.txt", "hello")
    with pytest.raises(ParserError) as exc:
        MarkdownParser().parse(p, source_hash="y" * 64)
    assert exc.value.code == "unsupported_type"


def test_markdown_extension_accepted(tmp_path: Path):
    """`.markdown`（长形式）也被接受。"""
    p = _write_md(tmp_path, "x.markdown", "# Hi\n")
    doc = MarkdownParser().parse(p, source_hash="z" * 64)
    assert doc.source_type == "markdown"
    assert doc.elements[0].type == "heading"


def test_empty_file_yields_warning(tmp_path: Path):
    p = _write_md(tmp_path, "empty.md", "")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "md_no_content" in codes


# ---------- Document 字段 ----------


def test_parser_name_and_version(tmp_path: Path):
    p = _write_md(tmp_path, "x.md", "# Hi\n")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    assert doc.parser_name == "markdown"
    assert doc.parser_version.startswith("stdlib/")
    assert doc.chunks == []
    assert doc.errors == []


def test_document_id_derived_from_hash(tmp_path: Path):
    p = _write_md(tmp_path, "x.md", "# Hi\n")
    # 6 * 10 + 4 = 64 字符
    source_hash = "abc123" * 10 + "abcd"
    assert len(source_hash) == 64
    doc = MarkdownParser().parse(p, source_hash=source_hash)
    # make_document_id 取前 16 字符
    assert doc.document_id == "doc-abc123abc123abc1"


# ---------- 综合 + schema ----------


def test_full_document_schema_valid(tmp_path: Path):
    """完整 Markdown → Document → JSON 通过 schema 校验。"""
    from app.schema import validate

    md = (
        "# Title\n\n"
        "Intro paragraph.\n\n"
        "## Subsection\n\n"
        "- item 1\n"
        "- item 2\n\n"
        "```python\n"
        "x = 1\n"
        "```\n\n"
        "> A quote.\n\n"
        "| A | B |\n"
        "|---|---|\n"
        "| 1 | 2 |\n\n"
        "![alt](pic.png)\n"
    )
    p = _write_md(tmp_path, "full.md", md)
    doc = MarkdownParser().parse(p, source_hash="b" * 64)
    validate(doc.to_dict())  # 不抛异常即通过


# 机械搬运（阶段 3 提交 1）：以下两个依赖 pipeline 注册/CLI 的端到端测试
# 曾按三段式计划推迟；阶段 3 提交 3（注册启用）原样搬回如下。


def test_pipeline_end_to_end_with_markdown(tmp_path: Path):
    """app.pipeline.process_single 对 .md 输入完整跑通 parse→chunk→validate→write。"""
    from app.pipeline import process_single

    md = (
        "# Project\n\n"
        "This is a paragraph with enough text to be useful for chunking.\n\n"
        "## Background\n\n"
        "More content here. Lorem ipsum dolor sit amet.\n\n"
        "- one\n"
        "- two\n"
    )
    src = _write_md(tmp_path, "doc.md", md)
    out = tmp_path / "out.json"
    document, errors = process_single(src, out, parser_name="markdown", write_json=True)
    assert errors == []
    assert document is not None
    assert document.source_type == "markdown"
    # 至少有 heading + paragraph + list_item
    types = {e.type for e in document.elements}
    assert "heading" in types
    assert "paragraph" in types
    assert "list_item" in types
    # chunker 对所有非 image element 都应产出 chunk
    assert len(document.chunks) >= 1
    for c in document.chunks:
        assert c.source_element_ids  # 非空
    # 输出文件存在
    assert out.is_file()


def test_cli_parse_markdown_end_to_end(tmp_path: Path):
    """`python -m app.cli parse doc.md -o out.json --parser markdown` 跑通。"""
    md = "# Title\n\nHello markdown world.\n"
    src = tmp_path / "doc.md"
    src.write_text(md, encoding="utf-8")
    out = tmp_path / "out.json"

    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(PROJECT_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    proc = subprocess.run(
        [_PYTHON, "-m", "app.cli", "parse", str(src),
         "-o", str(out), "--parser", "markdown"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    assert "[OK]" in proc.stdout
    assert out.is_file()
    # 输出 JSON 通过 schema 校验
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_type"] == "markdown"
    assert data["parser_name"] == "markdown"
    assert len(data["elements"]) >= 2

# ---------- 内部 helpers（纯函数）----------

from pathlib import Path as _Path  # noqa: E402

from app.parsers.markdown_parser import (  # noqa: E402
    _detect_md_source_type,
    _is_pipe_table_start,
    _rows_to_md,
    _split_pipe_row,
)


def test_detect_md_source_type_accepts_md_and_markdown():
    assert _detect_md_source_type(_Path("foo.md")) == "markdown"
    assert _detect_md_source_type(_Path("foo.markdown")) == "markdown"
    # 大小写不敏感
    assert _detect_md_source_type(_Path("FOO.MD")) == "markdown"


def test_detect_md_source_type_rejects_other_extensions():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(_Path("foo.txt"))
    assert exc.value.code == "unsupported_type"


def test_rows_to_md_empty():
    assert _rows_to_md([]) == ""


def test_rows_to_md_single_row():
    md = _rows_to_md([["a", "b"]])
    # 表头 + 分隔行，无数据行
    lines = md.splitlines()
    assert len(lines) == 2
    assert "| a | b |" in lines[0]
    assert "| --- | --- |" in lines[1]


def test_rows_to_md_pads_uneven_rows():
    md = _rows_to_md([["a", "b"], ["c"]])
    lines = md.splitlines()
    # 第二行（数据）应该被填充
    assert lines[2].count("|") == lines[0].count("|")
    assert "c" in lines[2]


def test_split_pipe_row_basic():
    assert _split_pipe_row("| a | b | c |") == ["a", "b", "c"]


def test_split_pipe_row_without_outer_pipes():
    assert _split_pipe_row("a | b | c") == ["a", "b", "c"]


def test_split_pipe_row_strips_cells():
    assert _split_pipe_row("|  spaced  |  trim  |") == ["spaced", "trim"]


def test_split_pipe_row_single_cell():
    assert _split_pipe_row("| only |") == ["only"]


def test_is_pipe_table_start_true_for_valid_table():
    lines = ["| a | b |", "| --- | --- |", "| 1 | 2 |"]
    assert _is_pipe_table_start(lines, 0) is True


def test_is_pipe_table_start_false_when_no_separator_line():
    lines = ["| a | b |", "| 1 | 2 |"]  # 缺少 --- 分隔行
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_false_at_last_line():
    """最后一行不可能有下一行做分隔。"""
    lines = ["| a | b |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_false_for_non_pipe_first_line():
    lines = ["regular text", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is False


# ---------- 边角与缺漏补强（Round 37） ----------


# _ATX_HEADING_RE 直接单测


def test_atx_heading_re_matches_six_levels():
    from app.parsers.markdown_parser import _ATX_HEADING_RE
    for level in range(1, 7):
        prefix = "#" * level
        m = _ATX_HEADING_RE.match(f"{prefix} Title")
        assert m is not None
        assert len(m.group(1)) == level
        assert m.group(2) == "Title"


def test_atx_heading_re_strips_trailing_hashes():
    from app.parsers.markdown_parser import _ATX_HEADING_RE
    m = _ATX_HEADING_RE.match("# Title ###")
    assert m is not None
    assert m.group(2) == "Title"


def test_atx_heading_re_rejects_seven_hashes():
    """7 个 # 不在 1-6 范围内（regex 是 `#{1,6}\\s+`，第 7 个 # 不是空白）。"""
    from app.parsers.markdown_parser import _ATX_HEADING_RE
    m = _ATX_HEADING_RE.match("####### Too many")
    assert m is None


def test_atx_heading_re_rejects_no_space_after_hashes():
    from app.parsers.markdown_parser import _ATX_HEADING_RE
    m = _ATX_HEADING_RE.match("#Title")  # 无空格
    assert m is None


def test_atx_heading_re_matches_inline_content_with_hash():
    """标题内容可以含 #。"""
    from app.parsers.markdown_parser import _ATX_HEADING_RE
    m = _ATX_HEADING_RE.match("# Title #1")
    assert m is not None
    assert m.group(2) == "Title #1"


# _THEMATIC_RE


def test_thematic_re_matches_dash_star_underscore():
    from app.parsers.markdown_parser import _THEMATIC_RE
    assert _THEMATIC_RE.match("---")
    assert _THEMATIC_RE.match("***")
    assert _THEMATIC_RE.match("___")
    assert _THEMATIC_RE.match("- - -")
    assert _THEMATIC_RE.match("*  *  *")


def test_thematic_re_rejects_short_strings():
    from app.parsers.markdown_parser import _THEMATIC_RE
    assert _THEMATIC_RE.match("-") is None
    assert _THEMATIC_RE.match("--") is None
    assert _THEMATIC_RE.match("a-b-c") is None


# _FENCED_RE


def test_fenced_re_matches_backtick_and_tilde():
    from app.parsers.markdown_parser import _FENCED_RE
    assert _FENCED_RE.match("```")
    assert _FENCED_RE.match("~~~")
    assert _FENCED_RE.match("````")
    assert _FENCED_RE.match("~~~~~~")


def test_fenced_re_captures_language():
    from app.parsers.markdown_parser import _FENCED_RE
    m = _FENCED_RE.match("```python")
    assert m is not None
    assert m.group(2) == "python"


def test_fenced_re_no_language_empty_string():
    from app.parsers.markdown_parser import _FENCED_RE
    m = _FENCED_RE.match("```")
    assert m is not None
    assert m.group(2) == ""


# _UNORDERED_LIST_RE / _ORDERED_LIST_RE


def test_unordered_list_re_matches_dash_star_plus():
    from app.parsers.markdown_parser import _UNORDERED_LIST_RE
    assert _UNORDERED_LIST_RE.match("- item")
    assert _UNORDERED_LIST_RE.match("* item")
    assert _UNORDERED_LIST_RE.match("+ item")


def test_unordered_list_re_captures_content():
    from app.parsers.markdown_parser import _UNORDERED_LIST_RE
    m = _UNORDERED_LIST_RE.match("- hello world")
    assert m is not None
    assert m.group(1) == "hello world"


def test_ordered_list_re_matches_dot_and_paren():
    from app.parsers.markdown_parser import _ORDERED_LIST_RE
    assert _ORDERED_LIST_RE.match("1. item")
    assert _ORDERED_LIST_RE.match("1) item")
    assert _ORDERED_LIST_RE.match("42. item")


def test_ordered_list_re_captures_content():
    from app.parsers.markdown_parser import _ORDERED_LIST_RE
    m = _ORDERED_LIST_RE.match("1. hello")
    assert m is not None
    assert m.group(1) == "hello"


# _BLOCKQUOTE_RE


def test_blockquote_re_matches_with_or_without_space():
    from app.parsers.markdown_parser import _BLOCKQUOTE_RE
    m1 = _BLOCKQUOTE_RE.match("> hello")
    assert m1 is not None
    assert m1.group(1) == "hello"
    m2 = _BLOCKQUOTE_RE.match(">hello")
    assert m2 is not None
    assert m2.group(1) == "hello"


# _STANDALONE_IMAGE_RE


def test_standalone_image_re_matches_full_line():
    from app.parsers.markdown_parser import _STANDALONE_IMAGE_RE
    m = _STANDALONE_IMAGE_RE.match("![alt text](http://example.com/x.png)")
    assert m is not None
    assert m.group(1) == "alt text"
    assert m.group(2) == "http://example.com/x.png"


def test_standalone_image_re_rejects_inline_image():
    """![alt](url) 前面有其他文本 → 不是 standalone。"""
    from app.parsers.markdown_parser import _STANDALONE_IMAGE_RE
    assert _STANDALONE_IMAGE_RE.match("text ![alt](url)") is None


def test_standalone_image_re_empty_alt_accepted():
    from app.parsers.markdown_parser import _STANDALONE_IMAGE_RE
    m = _STANDALONE_IMAGE_RE.match("![](url)")
    assert m is not None
    assert m.group(1) == ""
    assert m.group(2) == "url"


# _PIPE_TABLE_ROW_RE / _PIPE_TABLE_SEP_RE


def test_pipe_table_row_re_matches_pipe_lines():
    from app.parsers.markdown_parser import _PIPE_TABLE_ROW_RE
    assert _PIPE_TABLE_ROW_RE.match("| a | b |")
    assert _PIPE_TABLE_ROW_RE.match("  | a | b |  ")
    assert _PIPE_TABLE_ROW_RE.match("|a|b|")


def test_pipe_table_row_re_rejects_non_pipe_lines():
    from app.parsers.markdown_parser import _PIPE_TABLE_ROW_RE
    assert _PIPE_TABLE_ROW_RE.match("regular text") is None


def test_pipe_table_sep_re_matches_separator():
    from app.parsers.markdown_parser import _PIPE_TABLE_SEP_RE
    assert _PIPE_TABLE_SEP_RE.match("| --- | --- |")
    assert _PIPE_TABLE_SEP_RE.match("|:---:|:---:|")


# MarkdownParser metadata / element 边角


def test_markdown_parser_metadata_has_markdown_true(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("# T\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    assert doc.metadata == {"markdown": True}


def test_markdown_parser_element_confidence_is_095(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("# T\n\nparagraph.\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.confidence == 0.95


def test_markdown_parser_element_id_format(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("# T\n\npara.\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    expected_prefix = "doc-" + "a" * 16
    for i, el in enumerate(doc.elements):
        assert el.element_id == f"{expected_prefix}::e{i:04d}"


def test_markdown_parser_code_block_has_language_metadata(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("```python\nprint(1)\n```\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    code_blocks = [e for e in doc.elements if e.metadata.get("kind") == "code_block"]
    assert len(code_blocks) == 1
    assert code_blocks[0].metadata.get("language") == "python"


def test_markdown_parser_blockquote_has_kind_metadata(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("> quoted text\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    blockquotes = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    assert len(blockquotes) == 1


def test_markdown_parser_list_item_has_ordered_metadata(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("1. first\n2. second\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    list_items = [e for e in doc.elements if e.type == "list_item"]
    assert len(list_items) == 2
    for li in list_items:
        assert li.metadata.get("ordered") is True
        assert li.metadata.get("marker") == "ordered"


def test_markdown_parser_unordered_list_item_metadata(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("- first\n- second\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    list_items = [e for e in doc.elements if e.type == "list_item"]
    assert len(list_items) == 2
    for li in list_items:
        assert li.metadata.get("ordered") is False
        assert li.metadata.get("marker") == "unordered"


def test_markdown_parser_table_has_row_and_col_count(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("| a | b | c |\n| --- | --- | --- |\n| 1 | 2 | 3 |\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    t = tables[0]
    assert t.metadata.get("row_count") == 2
    assert t.metadata.get("col_count") == 3
    assert t.metadata.get("source") == "markdown_pipe_table"


def test_markdown_parser_image_element_has_alt_metadata(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("![my image](http://example.com/x.png)\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    images = [e for e in doc.elements if e.type == "image"]
    assert len(images) == 1
    assert images[0].metadata.get("alt") == "my image"
    assert images[0].resource_path == "http://example.com/x.png"
    assert images[0].content is None


def test_markdown_parser_empty_code_block_emits_warning(tmp_path: Path):
    """空代码块（紧邻的两个 fence）→ md_empty_code_block 警告。"""
    p = tmp_path / "doc.md"
    p.write_text("```\n```\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    warning_codes = [w.code for w in doc.warnings]
    assert "md_empty_code_block" in warning_codes


# _detect_md_source_type 边角


def test_detect_md_source_type_lowercase_only():
    """扩展名检查是 lower() 后比较，所以大写 .MD 也会接受。"""
    from app.parsers.markdown_parser import _detect_md_source_type
    assert _detect_md_source_type(Path("doc.MD")) == "markdown"
    assert _detect_md_source_type(Path("doc.MARKDOWN")) == "markdown"


def test_detect_md_source_type_unsupported_suffix_raises():
    from app.parsers.markdown_parser import _detect_md_source_type
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("doc.html"))
    assert exc.value.code == "unsupported_type"


def test_detect_md_source_type_no_suffix_raises():
    from app.parsers.markdown_parser import _detect_md_source_type
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("noext"))


# _rows_to_md 边角


def test_rows_to_md_two_rows():
    from app.parsers.markdown_parser import _rows_to_md
    md = _rows_to_md([["h1", "h2"], ["a", "b"]])
    lines = md.split("\n")
    assert len(lines) == 3  # header + separator + 1 body row
    assert lines[0] == "| h1 | h2 |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| a | b |"


def test_rows_to_md_jagged_pads_with_empty():
    from app.parsers.markdown_parser import _rows_to_md
    md = _rows_to_md([["h1", "h2", "h3"], ["a"]])
    lines = md.split("\n")
    assert lines[2] == "| a |  |  |"
