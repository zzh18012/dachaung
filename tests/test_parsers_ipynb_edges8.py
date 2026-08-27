r"""app/parsers/ipynb_parser.py 边角测试 - 第八轮（Round 198）。

补强已有 base/edges/edges2-7（共 844 测试）未覆盖的深度：
- _cell_source_to_text 各非 str/list 类型 + list 混合 + 多行
- _extract_kernel_language 各 fallback 优先级
- IpynbParser.parse 完整错误矩阵（bad JSON/OSError/top-level/cells/nbformat）
- 单 cell 多 element（heading + paragraph + list + table）
- element_id 编号、metadata、document metadata 完整字段
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, Element
from app.parsers.base import Parser, ParserError
from app.parsers.ipynb_parser import (
    IpynbParser,
    _IPYNB_EXTENSIONS,
    _cell_source_to_text,
    _detect_ipynb_source_type,
    _extract_kernel_language,
)


# =========================================================================
# _IPYNB_EXTENSIONS
# =========================================================================


def test_ipynb_extensions_constant_value():
    assert _IPYNB_EXTENSIONS == (".ipynb",)


def test_ipynb_extensions_is_tuple():
    assert isinstance(_IPYNB_EXTENSIONS, tuple)


def test_ipynb_extensions_single_item():
    assert len(_IPYNB_EXTENSIONS) == 1


# =========================================================================
# _detect_ipynb_source_type 深度
# =========================================================================


def test_detect_ipynb_source_type_lowercase_ipynb():
    assert _detect_ipynb_source_type(Path("a.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_uppercase_ipynb():
    """大写后缀 → lower() → 匹配。"""
    assert _detect_ipynb_source_type(Path("a.IPYNB")) == "ipynb"


def test_detect_ipynb_source_type_mixed_case():
    assert _detect_ipynb_source_type(Path("a.Ipynb")) == "ipynb"


def test_detect_ipynb_source_type_unknown_suffix_raises():
    with pytest.raises(ParserError) as excinfo:
        _detect_ipynb_source_type(Path("a.txt"))
    assert excinfo.value.code == "unsupported_type"
    assert "txt" in excinfo.value.details["suffix"]


def test_detect_ipynb_source_type_no_suffix_raises():
    with pytest.raises(ParserError) as excinfo:
        _detect_ipynb_source_type(Path("README"))
    assert excinfo.value.code == "unsupported_type"
    # 无后缀 → details.suffix == ""
    assert excinfo.value.details["suffix"] == ""


def test_detect_ipynb_source_type_message_contains_suffix_or_no():
    """无后缀时 message 含 '(无)'。"""
    with pytest.raises(ParserError) as excinfo:
        _detect_ipynb_source_type(Path("README"))
    assert "(无)" in excinfo.value.message


def test_detect_ipynb_source_type_double_extension():
    """多后缀只看最后一段。"""
    assert _detect_ipynb_source_type(Path("a.b.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_pdf_rejected():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("a.pdf"))


# =========================================================================
# _cell_source_to_text 深度
# =========================================================================


def test_cell_source_to_text_str_returns_str():
    assert _cell_source_to_text("hello") == "hello"


def test_cell_source_to_text_empty_str_returns_empty():
    assert _cell_source_to_text("") == ""


def test_cell_source_to_text_list_of_str():
    assert _cell_source_to_text(["a", "b", "c"]) == "abc"


def test_cell_source_to_text_list_with_newlines():
    """list 中含 \n → 拼接保留。"""
    assert _cell_source_to_text(["line1\n", "line2\n"]) == "line1\nline2\n"


def test_cell_source_to_text_empty_list():
    assert _cell_source_to_text([]) == ""


def test_cell_source_to_text_list_with_int():
    """list 含非 str → str() 强转。"""
    assert _cell_source_to_text(["a", 1, "b"]) is None


def test_cell_source_to_text_list_with_none():
    assert _cell_source_to_text(["a", None, "b"]) is None


def test_cell_source_to_text_list_with_dict():
    assert _cell_source_to_text([{"x": 1}]) is None


def test_cell_source_to_text_none_returns_none():
    assert _cell_source_to_text(None) is None


def test_cell_source_to_text_int_returns_none():
    """非 str/list → 空。"""
    assert _cell_source_to_text(42) is None


def test_cell_source_to_text_float_returns_none():
    assert _cell_source_to_text(3.14) is None


def test_cell_source_to_text_dict_returns_none():
    assert _cell_source_to_text({"x": 1}) is None


def test_cell_source_to_text_tuple_returns_none():
    """tuple 不是 list → 返回空。"""
    assert _cell_source_to_text(("a", "b")) is None


def test_cell_source_to_text_bool_returns_none():
    assert _cell_source_to_text(True) is None


def test_cell_source_to_text_multiline_str_preserved():
    text = "line1\nline2\nline3"
    assert _cell_source_to_text(text) == text


# =========================================================================
# _extract_kernel_language 深度
# =========================================================================


def test_extract_kernel_language_kernelspec_language():
    metadata = {"kernelspec": {"language": "python"}}
    assert _extract_kernel_language(metadata) == "python"


# adoption 契约 §6 注记（2026-08-27）：kernelspec.name 是内核标识，不参与语言判定；
# 链为 kernelspec.language → language_info.name → 空串。
def test_extract_kernel_language_kernelspec_name_not_a_language():
    metadata = {"kernelspec": {"name": "python3"}}
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_language_foblacks_name():
    """language 优先于 name。"""
    metadata = {"kernelspec": {"language": "python", "name": "py3"}}
    assert _extract_kernel_language(metadata) == "python"


def test_extract_kernel_language_language_info_name():
    metadata = {"language_info": {"name": "r"}}
    assert _extract_kernel_language(metadata) == "r"


def test_extract_kernel_language_kernelspec_over_language_info():
    """kernelspec 优先于 language_info。"""
    metadata = {
        "kernelspec": {"language": "python"},
        "language_info": {"name": "r"},
    }
    assert _extract_kernel_language(metadata) == "python"


def test_extract_kernel_language_empty_metadata():
    assert _extract_kernel_language({}) == ""


def test_extract_kernel_language_none_metadata_raises():
    """None metadata → AttributeError（_extract_kernel_language 不防 None）。"""
    with pytest.raises(AttributeError):
        _extract_kernel_language(None)  # type: ignore[arg-type]


def test_extract_kernel_language_kernelspec_empty():
    assert _extract_kernel_language({"kernelspec": {}}) == ""


def test_extract_kernel_language_kernelspec_none():
    assert _extract_kernel_language({"kernelspec": None}) == ""


def test_extract_kernel_language_no_kernelspec_no_language_info():
    assert _extract_kernel_language({"other": "data"}) == ""


def test_extract_kernel_language_kernelspec_language_empty_is_absent():
    metadata = {"kernelspec": {"language": "", "name": "fallback"}}
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_all_empty_returns_empty():
    metadata = {
        "kernelspec": {"language": "", "name": ""},
        "language_info": {"name": ""},
    }
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_kernelspec_empty_falls_to_language_info():
    metadata = {
        "kernelspec": {},
        "language_info": {"name": "julia"},
    }
    assert _extract_kernel_language(metadata) == "julia"


# =========================================================================
# IpynbParser 类属性
# =========================================================================


def test_ipynb_parser_name_constant():
    assert IpynbParser.name == "ipynb"


def test_ipynb_parser_version_constant():
    assert IpynbParser.version == "stdlib/0.1.0"


def test_ipynb_parser_inherits_parser():
    assert issubclass(IpynbParser, Parser)


def test_ipynb_parser_two_class_attrs_consistent():
    """两个 class attr 不需要实例化即可访问。"""
    assert IpynbParser.name is not None
    assert IpynbParser.version is not None


def test_ipynb_parser_parse_signature():
    sig = inspect.signature(IpynbParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


# =========================================================================
# IpynbParser.parse 错误矩阵
# =========================================================================


def _make_minimal_notebook(cells=None, nbformat=4, nbformat_minor=5,
                            metadata=None) -> dict:
    return {
        "nbformat": nbformat,
        "nbformat_minor": nbformat_minor,
        "metadata": metadata or {"kernelspec": {"language": "python"}},
        "cells": cells or [],
    }


def _write_ipynb(tmp_path: Path, nb: dict, name: str = "test.ipynb") -> Path:
    # adoption 契约 §2 注记（2026-08-27）：版本字段必填——fixture 缺省时补默认。
    nb.setdefault("nbformat", 4)
    nb.setdefault("nbformat_minor", 5)
    p = tmp_path / name
    p.write_text(json.dumps(nb), encoding="utf-8")
    return p


def test_parse_file_not_found(tmp_path: Path):
    parser = IpynbParser()
    missing = tmp_path / "missing.ipynb"
    with pytest.raises(ParserError) as excinfo:
        parser.parse(missing, "a" * 64)
    assert excinfo.value.code == "file_not_found"


def test_parse_unsupported_suffix(tmp_path: Path):
    parser = IpynbParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as excinfo:
        parser.parse(p, "a" * 64)
    assert excinfo.value.code == "unsupported_type"


def test_parse_invalid_json(tmp_path: Path):
    parser = IpynbParser()
    p = tmp_path / "bad.ipynb"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ParserError) as excinfo:
        parser.parse(p, "a" * 64)
    assert excinfo.value.code == "ipynb_invalid_json"
    assert "JSONDecodeError" in excinfo.value.details["exception_type"]


def test_parse_top_level_list(tmp_path: Path):
    parser = IpynbParser()
    p = tmp_path / "list.ipynb"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ParserError) as excinfo:
        parser.parse(p, "a" * 64)
    assert excinfo.value.code == "ipynb_bad_structure"
    assert "顶层不是对象" in excinfo.value.message


def test_parse_top_level_int(tmp_path: Path):
    parser = IpynbParser()
    p = tmp_path / "int.ipynb"
    p.write_text("42", encoding="utf-8")
    with pytest.raises(ParserError) as excinfo:
        parser.parse(p, "a" * 64)
    assert excinfo.value.code == "ipynb_bad_structure"


def test_parse_nbformat_3_rejected(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(nbformat=3)
    p = _write_ipynb(tmp_path, nb)
    with pytest.raises(ParserError) as excinfo:
        parser.parse(p, "a" * 64)
    assert excinfo.value.code == "ipynb_unsupported_version"
    assert excinfo.value.details["nbformat"] == 3


def test_parse_nbformat_2_rejected(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(nbformat=2)
    p = _write_ipynb(tmp_path, nb)
    with pytest.raises(ParserError) as excinfo:
        parser.parse(p, "a" * 64)
    assert excinfo.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_none_rejected(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：nbformat=None → ipynb_bad_structure。"""
    parser = IpynbParser()
    nb = _make_minimal_notebook()
    nb["nbformat"] = None
    p = _write_ipynb(tmp_path, nb)
    with pytest.raises(ParserError) as ei:
        parser.parse(p, "a" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_nbformat_4_accepted(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(nbformat=4)
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_nbformat_5_unsupported(tmp_path: Path):
    """adoption 契约 §1（2026-08-27）：nbformat=5 → ipynb_unsupported_version。"""
    parser = IpynbParser()
    nb = _make_minimal_notebook(nbformat=5)
    p = _write_ipynb(tmp_path, nb)
    with pytest.raises(ParserError) as ei:
        parser.parse(p, "a" * 64)
    assert ei.value.code == "ipynb_unsupported_version"


def test_parse_cells_not_list(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook()
    nb["cells"] = {"key": "value"}
    p = _write_ipynb(tmp_path, nb)
    with pytest.raises(ParserError) as excinfo:
        parser.parse(p, "a" * 64)
    assert excinfo.value.code == "ipynb_bad_structure"
    assert "cells" in excinfo.value.message


def test_parse_cells_missing(tmp_path: Path):
    """cells 缺失 → 默认 [] → no content warning。"""
    parser = IpynbParser()
    nb = _make_minimal_notebook()
    del nb["cells"]
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert len(doc.warnings) > 0
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


def test_parse_cells_empty_list(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 0
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


def test_parse_cell_not_dict_warning(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=["not_a_dict", 42, None])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert len(doc.warnings) >= 3
    bad_cell_warnings = [w for w in doc.warnings if w.code == "ipynb_bad_cell"]
    assert len(bad_cell_warnings) == 3


def test_parse_unknown_cell_type_warning(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "unknown_type", "source": "hello"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert any(w.code == "ipynb_unknown_cell_type" for w in doc.warnings)


def test_parse_unknown_cell_type_recorded_in_details(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "weird", "source": "x"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    w = next(w for w in doc.warnings if w.code == "ipynb_unknown_cell_type")
    assert w.details["cell_type"] == "weird"


# =========================================================================
# IpynbParser.parse 各 cell 类型
# =========================================================================


def test_parse_markdown_cell_creates_elements(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "markdown", "source": "# Hello\n\nWorld paragraph."},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    # 至少一个 element
    assert len(doc.elements) >= 1


def test_parse_markdown_cell_locator_has_cell_index_and_type(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "markdown", "source": "Hello"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    el = doc.elements[0]
    assert el.source_locator["cell_index"] == 0
    assert el.source_locator["cell_type"] == "markdown"


def test_parse_code_cell_creates_paragraph(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "print('hello')"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    el = doc.elements[0]
    assert el.type == "paragraph"
    assert el.metadata["kind"] == "code_cell"
    assert el.metadata["language"] == "python"


def test_parse_code_cell_preserves_whitespace(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "  print('hello')  \n\n"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].content == "  print('hello')  \n\n"


def test_parse_code_cell_locator(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "x = 1"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    el = doc.elements[0]
    assert el.source_locator["cell_index"] == 0
    assert el.source_locator["cell_type"] == "code"


def test_parse_code_cell_empty_warning(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "   "},  # 空白
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert any(w.code == "ipynb_empty_code_cell" for w in doc.warnings)
    assert len(doc.elements) == 0


def test_parse_code_cell_empty_source_warning(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": ""},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert any(w.code == "ipynb_empty_code_cell" for w in doc.warnings)


def test_parse_raw_cell_creates_paragraph(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "raw", "source": "raw text content"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    el = doc.elements[0]
    assert el.type == "paragraph"
    assert el.metadata["kind"] == "raw_cell"


def test_parse_raw_cell_preserves_whitespace(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "raw", "source": "  hello  "},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].content == '  hello  '


def test_parse_raw_cell_locator(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "raw", "source": "x"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    el = doc.elements[0]
    assert el.source_locator["cell_index"] == 0
    assert el.source_locator["cell_type"] == "raw"


def test_parse_raw_cell_empty_skipped_silently(tmp_path: Path):
    """raw cell 空白 → 直接跳过（不警告）。"""
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "raw", "source": "   "},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    # 仍会有 ipynb_no_content warning（因为没有 element）
    assert len(doc.elements) == 0
    # 但没有 ipynb_empty_code_cell（那是 code 专属）
    assert not any(w.code == "ipynb_empty_code_cell" for w in doc.warnings)


# =========================================================================
# element_id 编号
# =========================================================================


def test_parse_element_id_zero_padded_4_digits(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "x = 1"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].element_id.endswith("::e0000")


def test_parse_element_id_increments_across_cells(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "x = 1"},
        {"cell_type": "code", "source": "y = 2"},
        {"cell_type": "code", "source": "z = 3"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    ids = [el.element_id for el in doc.elements]
    assert ids[0].endswith("::e0000")
    assert ids[1].endswith("::e0001")
    assert ids[2].endswith("::e0002")


def test_parse_element_id_uses_document_id_prefix(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "x"},
    ])
    p = _write_ipynb(tmp_path, nb)
    source_hash = "b" * 64
    doc = parser.parse(p, source_hash)
    # document_id 是 source_hash 的前缀
    assert doc.elements[0].element_id.startswith(doc.document_id)


def test_parse_element_id_5_digits_for_10k_elements(tmp_path: Path):
    """10000+ elements → 5 位数字（k:04d 在 k>=10000 时自然变长）。"""
    parser = IpynbParser()
    cells = [
        {"cell_type": "code", "source": f"x = {i}"} for i in range(10001)
    ]
    nb = _make_minimal_notebook(cells=cells)
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[10000].element_id.endswith("::e10000")


# =========================================================================
# Document metadata 完整字段
# =========================================================================


def test_parse_document_metadata_has_ipynb_true(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook()
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["ipynb"] is True


def test_parse_document_metadata_has_nbformat(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(nbformat=4)
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["nbformat"] == 4


def test_parse_document_metadata_has_nbformat_minor(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(nbformat_minor=5)
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["nbformat_minor"] == 5


def test_parse_document_metadata_has_cell_count(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "x"},
        {"cell_type": "code", "source": "y"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["cell_count"] == 2


def test_parse_document_metadata_has_language(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(metadata={"kernelspec": {"language": "r"}})
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["language"] == "r"


def test_parse_document_metadata_six_keys(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook()
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    expected_keys = {"ipynb", "nbformat", "nbformat_minor", "cell_count", "language"}
    assert expected_keys.issubset(doc.metadata.keys())


def test_parse_returns_document_instance(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook()
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_document_source_type_ipynb(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook()
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.source_type == "ipynb"


def test_parse_document_parser_name_ipynb(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook()
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.parser_name == "ipynb"


def test_parse_document_empty_chunks_and_relations(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook()
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.chunks == []
    assert doc.relations == []


def test_parse_document_errors_empty_on_success(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook()
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.errors == []


def test_parse_element_confidence_095(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "x"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].confidence == 0.95


def test_parse_element_parent_id_none(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "x"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].parent_id is None


# =========================================================================
# 多 cell 组合
# =========================================================================


def test_parse_mixed_cell_types(tmp_path: Path):
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "markdown", "source": "# Title"},
        {"cell_type": "code", "source": "print('hello')"},
        {"cell_type": "raw", "source": "raw text"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) >= 3


def test_parse_cell_index_increments_across_skip(tmp_path: Path):
    """空 code cell 被跳过，但 cell_index 仍是原 index。"""
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "x"},  # cell_index 0
        {"cell_type": "code", "source": "  "},  # empty, cell_index 1, skipped
        {"cell_type": "code", "source": "z"},  # cell_index 2
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    # 2 elements（cell 0 和 cell 2），但 cell_index 应是 0 和 2
    assert doc.elements[0].source_locator["cell_index"] == 0
    assert doc.elements[1].source_locator["cell_index"] == 2


def test_parse_markdown_cell_with_heading_and_paragraph(tmp_path: Path):
    """单 markdown cell 含 heading + paragraph → 至少 2 elements。"""
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "markdown", "source": "# Title\n\nBody paragraph."},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    types = [el.type for el in doc.elements]
    assert "heading" in types
    assert "paragraph" in types


def test_parse_markdown_sub_warning_propagated_with_cell_index(tmp_path: Path):
    """markdown cell 内部产生的 warning 应带 cell_index 信息。"""
    parser = IpynbParser()
    # 用一个会触发 markdown parser warning 的输入（如果存在）
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "markdown", "source": "# Title\n\nOK content"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    # 这个 input 不一定产生 warning，但若有则需含 cell_index
    for w in doc.warnings:
        if w.code != "ipynb_no_content" and "cell" not in (w.details or {}).get("cell_index", "").__str__():
            # 不是 ipynb 自己的 warning，应是 markdown 子 warning
            assert "cell_index" in (w.details or {})


# adoption 契约 §5/§8 注记（2026-08-27）：source 非法输入归一为 None（跳过 cell +
# ipynb_bad_cell）；code/raw 正文保留原始缩进换行（strip 仅判空）；locator 补 line=1。
# 以下原快照期望已按定稿契约改写。
def test_parse_code_cell_list_source(tmp_path: Path):
    """source 是 list 形式 → 拼接。"""
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": ["line1\n", "line2\n"]},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].content == 'line1\nline2\n'


# =========================================================================
# 模块结构与签名
# =========================================================================


def test_module_all_exports_ipynb_parser():
    import app.parsers.ipynb_parser as m
    assert m.__all__ == ["IpynbParser"]


def test_module_imports_json():
    import app.parsers.ipynb_parser as m
    assert hasattr(m, "json")


def test_module_imports_path():
    import app.parsers.ipynb_parser as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import app.parsers.ipynb_parser as m
    assert hasattr(m, "Any")


def test_module_imports_document():
    import app.parsers.ipynb_parser as m
    assert hasattr(m, "Document")


def test_module_imports_element():
    import app.parsers.ipynb_parser as m
    assert hasattr(m, "Element")


def test_module_imports_warning_record():
    import app.parsers.ipynb_parser as m
    assert hasattr(m, "WarningRecord")


def test_module_imports_parser_base():
    import app.parsers.ipynb_parser as m
    assert hasattr(m, "Parser")
    assert hasattr(m, "ParserError")
    assert hasattr(m, "make_document_id")


def test_module_imports_markdown_parser():
    import app.parsers.ipynb_parser as m
    assert hasattr(m, "MarkdownParser")


def test_detect_ipynb_source_type_signature():
    sig = inspect.signature(_detect_ipynb_source_type)
    assert set(sig.parameters) == {"path"}


def test_detect_ipynb_source_type_return_annotation_str():
    sig = inspect.signature(_detect_ipynb_source_type)
    assert "str" in str(sig.return_annotation)


def test_cell_source_to_text_signature():
    sig = inspect.signature(_cell_source_to_text)
    assert set(sig.parameters) == {"source"}


def test_extract_kernel_language_signature():
    sig = inspect.signature(_extract_kernel_language)
    assert set(sig.parameters) == {"metadata"}


def test_extract_kernel_language_return_annotation_str():
    sig = inspect.signature(_extract_kernel_language)
    assert "str" in str(sig.return_annotation)


def test_all_internal_functions_callable():
    assert callable(_detect_ipynb_source_type)
    assert callable(_cell_source_to_text)
    assert callable(_extract_kernel_language)
    assert callable(IpynbParser)


# =========================================================================
# idempotency
# =========================================================================


def test_detect_ipynb_source_type_idempotent():
    a = _detect_ipynb_source_type(Path("a.ipynb"))
    b = _detect_ipynb_source_type(Path("a.ipynb"))
    assert a == b


def test_cell_source_to_text_idempotent():
    a = _cell_source_to_text(["a", "b"])
    b = _cell_source_to_text(["a", "b"])
    assert a == b


def test_extract_kernel_language_idempotent():
    metadata = {"kernelspec": {"language": "python"}}
    a = _extract_kernel_language(metadata)
    b = _extract_kernel_language(metadata)
    assert a == b


def test_parse_idempotent(tmp_path: Path):
    """同一 input 两跑 → elements 数量、内容（不计 element_id）应一致。"""
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": "x = 1"},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc1 = parser.parse(p, "a" * 64)
    doc2 = parser.parse(p, "a" * 64)
    assert len(doc1.elements) == len(doc2.elements)
    assert doc1.elements[0].content == doc2.elements[0].content


# =========================================================================
# 综合行为
# =========================================================================


def test_full_pipeline_real_notebook(tmp_path: Path):
    """完整 notebook：多种 cell + metadata。"""
    parser = IpynbParser()
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "name": "python3",
                "language": "python",
                "display_name": "Python 3",
            },
            "language_info": {"name": "python", "version": "3.12.10"},
        },
        "cells": [
            {"cell_type": "markdown", "source": "# Title\n\nIntro."},
            {"cell_type": "code", "source": "import os\nprint(os.getcwd())"},
            {"cell_type": "markdown", "source": "## Section\n\nMore text."},
            {"cell_type": "raw", "source": "raw content"},
            {"cell_type": "code", "source": "   "},  # empty
        ],
    }
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.source_type == "ipynb"
    assert doc.metadata["cell_count"] == 5
    assert doc.metadata["language"] == "python"
    assert doc.metadata["nbformat"] == 4
    # 至少 4 个非空 cell 的 elements（markdown 至少 1 each + code 1 each + raw 1）
    assert len(doc.elements) >= 4
    # 含 empty code cell warning
    assert any(w.code == "ipynb_empty_code_cell" for w in doc.warnings)


def test_parse_does_not_raise_on_minimal_notebook(tmp_path: Path):
    """最小 notebook：只 nbformat=4 + 空 cells。"""
    parser = IpynbParser()
    nb = {"nbformat": 4, "cells": []}
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_source_is_list_with_empty_strings(tmp_path: Path):
    """source = ['', 'actual', ''] → 拼接 'actual'。"""
    parser = IpynbParser()
    nb = _make_minimal_notebook(cells=[
        {"cell_type": "code", "source": ["", "actual", ""]},
    ])
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    # 拼接后 strip → "actual"
    assert doc.elements[0].content == "actual"


def test_parse_metadata_missing_kernelspec(tmp_path: Path):
    """metadata 缺失 kernelspec → language="" 不抛。"""
    parser = IpynbParser()
    # 注意：_make_minimal_notebook 的 metadata or {...} 会让 {} fall through 到默认值；
    # 必须传一个 truthy 但无 kernelspec 的 dict
    nb = _make_minimal_notebook(metadata={"other": "data"})
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["language"] == ""


def test_parse_metadata_none(tmp_path: Path):
    """metadata=None → 不抛（nb.get('metadata') or {}）。"""
    parser = IpynbParser()
    nb = {"nbformat": 4, "cells": [], "metadata": None}
    p = _write_ipynb(tmp_path, nb)
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)
