"""app/parsers/ipynb_parser.py 边角测试 - 第二轮（Round 78）。

补强 tests/test_parsers_ipynb.py（65）+ tests/test_parsers_ipynb_edges.py（114）
未覆盖的：
- _cell_source_to_text：更多输入类型（set/tuple/generator/list of bool 等）、
  list[str] join 行为、list 中含 None、list of list of str
- _extract_kernel_language：所有 fallback 路径组合、kernelspec/name 包含特殊字符
- _detect_ipynb_source_type：.IPYNB 大写、.Json 拒绝、error code 值、ParserError 类型
- IpynbParser.parse()：markdown cell 多种 sub-element 类型（heading/paragraph/
  list_item/table/blockquote/code_block）、code cell 多行 list source、raw cell 多行、
  cell_index 跨 cell 类型传递、同 cell 多 sub-element 共享 cell_index、
  element_id 连续编号、metadata 字段精确 keys
- ipynb_invalid_json / ipynb_bad_structure / ipynb_unsupported_version 详细路径
- empty_notebook metadata 各字段值
- 模块结构与 __all__、parse 签名
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError
from app.parsers.ipynb_parser import (
    IpynbParser,
    _IPYNB_EXTENSIONS,
    _cell_source_to_text,
    _detect_ipynb_source_type,
    _extract_kernel_language,
)


# ---------- 模块常量 ----------


def test_ipynb_extensions_count_one():
    assert len(_IPYNB_EXTENSIONS) == 1


def test_ipynb_extensions_value():
    assert _IPYNB_EXTENSIONS == (".ipynb",)


def test_ipynb_extensions_is_tuple():
    assert isinstance(_IPYNB_EXTENSIONS, tuple)


def test_ipynb_extensions_lowercase():
    for ext in _IPYNB_EXTENSIONS:
        assert ext == ext.lower()


def test_ipynb_extensions_starts_with_dot():
    for ext in _IPYNB_EXTENSIONS:
        assert ext.startswith(".")


# ---------- _detect_ipynb_source_type 深度 ----------


def test_detect_ipynb_source_type_returns_str_type():
    assert isinstance(_detect_ipynb_source_type(Path("x.ipynb")), str)


def test_detect_ipynb_source_type_value():
    assert _detect_ipynb_source_type(Path("x.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_uppercase():
    assert _detect_ipynb_source_type(Path("X.IPYNB")) == "ipynb"


def test_detect_ipynb_source_type_mixed_case():
    assert _detect_ipynb_source_type(Path("x.IpYnB")) == "ipynb"


def test_detect_ipynb_source_type_double_extension():
    """file.tar.ipynb → suffix 是 .ipynb。"""
    assert _detect_ipynb_source_type(Path("file.tar.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_json_rejected():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("x.json"))


def test_detect_ipynb_source_type_md_rejected():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("x.md"))


def test_detect_ipynb_source_type_txt_rejected():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("x.txt"))


def test_detect_ipynb_source_type_no_suffix_rejected():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("README"))


def test_detect_ipynb_source_type_error_code_value():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("x.json"))
    assert exc.value.code == "unsupported_type"


def test_detect_ipynb_source_type_error_is_parser_error_type():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("x.json"))
    assert isinstance(exc.value, ParserError)


def test_detect_ipynb_source_type_error_details_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("x.docx"))
    assert exc.value.details["suffix"] == ".docx"


def test_detect_ipynb_source_type_error_message_contains_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("x.docx"))
    assert ".docx" in str(exc.value)


# ---------- _cell_source_to_text 深度 ----------


def test_cell_source_to_text_str_passthrough():
    assert _cell_source_to_text("hello") == "hello"


def test_cell_source_to_text_empty_str_returns_empty():
    assert _cell_source_to_text("") == ""


def test_cell_source_to_text_list_of_str_joins():
    assert _cell_source_to_text(["a", "b", "c"]) == "abc"


def test_cell_source_to_text_list_of_str_with_newlines():
    """nbformat 标准：list 中每项已含 \\n。"""
    assert _cell_source_to_text(["line1\n", "line2\n", "line3"]) == "line1\nline2\nline3"


def test_cell_source_to_text_empty_list():
    assert _cell_source_to_text([]) == ""


def test_cell_source_to_text_none_returns_none():
    assert _cell_source_to_text(None) is None


def test_cell_source_to_text_int_returns_none():
    assert _cell_source_to_text(42) is None


def test_cell_source_to_text_float_returns_none():
    assert _cell_source_to_text(3.14) is None


def test_cell_source_to_text_bool_true_returns_none():
    assert _cell_source_to_text(True) is None


def test_cell_source_to_text_bool_false_returns_none():
    assert _cell_source_to_text(False) is None


def test_cell_source_to_text_dict_returns_none():
    assert _cell_source_to_text({"k": "v"}) is None


def test_cell_source_to_text_bytes_returns_none():
    assert _cell_source_to_text(b"hello") is None


def test_cell_source_to_text_list_with_int_items():
    """list 中含 int → 强制 str。"""
    assert _cell_source_to_text([1, 2, 3]) is None


# adoption 契约 §5 注记（2026-08-27）：list 须全为 str 才拼接，含非 str 项 → None。
def test_cell_source_to_text_list_with_none_items():
    """list 中含 None → None（不做 str() 强转）。"""
    assert _cell_source_to_text([None, "x"]) is None


def test_cell_source_to_text_list_with_bool_items():
    """list 中含 bool → None（不做 str() 强转）。"""
    assert _cell_source_to_text([True, False]) is None


def test_cell_source_to_text_list_mixed_types():
    """list 混入 int/float → None（不做 str() 强转）。"""
    assert _cell_source_to_text(["a", 1, "b", 2.5]) is None


def test_cell_source_to_text_returns_str_type():
    assert isinstance(_cell_source_to_text("hello"), str)


def test_cell_source_to_text_returns_str_type_for_list():
    assert isinstance(_cell_source_to_text(["a", "b"]), str)


def test_cell_source_to_text_returns_str_type_for_empty():
    assert isinstance(_cell_source_to_text(""), str)


def test_cell_source_to_text_tuple_input_returns_none():
    """tuple 不是 list → 不被识别 → 返 ''。"""
    assert _cell_source_to_text(("a", "b")) is None


def test_cell_source_to_text_set_input_returns_none():
    """set 不是 list → 返 ''。"""
    assert _cell_source_to_text({"a", "b"}) is None


def test_cell_source_to_text_long_list():
    items = ["line\n"] * 1000
    result = _cell_source_to_text(items)
    assert len(result) == 5000


def test_cell_source_to_text_unicode():
    assert _cell_source_to_text("你好") == "你好"


def test_cell_source_to_text_list_unicode():
    assert _cell_source_to_text(["你好", "世界"]) == "你好世界"


def test_cell_source_to_text_list_with_nested_list():
    """list 中含 nested list → None（不做 str() 强转）。"""
    assert _cell_source_to_text([["a", "b"], "c"]) is None


# ---------- _extract_kernel_language 深度 ----------


def test_extract_kernel_language_kernelspec_language_field():
    md = {"kernelspec": {"language": "python", "name": "python3"}}
    assert _extract_kernel_language(md) == "python"


# adoption 契约 §6 注记（2026-08-27）：kernelspec.name 是内核标识，不参与语言判定；
# 链为 kernelspec.language → language_info.name → 空串。
def test_extract_kernel_language_kernelspec_name_not_a_language():
    md = {"kernelspec": {"name": "python3"}}
    assert _extract_kernel_language(md) == ""


def test_extract_kernel_language_language_info_name_fallback():
    md = {"language_info": {"name": "r"}}
    assert _extract_kernel_language(md) == "r"


def test_extract_kernel_language_empty_metadata_returns_empty():
    assert _extract_kernel_language({}) == ""


def test_extract_kernel_language_kernelspec_empty_dict():
    assert _extract_kernel_language({"kernelspec": {}}) == ""


def test_extract_kernel_language_language_info_empty_dict():
    assert _extract_kernel_language({"language_info": {}}) == ""


def test_extract_kernel_language_kernelspec_language_overrides_name():
    md = {"kernelspec": {"language": "python", "name": "python3"}}
    assert _extract_kernel_language(md) == "python"


def test_extract_kernel_language_kernelspec_language_empty_is_absent():
    md = {"kernelspec": {"language": "", "name": "fallback_name"}}
    assert _extract_kernel_language(md) == ""


def test_extract_kernel_language_kernelspec_language_none_is_absent():
    md = {"kernelspec": {"language": None, "name": "fallback"}}
    assert _extract_kernel_language(md) == ""


def test_extract_kernel_language_all_fields_empty():
    md = {"kernelspec": {"language": "", "name": ""}, "language_info": {"name": ""}}
    assert _extract_kernel_language(md) == ""


def test_extract_kernel_language_returns_str_type():
    md = {"kernelspec": {"language": "python"}}
    assert isinstance(_extract_kernel_language(md), str)


def test_extract_kernel_language_kernelspec_none_language_info_present():
    md = {"kernelspec": None, "language_info": {"name": "julia"}}
    assert _extract_kernel_language(md) == "julia"


def test_extract_kernel_language_special_chars_in_kernel_name_ignored():
    md = {"kernelspec": {"name": "python-c++"}}
    assert _extract_kernel_language(md) == ""


def test_extract_kernel_language_kernelspec_with_only_name_key():
    """kernelspec 仅含 name 不含 language → 空串（name 不参与）。"""
    md = {"kernelspec": {"name": "python3"}}
    assert _extract_kernel_language(md) == ""


def test_extract_kernel_language_language_info_with_only_name():
    md = {"language_info": {"name": "r"}}
    assert _extract_kernel_language(md) == "r"


# ---------- IpynbParser.parse() 错误路径深度 ----------


def _write_nb(tmp_path: Path, name: str, nb: Any) -> Path:
    # adoption 契约 §2 注记（2026-08-27）：版本字段必填——fixture 缺省时补
    # nbformat=4 / nbformat_minor=5；显式传入的非法值不被覆盖（契约测试覆盖）。
    if isinstance(nb, dict):
        nb.setdefault("nbformat", 4)
        nb.setdefault("nbformat_minor", 5)
    f = tmp_path / name
    f.write_text(json.dumps(nb), encoding="utf-8")
    return f


def test_parse_missing_file_raises_file_not_found(tmp_path: Path):
    p = IpynbParser()
    with pytest.raises(ParserError) as exc:
        p.parse(tmp_path / "missing.ipynb", "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_missing_file_details_has_path(tmp_path: Path):
    p = IpynbParser()
    missing = tmp_path / "missing.ipynb"
    with pytest.raises(ParserError) as exc:
        p.parse(missing, "a" * 64)
    assert exc.value.details["path"] == str(missing)


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = IpynbParser()
    f = tmp_path / "f.json"
    f.write_text("{}", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "unsupported_type"


def test_parse_directory_raises_file_not_found(tmp_path: Path):
    """目录 → is_file()=False → file_not_found。"""
    p = IpynbParser()
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(ParserError) as exc:
        p.parse(sub, "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_invalid_json_raises(tmp_path: Path):
    p = IpynbParser()
    f = tmp_path / "f.ipynb"
    f.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "ipynb_invalid_json"


def test_parse_invalid_json_details_has_exception_type(tmp_path: Path):
    p = IpynbParser()
    f = tmp_path / "f.ipynb"
    f.write_text("{not valid", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.details["exception_type"] == "JSONDecodeError"


def test_parse_top_level_list_raises_bad_structure(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", [1, 2, 3])
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_top_level_string_raises_bad_structure(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", "hello")
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_top_level_int_raises_bad_structure(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", 42)
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_top_level_null_raises_bad_structure(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", None)
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_cells_field_dict_raises_bad_structure(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"cells": {"not": "list"}})
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_cells_field_string_raises_bad_structure(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"cells": "not a list"})
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_nbformat_3_raises_unsupported_version(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 3, "cells": []})
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_0_raises_unsupported_version(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 0, "cells": []})
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_1_raises_unsupported_version(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 1, "cells": []})
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "ipynb_unsupported_version"


def test_parse_unsupported_version_details_has_nbformat(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 2, "cells": []})
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.details["nbformat"] == 2


# ---------- parse() 成功路径深度 ----------


def test_parse_returns_document_type(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_correct_source_hash(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    sha = "b" * 64
    doc = p.parse(f, sha)
    assert doc.source_hash == sha


def test_parse_document_id_derived_from_hash(tmp_path: Path):
    from app.parsers.base import make_document_id
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    sha = "c" * 64
    doc = p.parse(f, sha)
    assert doc.document_id == make_document_id(sha)


def test_parse_metadata_has_ipynb_true(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.metadata["ipynb"] is True


def test_parse_metadata_records_nbformat(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "nbformat_minor": 5, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.metadata["nbformat"] == 4


def test_parse_metadata_records_nbformat_minor(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "nbformat_minor": 5, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.metadata["nbformat_minor"] == 5


def test_parse_metadata_records_cell_count(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "raw", "source": "x"}] * 3
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert doc.metadata["cell_count"] == 3


def test_parse_metadata_records_language(tmp_path: Path):
    p = IpynbParser()
    nb = {
        "nbformat": 4,
        "cells": [],
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
    }
    f = _write_nb(tmp_path, "f.ipynb", nb)
    doc = p.parse(f, "a" * 64)
    assert doc.metadata["language"] == "python"


def test_parse_metadata_language_empty_when_no_kernelspec(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.metadata["language"] == ""


def test_parse_metadata_keys_full_set(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "nbformat_minor": 0, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert set(doc.metadata.keys()) == {
        "ipynb", "nbformat", "nbformat_minor", "cell_count", "language"
    }


def test_parse_chunks_empty(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.chunks == []


def test_parse_relations_empty(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.relations == []


def test_parse_errors_empty(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.errors == []


def test_parse_source_type_ipynb(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.source_type == "ipynb"


def test_parse_parser_name_value(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.parser_name == "ipynb"


def test_parse_parser_version_value(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.parser_version == "stdlib/0.1.0"


# ---------- cell 类型 → element 类型深度 ----------


def test_parse_markdown_cell_heading_creates_heading_element(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "markdown", "source": "# Title"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 1


def test_parse_markdown_cell_paragraph_creates_paragraph(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "markdown", "source": "just text"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1


def test_parse_markdown_cell_list_item_creates_list_item(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "markdown", "source": "- item"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1


def test_parse_markdown_cell_table_creates_table_element(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "markdown", "source": "| a | b |\n| --- | --- |\n| 1 | 2 |"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1


def test_parse_markdown_cell_multiple_sub_elements(tmp_path: Path):
    """一个 markdown cell 含 heading + paragraph + list → 3 个 element。"""
    p = IpynbParser()
    cells = [{"cell_type": "markdown", "source": "# Title\nparagraph\n- item"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert len(doc.elements) == 3


def test_parse_code_cell_creates_paragraph_with_code_cell_kind(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "code", "source": "print('hello')"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].metadata["kind"] == "code_cell"


def test_parse_code_cell_includes_language_metadata(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "code", "source": "x"}]
    nb = {
        "nbformat": 4,
        "cells": cells,
        "metadata": {"kernelspec": {"language": "r", "name": "ir"}},
    }
    f = _write_nb(tmp_path, "f.ipynb", nb)
    doc = p.parse(f, "a" * 64)
    assert doc.elements[0].metadata["language"] == "r"


def test_parse_raw_cell_creates_paragraph_with_raw_cell_kind(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "raw", "source": "raw text"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert doc.elements[0].metadata["kind"] == "raw_cell"


def test_parse_raw_cell_no_language_in_metadata(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "raw", "source": "raw text"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert "language" not in doc.elements[0].metadata


# ---------- cell_index 跨 cell 类型 ----------


def test_parse_cell_index_zero_first_cell(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "raw", "source": "x"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert doc.elements[0].source_locator["cell_index"] == 0


def test_parse_cell_index_increments_across_types(tmp_path: Path):
    p = IpynbParser()
    cells = [
        {"cell_type": "raw", "source": "raw1"},
        {"cell_type": "code", "source": "code1"},
        {"cell_type": "raw", "source": "raw2"},
    ]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    idxs = [e.source_locator["cell_index"] for e in doc.elements]
    assert idxs == [0, 1, 2]


def test_parse_same_cell_index_for_markdown_sub_elements(tmp_path: Path):
    """一个 markdown cell 含多个 sub-element → 共享 cell_index。"""
    p = IpynbParser()
    cells = [{"cell_type": "markdown", "source": "# H1\nparagraph\n- item"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    idxs = [e.source_locator["cell_index"] for e in doc.elements]
    assert all(i == 0 for i in idxs)


def test_parse_element_id_increments_across_cells(tmp_path: Path):
    p = IpynbParser()
    cells = [
        {"cell_type": "raw", "source": "a"},
        {"cell_type": "raw", "source": "b"},
        {"cell_type": "raw", "source": "c"},
    ]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    ids = [e.element_id for e in doc.elements]
    for i in range(1, len(ids)):
        assert ids[i] > ids[i - 1]


def test_parse_element_id_format_zero_pad(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "raw", "source": "x"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    eid = doc.elements[0].element_id
    parts = eid.split("::")
    assert parts[1].startswith("e")
    num = parts[1][1:]
    assert len(num) == 4
    assert num == "0000"


def test_parse_element_parent_id_always_none(tmp_path: Path):
    p = IpynbParser()
    cells = [
        {"cell_type": "markdown", "source": "# T\npara"},
        {"cell_type": "code", "source": "x"},
        {"cell_type": "raw", "source": "y"},
    ]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    for e in doc.elements:
        assert e.parent_id is None


def test_parse_element_confidence_strictly_095(tmp_path: Path):
    p = IpynbParser()
    cells = [
        {"cell_type": "markdown", "source": "# T"},
        {"cell_type": "code", "source": "x"},
        {"cell_type": "raw", "source": "y"},
    ]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    for e in doc.elements:
        assert e.confidence == 0.95


def test_parse_code_cell_content_preserved(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "code", "source": "  print('x')  \n"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert doc.elements[0].content == "  print('x')  \n"


# adoption 契约 §5/§8 注记（2026-08-27）：source 非法输入归一为 None（跳过 cell +
# ipynb_bad_cell）；code/raw 正文保留原始缩进换行（strip 仅判空）；locator 补 line=1。
# 以下原快照期望已按定稿契约改写。
def test_parse_raw_cell_content_preserved(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "raw", "source": "  raw content  "}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert doc.elements[0].content == '  raw content  '


def test_parse_code_cell_multiline_source_list(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "code", "source": ["line1\n", "line2\n", "line3"]}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert "line1" in doc.elements[0].content
    assert "line3" in doc.elements[0].content


def test_parse_markdown_cell_locator_carries_section_path(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "markdown", "source": "# Title\nparagraph"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    para = [e for e in doc.elements if e.type == "paragraph"][0]
    assert para.source_locator["section_path"] == "Title"


# ---------- warning 路径深度 ----------


def test_parse_empty_code_cell_emits_warning(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "code", "source": ""}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert any(w.code == "ipynb_empty_code_cell" for w in doc.warnings)


def test_parse_whitespace_only_code_cell_emits_warning(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "code", "source": "   \n  "}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert any(w.code == "ipynb_empty_code_cell" for w in doc.warnings)


def test_parse_empty_code_cell_warning_has_cell_index(tmp_path: Path):
    p = IpynbParser()
    cells = [
        {"cell_type": "raw", "source": "first"},
        {"cell_type": "code", "source": ""},
    ]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    for w in doc.warnings:
        if w.code == "ipynb_empty_code_cell":
            assert w.details["cell_index"] == 1


def test_parse_unknown_cell_type_emits_warning(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "unknown_type", "source": "x"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert any(w.code == "ipynb_unknown_cell_type" for w in doc.warnings)


def test_parse_unknown_cell_type_warning_has_cell_type(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "weird", "source": "x"}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    for w in doc.warnings:
        if w.code == "ipynb_unknown_cell_type":
            assert w.details["cell_type"] == "weird"


def test_parse_cell_not_dict_emits_warning(tmp_path: Path):
    p = IpynbParser()
    cells = ["not a dict"]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    assert any(w.code == "ipynb_bad_cell" for w in doc.warnings)


def test_parse_cell_not_dict_warning_has_cell_index(tmp_path: Path):
    p = IpynbParser()
    cells = [
        {"cell_type": "raw", "source": "ok"},
        "not a dict",
    ]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    for w in doc.warnings:
        if w.code == "ipynb_bad_cell":
            assert w.details["cell_index"] == 1


def test_parse_empty_notebook_emits_no_content_warning(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


def test_parse_raw_empty_silently_skipped_no_warning(tmp_path: Path):
    p = IpynbParser()
    cells = [{"cell_type": "raw", "source": ""}]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    # raw 空 → 静默跳过；总 warning 应当是 no_content
    codes = [w.code for w in doc.warnings]
    # 不应有 ipynb_empty_code_cell（raw 不是 code）
    assert "ipynb_empty_code_cell" not in codes


def test_parse_warning_records_have_reason_string(tmp_path: Path):
    p = IpynbParser()
    cells = ["not a dict"]
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "cells": cells})
    doc = p.parse(f, "a" * 64)
    for w in doc.warnings:
        assert isinstance(w.reason, str)
        assert len(w.reason) > 0


# ---------- nbformat 边界 ----------


def test_parse_nbformat_missing_rejected_as_bad_structure(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：无 nbformat 字段 → ipynb_bad_structure。

    原快照语义为"缺失视为支持"；helper 现会补默认，故直写文件。
    """
    p = IpynbParser()
    f = tmp_path / "f.ipynb"
    f.write_text(json.dumps({"cells": [], "nbformat_minor": 5}), encoding="utf-8")
    with pytest.raises(ParserError) as ei:
        p.parse(f, "a" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_nbformat_4_minor_0(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4, "nbformat_minor": 0, "cells": []})
    doc = p.parse(f, "a" * 64)
    assert doc.metadata["nbformat"] == 4
    assert doc.metadata["nbformat_minor"] == 0


