"""纯文本 parser 的单元测试 + 端到端 pipeline 测试。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.models import Document
from app.parsers import ParserError
from app.parsers.text_parser import TextParser, _split_paragraphs


VENV_PYTHON = str(
    Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PYTHON = VENV_PYTHON if Path(VENV_PYTHON).is_file() else sys.executable


def _write_text(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------- 基础切分 ----------


def test_text_single_paragraph(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "Just one paragraph with no blank lines.\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "Just one paragraph with no blank lines."


def test_text_two_paragraphs_blank_line_separated(tmp_path: Path):
    content = "First paragraph.\n\nSecond paragraph.\n"
    p = _write_text(tmp_path, "b.txt", content)
    doc = TextParser().parse(p, source_hash="b" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 2
    assert paras[0].content == "First paragraph."
    assert paras[1].content == "Second paragraph."


def test_text_multiple_blank_lines_treated_as_one_separator(tmp_path: Path):
    """连续多个空行也只算一个分隔。"""
    content = "Para one.\n\n\n\n\nPara two.\n"
    p = _write_text(tmp_path, "c.txt", content)
    doc = TextParser().parse(p, source_hash="c" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 2


def test_text_multiple_lines_in_one_paragraph(tmp_path: Path):
    """段落内的换行保留；不合并成空格。"""
    content = "line one\nline two\nline three\n"
    p = _write_text(tmp_path, "d.txt", content)
    doc = TextParser().parse(p, source_hash="d" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "line one\nline two\nline three"


def test_text_crlf_normalized(tmp_path: Path):
    """Windows CRLF 被归一化为 LF。"""
    content = "First.\r\n\r\nSecond.\r\n"
    p = _write_text(tmp_path, "e.txt", content)
    doc = TextParser().parse(p, source_hash="e" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 2
    assert paras[0].content == "First."
    assert paras[1].content == "Second."


def test_text_strips_leading_trailing_whitespace(tmp_path: Path):
    """段落首尾的空白被 strip。"""
    content = "\n\n\n   middle content   \n\n"
    p = _write_text(tmp_path, "f.txt", content)
    doc = TextParser().parse(p, source_hash="10" * 32)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "middle content"


def test_text_only_whitespace_lines_skipped(tmp_path: Path):
    """全空白行不产生段落。"""
    content = "   \n\t\n   \n"
    p = _write_text(tmp_path, "g.txt", content)
    doc = TextParser().parse(p, source_hash="11" * 32)
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "text_no_content" in codes


def test_text_empty_file_warning(tmp_path: Path):
    p = _write_text(tmp_path, "empty.txt", "")
    doc = TextParser().parse(p, source_hash="12" * 32)
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "text_no_content" in codes


# ---------- source_locator ----------


def test_text_line_numbers_1_indexed(tmp_path: Path):
    """locator.line 是段落起始行的 1-indexed 行号。"""
    content = "Para one.\n\nPara two starts here.\n"
    p = _write_text(tmp_path, "h.txt", content)
    doc = TextParser().parse(p, source_hash="13" * 32)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras[0].source_locator["line"] == 1
    # 第二段在第 3 行（para one 在第 1 行；第 2 行是空；第 3 行是 para two）
    assert paras[1].source_locator["line"] == 3


def test_text_line_number_after_multiple_blank_lines(tmp_path: Path):
    content = "First.\n\n\n\n\nSecond.\n"
    p = _write_text(tmp_path, "i.txt", content)
    doc = TextParser().parse(p, source_hash="14" * 32)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    # 第 1 行 first；第 2-5 空；第 6 行 second
    assert paras[1].source_locator["line"] == 6


def test_text_locator_no_section_path_key(tmp_path: Path):
    """纯文本不需要 section_path；locator 只含 line。"""
    p = _write_text(tmp_path, "j.txt", "hi\n")
    doc = TextParser().parse(p, source_hash="15" * 32)
    para = doc.elements[0]
    assert "section_path" not in para.source_locator
    assert set(para.source_locator.keys()) == {"line"}


# ---------- split_paragraphs 单元测试 ----------


def test_split_paragraphs_handles_empty_string():
    assert _split_paragraphs("") == []


def test_split_paragraphs_handles_whitespace_only():
    assert _split_paragraphs("   \n\n\t\n") == []


def test_split_paragraphs_single_chunk_no_trailing_newline():
    result = _split_paragraphs("just text")
    assert len(result) == 1
    assert result[0] == (1, "just text")


def test_split_paragraphs_cr_only_line_endings():
    """老 Mac 风格 \\r（无 \\n）也要被归一化为换行。"""
    result = _split_paragraphs("line one\rline two\r\rpara two")
    # \r 归一为 \n：3 行 + 1 空行 + 1 行
    # "line one" + "line two" 是连续非空行 → 同一段；空行分隔 → "para two" 第二段
    assert len(result) == 2
    assert result[0] == (1, "line one\nline two")
    assert result[1] == (4, "para two")


def test_split_paragraphs_trailing_blank_lines_ignored():
    result = _split_paragraphs("content\n\n\n")
    assert result == [(1, "content")]


def test_split_paragraphs_leading_blank_lines_skipped():
    """文件开头就有空行不应偏移第一段的行号。"""
    result = _split_paragraphs("\n\n\nactual content")
    # 第 4 行才是 actual content
    assert result == [(4, "actual content")]


def test_split_paragraphs_multiple_chunks_line_numbers():
    result = _split_paragraphs("first\n\nsecond\n\nthird")
    assert result == [
        (1, "first"),
        (3, "second"),
        (5, "third"),
    ]


# ---------- 错误路径 ----------


def test_text_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        TextParser().parse(tmp_path / "nope.txt", source_hash="x" * 64)
    assert exc.value.code == "file_not_found"


def test_text_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("hi")
    with pytest.raises(ParserError) as exc:
        TextParser().parse(p, source_hash="y" * 64)
    assert exc.value.code == "unsupported_type"


def test_text_long_extension_accepted(tmp_path: Path):
    p = _write_text(tmp_path, "x.text", "hello\n")
    doc = TextParser().parse(p, source_hash="z" * 64)
    assert doc.source_type == "text"
    assert doc.elements[0].type == "paragraph"


# ---------- Document 字段 / schema ----------


def test_text_parser_name_and_version(tmp_path: Path):
    p = _write_text(tmp_path, "x.txt", "hi\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert doc.parser_name == "text"
    assert doc.parser_version.startswith("stdlib/")
    assert doc.chunks == []
    assert doc.errors == []


def test_text_full_document_schema_valid(tmp_path: Path):
    from app.schema import validate

    content = (
        "Intro paragraph one.\n\n"
        "Second paragraph with more text.\n\n"
        "Third paragraph.\n"
    )
    p = _write_text(tmp_path, "full.txt", content)
    doc = TextParser().parse(p, source_hash="b" * 64)
    validate(doc.to_dict())


def test_text_pipeline_end_to_end(tmp_path: Path):
    from app.pipeline import process_single

    content = (
        "First meaningful paragraph with enough text to chunk.\n\n"
        "Second paragraph. More content here.\n\n"
        "Third paragraph to ensure multiple chunks.\n"
    )
    src = _write_text(tmp_path, "doc.txt", content)
    out = tmp_path / "out.json"
    document, errors = process_single(src, out, parser_name="text", write_json=True)
    assert errors == []
    assert document is not None
    assert document.source_type == "text"
    assert len(document.elements) == 3
    assert len(document.chunks) >= 1
    for c in document.chunks:
        assert c.source_element_ids


def test_cli_parse_text_end_to_end(tmp_path: Path):
    src = tmp_path / "doc.txt"
    src.write_text("Hello text world.\n\nSecond paragraph.\n", encoding="utf-8")
    out = tmp_path / "out.json"

    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(PROJECT_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    proc = subprocess.run(
        [_PYTHON, "-m", "app.cli", "parse", str(src),
         "-o", str(out), "--parser", "text"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    assert "[OK]" in proc.stdout
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_type"] == "text"
    assert data["parser_name"] == "text"
    assert len(data["elements"]) == 2


# ---------- 边角与缺漏补强（Round 37） ----------


# _detect_text_source_type 直接单测


def test_detect_text_source_type_accepts_txt():
    from app.parsers.text_parser import _detect_text_source_type
    assert _detect_text_source_type(Path("doc.txt")) == "text"


def test_detect_text_source_type_accepts_text():
    from app.parsers.text_parser import _detect_text_source_type
    assert _detect_text_source_type(Path("doc.text")) == "text"


def test_detect_text_source_type_accepts_uppercase_extensions():
    """扩展名 lower() 后比较，所以 .TXT 也接受。"""
    from app.parsers.text_parser import _detect_text_source_type
    assert _detect_text_source_type(Path("doc.TXT")) == "text"
    assert _detect_text_source_type(Path("doc.TEXT")) == "text"


def test_detect_text_source_type_rejects_markdown():
    from app.parsers.text_parser import _detect_text_source_type
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("doc.md"))
    assert exc.value.code == "unsupported_type"


def test_detect_text_source_type_rejects_no_suffix():
    from app.parsers.text_parser import _detect_text_source_type
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("noext"))


# TextParser metadata / element 边角


def test_text_parser_metadata_has_text_true(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert doc.metadata == {"text": True}


def test_text_parser_element_confidence_is_095(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.confidence == 0.95


def test_text_parser_element_id_format(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    expected_prefix = "doc-" + "a" * 16
    for i, el in enumerate(doc.elements):
        assert el.element_id == f"{expected_prefix}::e{i:04d}"


def test_text_parser_element_type_is_paragraph(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n\nworld\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.type == "paragraph"


def test_text_parser_element_metadata_is_empty_dict(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.metadata == {}


def test_text_parser_element_parent_id_is_none(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.parent_id is None


def test_text_parser_source_path_preserved(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert doc.source_path == str(p)


def test_text_parser_source_hash_passed_through(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    custom_hash = "b" * 64
    doc = TextParser().parse(p, source_hash=custom_hash)
    assert doc.source_hash == custom_hash


def test_text_parser_document_id_derived_from_hash(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert doc.document_id == "doc-" + "a" * 16


def test_text_parser_chunks_empty_by_default(tmp_path: Path):
    """parser 只产 elements，chunking 由 pipeline 串接。"""
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert doc.chunks == []


def test_text_parser_relations_empty_by_default(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert doc.relations == []


def test_text_parser_errors_empty_by_default(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert doc.errors == []


# _split_paragraphs 更多边角


def test_split_paragraphs_single_chunk_with_trailing_newline():
    from app.parsers.text_parser import _split_paragraphs
    result = _split_paragraphs("hello\n")
    assert len(result) == 1
    assert result[0][0] == 1  # start_line
    assert result[0][1] == "hello"


def test_split_paragraphs_returns_content_without_trailing_whitespace():
    from app.parsers.text_parser import _split_paragraphs
    result = _split_paragraphs("hello   \n")
    assert result[0][1] == "hello"


def test_split_paragraphs_handles_tabs_as_whitespace():
    from app.parsers.text_parser import _split_paragraphs
    result = _split_paragraphs("\thello\n")
    assert len(result) == 1
    assert result[0][1] == "hello"


# TextParser warning 边角


def test_text_parser_empty_file_emits_warning(tmp_path: Path):
    p = _write_text(tmp_path, "empty.txt", "")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 0
    warning_codes = [w.code for w in doc.warnings]
    assert "text_no_content" in warning_codes


def test_text_parser_whitespace_only_file_emits_warning(tmp_path: Path):
    p = _write_text(tmp_path, "ws.txt", "   \n\n  \t  \n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 0
    warning_codes = [w.code for w in doc.warnings]
    assert "text_no_content" in warning_codes


# TextParser 错误路径


def test_text_parser_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        TextParser().parse(tmp_path / "nope.txt", source_hash="a" * 64)
    assert exc.value.code == "file_not_found"


def test_text_parser_unsupported_extension_raises(tmp_path: Path):
    p = _write_text(tmp_path, "doc.md", "hello\n")
    with pytest.raises(ParserError) as exc:
        TextParser().parse(p, source_hash="a" * 64)
    assert exc.value.code == "unsupported_type"


# TextParser UTF-8 fallback


def test_text_parser_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    """非法 UTF-8 → 用 errors=replace 而不是抛 UnicodeDecodeError。"""
    p = tmp_path / "bad.txt"
    p.write_bytes(b"\xff\xfe hello world\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    # 不抛异常，仍能提取 element
    assert len(doc.elements) >= 1


def test_text_parser_name_and_version_constants(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert doc.parser_name == "text"
    assert doc.parser_version == "stdlib/0.1.0"


# section_path 缺失（text locator 只有 line）


def test_text_parser_locator_only_has_line_key(tmp_path: Path):
    p = _write_text(tmp_path, "a.txt", "hello\n\nworld\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert set(el.source_locator.keys()) == {"line"}
