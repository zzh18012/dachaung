r"""app/parsers/text_parser.py 边角测试 - 第六轮（Round 168）。

补强已有 base/edges/edges2-5（共 455 测试）未覆盖的深度：
- _TEXT_EXTENSIONS 常量精确
- _detect_text_source_type details 精确
- _split_paragraphs 边界（CRLF/CR 换行、连续空行、嵌套空白、首尾空行）
- TextParser 类属性与签名
- parse() 错误路径（file_not_found/unsupported/read_failed）
- parse() metadata 字段精确
- 各种文件内容场景
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
from app.parsers.text_parser import (
    _TEXT_EXTENSIONS,
    TextParser,
    _detect_text_source_type,
    _split_paragraphs,
)


_H = "a" * 64
_H2 = "b" * 64


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# =========================================================================
# _TEXT_EXTENSIONS
# =========================================================================


def test_text_extensions_exact():
    assert _TEXT_EXTENSIONS == (".txt", ".text")


def test_text_extensions_is_tuple():
    assert isinstance(_TEXT_EXTENSIONS, tuple)


def test_text_extensions_lowercase():
    for ext in _TEXT_EXTENSIONS:
        assert ext == ext.lower()


def test_text_extensions_starts_with_dot():
    for ext in _TEXT_EXTENSIONS:
        assert ext.startswith(".")


def test_text_extensions_length_two():
    assert len(_TEXT_EXTENSIONS) == 2


# =========================================================================
# _detect_text_source_type details
# =========================================================================


def test_detect_text_source_type_txt_returns_text():
    assert _detect_text_source_type(Path("foo.txt")) == "text"


def test_detect_text_source_type_text_returns_text():
    assert _detect_text_source_type(Path("foo.text")) == "text"


def test_detect_text_source_type_uppercase_txt():
    assert _detect_text_source_type(Path("foo.TXT")) == "text"


def test_detect_text_source_type_uppercase_text():
    assert _detect_text_source_type(Path("foo.TEXT")) == "text"


def test_detect_text_source_type_pdf_raises():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("foo.pdf"))
    assert exc.value.code == "unsupported_type"


def test_detect_text_source_type_no_suffix_raises():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("foo"))
    assert exc.value.code == "unsupported_type"


def test_detect_text_source_type_no_suffix_details_empty():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("foo"))
    assert exc.value.details == {"suffix": ""}


def test_detect_text_source_type_pdf_details_has_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("foo.pdf"))
    assert exc.value.details == {"suffix": ".pdf"}


def test_detect_text_source_type_message_mentions_txt_text():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("foo.pdf"))
    msg = exc.value.message
    assert ".txt" in msg
    assert ".text" in msg


def test_detect_text_source_type_message_mentions_actual_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("foo.json"))
    assert ".json" in exc.value.message


# =========================================================================
# _split_paragraphs 边界
# =========================================================================


def test_split_paragraphs_empty_string():
    assert _split_paragraphs("") == []


def test_split_paragraphs_single_line():
    result = _split_paragraphs("hello")
    assert len(result) == 1
    assert result[0] == (1, "hello")


def test_split_paragraphs_two_paragraphs_separated_by_blank_line():
    text = "para1\n\npara2"
    result = _split_paragraphs(text)
    assert len(result) == 2
    assert result[0] == (1, "para1")
    assert result[1] == (3, "para2")


def test_split_paragraphs_multiple_blank_lines():
    """连续多个空行 → 视为单一分隔。"""
    text = "para1\n\n\n\npara2"
    result = _split_paragraphs(text)
    assert len(result) == 2


def test_split_paragraphs_leading_blank_lines_skipped():
    text = "\n\nhello"
    result = _split_paragraphs(text)
    assert len(result) == 1
    assert result[0] == (3, "hello")


def test_split_paragraphs_trailing_blank_lines_skipped():
    text = "hello\n\n"
    result = _split_paragraphs(text)
    assert len(result) == 1
    assert result[0] == (1, "hello")


def test_split_paragraphs_crlf_normalized():
    """\r\n 应被归一为 \n。"""
    text = "para1\r\n\r\npara2"
    result = _split_paragraphs(text)
    assert len(result) == 2
    assert result[0][1] == "para1"
    assert result[1][1] == "para2"


def test_split_paragraphs_cr_only_normalized():
    """单独的 \\r 应被归一为 \\n。"""
    text = "para1\r\rpara2"
    result = _split_paragraphs(text)
    assert len(result) == 2


def test_split_paragraphs_whitespace_only_lines_ignored():
    """仅含空白的行视为空行。"""
    text = "para1\n   \n\t\npara2"
    result = _split_paragraphs(text)
    assert len(result) == 2


def test_split_paragraphs_only_whitespace_returns_empty():
    assert _split_paragraphs("   \n\t\n   ") == []


def test_split_paragraphs_only_newlines_returns_empty():
    assert _split_paragraphs("\n\n\n") == []


def test_split_paragraphs_consecutive_non_blank_lines_kept_together():
    """连续非空行合并到同一 paragraph（不切段）。"""
    text = "line1\nline2\nline3"
    result = _split_paragraphs(text)
    assert len(result) == 1
    assert "line1" in result[0][1]
    assert "line3" in result[0][1]
    # 内部 \n 保留
    assert "\n" in result[0][1]


def test_split_paragraphs_returns_list_of_tuples():
    result = _split_paragraphs("hello")
    assert isinstance(result, list)
    assert isinstance(result[0], tuple)
    assert len(result[0]) == 2


def test_split_paragraphs_start_line_1based():
    text = "para1\n\npara2"
    result = _split_paragraphs(text)
    assert result[0][0] == 1  # para1 在 line 1
    assert result[1][0] == 3  # para2 在 line 3


def test_split_paragraphs_content_strips_outer_whitespace():
    text = "  hello  "
    result = _split_paragraphs(text)
    assert result[0][1] == "hello"


def test_split_paragraphs_preserves_internal_newlines():
    text = "line1\nline2"
    result = _split_paragraphs(text)
    assert result[0][1] == "line1\nline2"


def test_split_paragraphs_idempotent():
    text = "para1\n\npara2"
    assert _split_paragraphs(text) == _split_paragraphs(text)


def test_split_paragraphs_does_not_mutate_input():
    text = "para1\n\npara2"
    before = text
    _split_paragraphs(text)
    assert text == before


def test_split_paragraphs_unicode_chinese():
    text = "中文段落\n\nanother"
    result = _split_paragraphs(text)
    assert len(result) == 2
    assert result[0][1] == "中文段落"


def test_split_paragraphs_mixed_blank_and_whitespace():
    text = "p1\n \n\ntab\t\np2"
    result = _split_paragraphs(text)
    assert len(result) == 2


# =========================================================================
# TextParser 类属性
# =========================================================================


def test_text_parser_name_value():
    assert TextParser.name == "text"


def test_text_parser_version_value():
    assert TextParser.version == "stdlib/0.1.0"


def test_text_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(TextParser, Parser)


def test_text_parser_init_no_args():
    p = TextParser()
    assert p is not None


def test_text_parser_has_parse_method():
    assert callable(TextParser.parse)


# =========================================================================
# parse() 错误路径
# =========================================================================


def test_parse_nonexistent_file_raises(tmp_path: Path):
    p = tmp_path / "missing.txt"
    with pytest.raises(ParserError) as exc:
        TextParser().parse(p, _H)
    assert exc.value.code == "file_not_found"


def test_parse_nonexistent_file_message(tmp_path: Path):
    p = tmp_path / "missing.txt"
    with pytest.raises(ParserError) as exc:
        TextParser().parse(p, _H)
    assert str(p) in exc.value.message


def test_parse_nonexistent_file_details(tmp_path: Path):
    p = tmp_path / "missing.txt"
    with pytest.raises(ParserError) as exc:
        TextParser().parse(p, _H)
    assert exc.value.details == {"path": str(p)}


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = _write(tmp_path, "foo.pdf", "hello")
    with pytest.raises(ParserError) as exc:
        TextParser().parse(p, _H)
    assert exc.value.code == "unsupported_type"


def test_parse_text_extension_works(tmp_path: Path):
    p = _write(tmp_path, "foo.text", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.source_type == "text"


# =========================================================================
# parse() 成功路径
# =========================================================================


def test_parse_returns_document(tmp_path: Path):
    p = _write(tmp_path, "test.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert isinstance(doc, Document)


def test_parse_metadata_has_text_true(tmp_path: Path):
    p = _write(tmp_path, "test.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.metadata == {"text": True}


def test_parse_source_type_text(tmp_path: Path):
    p = _write(tmp_path, "test.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.source_type == "text"


def test_parse_source_path_is_str(tmp_path: Path):
    p = _write(tmp_path, "test.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert isinstance(doc.source_path, str)
    assert doc.source_path == str(p)


def test_parse_source_hash_propagated(tmp_path: Path):
    p = _write(tmp_path, "test.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.source_hash == _H


def test_parse_parser_name_propagated(tmp_path: Path):
    p = _write(tmp_path, "test.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.parser_name == "text"


def test_parse_parser_version_propagated(tmp_path: Path):
    p = _write(tmp_path, "test.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.parser_version == "stdlib/0.1.0"


def test_parse_empty_chunks_relations_errors(tmp_path: Path):
    p = _write(tmp_path, "test.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []


def test_parse_uses_make_document_id(tmp_path: Path):
    from app.parsers.base import make_document_id
    p = _write(tmp_path, "test.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.document_id == make_document_id(_H)


def test_parse_empty_file_emits_warning(tmp_path: Path):
    p = _write(tmp_path, "empty.txt", "")
    doc = TextParser().parse(p, _H)
    assert any(w.code == "text_no_content" for w in doc.warnings)


def test_parse_whitespace_only_file_emits_warning(tmp_path: Path):
    p = _write(tmp_path, "ws.txt", "   \n\t\n   ")
    doc = TextParser().parse(p, _H)
    assert any(w.code == "text_no_content" for w in doc.warnings)


def test_parse_single_paragraph(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == "hello"


def test_parse_multi_paragraphs(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "para1\n\npara2\n\npara3")
    doc = TextParser().parse(p, _H)
    assert len(doc.elements) == 3
    contents = [e.content for e in doc.elements]
    assert contents == ["para1", "para2", "para3"]


def test_parse_locator_line_1based(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "para1\n\npara2")
    doc = TextParser().parse(p, _H)
    assert doc.elements[0].source_locator["line"] == 1
    assert doc.elements[1].source_locator["line"] == 3


def test_parse_element_id_zero_padded(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert "::e0000" in doc.elements[0].element_id


def test_parse_element_id_increments(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "p1\n\np2\n\np3")
    doc = TextParser().parse(p, _H)
    ids = [e.element_id for e in doc.elements]
    suffixes = [i.split("::")[1] for i in ids]
    assert suffixes == ["e0000", "e0001", "e0002"]


def test_parse_confidence_default_095(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.elements[0].confidence == 0.95


def test_parse_metadata_empty_dict_for_paragraph(tmp_path: Path):
    """TextParser 的 paragraph element metadata 是空 dict。"""
    p = _write(tmp_path, "x.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.elements[0].metadata == {}


def test_parse_no_warning_when_content_exists(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello")
    doc = TextParser().parse(p, _H)
    assert doc.warnings == []


def test_parse_crlf_file(tmp_path: Path):
    """CRLF 换行的文件。"""
    p = tmp_path / "x.txt"
    p.write_bytes(b"para1\r\n\r\npara2")
    doc = TextParser().parse(p, _H)
    assert len(doc.elements) == 2


def test_parse_unicode_file(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "中文段落")
    doc = TextParser().parse(p, _H)
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "中文段落"


def test_parse_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    """非 UTF-8 字节 → errors=replace fallback。"""
    p = tmp_path / "x.txt"
    # 写入非 UTF-8 字节（ latin-1 编码的高位字符）
    p.write_bytes(b"\xff\xfe hello")
    # 不应抛异常
    doc = TextParser().parse(p, _H)
    assert isinstance(doc, Document)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.parsers.text_parser as mod
    assert mod.__all__ == ["TextParser"]


def test_module_all_is_list():
    import app.parsers.text_parser as mod
    assert isinstance(mod.__all__, list)


def test_module_uses_future_annotations():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_imports_path():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_docstring_present():
    import app.parsers.text_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_strategy():
    """docstring 提及分段策略。"""
    import app.parsers.text_parser as mod
    doc = mod.__doc__
    assert "空行" in doc or "paragraph" in doc.lower()


def test_module_docstring_mentions_supported_extensions():
    import app.parsers.text_parser as mod
    doc = mod.__doc__
    assert ".txt" in doc
    assert ".text" in doc


def test_module_docstring_mentions_unsupported_features():
    """docstring 列出明确放弃的功能。"""
    import app.parsers.text_parser as mod
    doc = mod.__doc__
    assert "不" in doc  # 提及"不做"


def test_module_no_silence_unused():
    import app.parsers.text_parser as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 签名深度
# =========================================================================


def test_parse_signature_two_params():
    sig = inspect.signature(TextParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


def test_parse_params_no_defaults():
    sig = inspect.signature(TextParser.parse)
    for p in sig.parameters.values():
        if p.name == "self":
            continue
        assert p.default is inspect.Parameter.empty


def test_parse_return_annotation_document():
    sig = inspect.signature(TextParser.parse)
    assert "Document" in str(sig.return_annotation)


def test_detect_text_source_type_signature():
    sig = inspect.signature(_detect_text_source_type)
    assert set(sig.parameters) == {"path"}


def test_detect_text_source_type_return_annotation_str():
    sig = inspect.signature(_detect_text_source_type)
    assert "str" in str(sig.return_annotation)


def test_split_paragraphs_signature():
    sig = inspect.signature(_split_paragraphs)
    assert set(sig.parameters) == {"text"}


def test_split_paragraphs_return_annotation_list_of_tuples():
    sig = inspect.signature(_split_paragraphs)
    ret = str(sig.return_annotation)
    assert "list" in ret.lower() or "tuple" in ret.lower()


# =========================================================================
# 综合行为
# =========================================================================


def test_parse_idempotent_same_file(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "para1\n\npara2")
    d1 = TextParser().parse(p, _H)
    d2 = TextParser().parse(p, _H)
    assert d1.document_id == d2.document_id
    assert len(d1.elements) == len(d2.elements)


def test_parse_different_hash_different_doc_id(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello")
    d1 = TextParser().parse(p, _H)
    d2 = TextParser().parse(p, _H2)
    assert d1.document_id != d2.document_id


def test_split_paragraphs_then_parse_consistent(tmp_path: Path):
    """split_paragraphs 与 parse 结果一致。"""
    text = "para1\n\npara2"
    p = _write(tmp_path, "x.txt", text)
    doc = TextParser().parse(p, _H)
    splits = _split_paragraphs(text)
    assert len(doc.elements) == len(splits)
    for el, (start_line, content) in zip(doc.elements, splits):
        assert el.content == content
        assert el.source_locator["line"] == start_line


def test_parse_does_not_mutate_input_file(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello\n\nworld")
    before = p.read_text(encoding="utf-8")
    TextParser().parse(p, _H)
    after = p.read_text(encoding="utf-8")
    assert before == after