def test_parse_nbformat_5_unsupported(tmp_path: Path):
    """adoption 契约 §1（2026-08-27）：nbformat=5 → ipynb_unsupported_version。"""
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 5, "cells": []})
    with pytest.raises(ParserError) as ei:
        p.parse(f, "a" * 64)
    assert ei.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_minor_missing_rejected(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：nbformat_minor 缺失 → ipynb_bad_structure。"""
    p = IpynbParser()
    f = tmp_path / "f.ipynb"
    f.write_text(json.dumps({"nbformat": 4, "cells": []}), encoding="utf-8")
    with pytest.raises(ParserError) as ei:
        p.parse(f, "a" * 64)
    assert ei.value.code == "ipynb_bad_structure"
    assert ei.value.details["field"] == "nbformat_minor"


def test_parse_cells_missing_treated_as_empty(tmp_path: Path):
    p = IpynbParser()
    f = _write_nb(tmp_path, "f.ipynb", {"nbformat": 4})
    doc = p.parse(f, "a" * 64)
    # 无 cells → 视为空，cell_count=0
    assert doc.metadata["cell_count"] == 0


def test_parse_metadata_none_does_not_crash(tmp_path: Path):
    p = IpynbParser()
    nb = {"nbformat": 4, "cells": [], "metadata": None}
    f = _write_nb(tmp_path, "f.ipynb", nb)
    doc = p.parse(f, "a" * 64)
    assert doc.metadata["language"] == ""


# ---------- 模块结构 ----------


def test_module_imports_json():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "json")


def test_module_imports_path():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "Path")


def test_module_imports_any():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "Any")


def test_module_imports_document():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "Document")


def test_module_imports_element():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser_base():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "ParserError")


def test_module_imports_make_document_id():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "make_document_id")


def test_module_imports_markdown_parser():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "MarkdownParser")


def test_module_has_all():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "__all__")


def test_module_all_contains_ipynb_parser():
    import app.parsers.ipynb_parser as mod
    assert "IpynbParser" in mod.__all__


def test_module_all_is_list():
    import app.parsers.ipynb_parser as mod
    assert isinstance(mod.__all__, list)


def test_ipynb_parser_inherits_parser():
    p = IpynbParser()
    assert isinstance(p, Parser)


def test_ipynb_parser_name_is_str():
    p = IpynbParser()
    assert isinstance(p.name, str)


def test_ipynb_parser_version_is_str():
    p = IpynbParser()
    assert isinstance(p.version, str)


def test_ipynb_parser_parse_callable():
    p = IpynbParser()
    assert callable(p.parse)


def test_ipynb_parser_parse_signature():
    """parse 签名: (self, path, source_hash)。"""
    import inspect
    sig = inspect.signature(IpynbParser.parse)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "path" in params
    assert "source_hash" in params
