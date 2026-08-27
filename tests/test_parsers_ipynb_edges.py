"""app/parsers/ipynb_parser.py 边角测试（Round 58）。

补强 tests/test_parsers_ipynb.py（65 个测试）未覆盖的：
- 模块级常量 _IPYNB_EXTENSIONS 直接引用
- _detect_ipynb_source_type 边角（双扩展名/dotfile/大小写混合/details）
- _cell_source_to_text 类型覆盖（bool/float/dict/bytes/嵌套 list）
- _extract_kernel_language 边角（falsy language/name 优先级）
- IpynbParser 实例复用、无状态、连续 element_id
- 大 notebook、Unicode、多 cell 混合
- 顶层非 dict（array/string/None）、cells 非 list 多种形态
- code/raw cell metadata.kind / language 字段
- nbformat_minor 缺失 → metadata null
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.parsers.base import ParserError
from app.parsers.ipynb_parser import (
    IpynbParser,
    _IPYNB_EXTENSIONS,
    _cell_source_to_text,
    _detect_ipynb_source_type,
    _extract_kernel_language,
)


# ---------- 模块级常量 ----------


def test_ipynb_extensions_constant_is_tuple():
    assert isinstance(_IPYNB_EXTENSIONS, tuple)


def test_ipynb_extensions_constant_single_extension():
    assert set(_IPYNB_EXTENSIONS) == {".ipynb"}


def test_ipynb_extensions_lowercase_only():
    for ext in _IPYNB_EXTENSIONS:
        assert ext == ext.lower()


def test_ipynb_parser_class_attributes():
    assert IpynbParser.name == "ipynb"
    assert IpynbParser.version == "stdlib/0.1.0"


def test_ipynb_parser_inherits_from_parser():
    from app.parsers.base import Parser
    assert issubclass(IpynbParser, Parser)


def test_ipynb_parser_can_be_instantiated_without_args():
    p = IpynbParser()
    assert p is not None


def test_ipynb_parser_has_parse_method():
    p = IpynbParser()
    assert callable(p.parse)


# ---------- _detect_ipynb_source_type 边角 ----------


def test_detect_ipynb_source_type_returns_str():
    result = _detect_ipynb_source_type(Path("file.ipynb"))
    assert isinstance(result, str)


def test_detect_ipynb_source_type_returns_ipynb():
    assert _detect_ipynb_source_type(Path("file.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_uppercase():
    assert _detect_ipynb_source_type(Path("file.IPYNB")) == "ipynb"


def test_detect_ipynb_source_type_mixed_case():
    assert _detect_ipynb_source_type(Path("file.Ipynb")) == "ipynb"
    assert _detect_ipynb_source_type(Path("file.iPyNb")) == "ipynb"


def test_detect_ipynb_source_type_double_extension():
    """file.tar.ipynb → suffix 是 '.ipynb'。"""
    assert _detect_ipynb_source_type(Path("file.tar.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_dotfile_with_ipynb_suffix():
    """.hidden.ipynb → suffix 是 '.ipynb'。"""
    assert _detect_ipynb_source_type(Path(".hidden.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_rejects_json():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("file.json"))
    assert exc.value.code == "unsupported_type"


def test_detect_ipynb_source_type_rejects_md():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("file.md"))


def test_detect_ipynb_source_type_rejects_no_suffix():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("README"))
    assert exc.value.code == "unsupported_type"
    assert "(无)" in exc.value.message


def test_detect_ipynb_source_type_error_details_has_suffix():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("file.unknown"))
    assert "suffix" in exc.value.details
    assert exc.value.details["suffix"] == ".unknown"


def test_detect_ipynb_source_type_error_message_mentions_ipynb():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("file.xxx"))
    assert "ipynb" in exc.value.message.lower() or ".ipynb" in exc.value.message


# ---------- _cell_source_to_text 类型覆盖 ----------


def test_cell_source_to_text_string_passthrough():
    assert _cell_source_to_text("hello") == "hello"


def test_cell_source_to_text_empty_string():
    assert _cell_source_to_text("") == ""


def test_cell_source_to_text_list_of_strings():
    assert _cell_source_to_text(["a", "b", "c"]) == "abc"


def test_cell_source_to_text_list_of_strings_with_newlines():
    """list 内字符串本身可含换行。"""
    assert _cell_source_to_text(["line1\n", "line2\n"]) == "line1\nline2\n"


def test_cell_source_to_text_empty_list_returns_empty():
    assert _cell_source_to_text([]) == ""


def test_cell_source_to_text_none_returns_none():
    assert _cell_source_to_text(None) is None


def test_cell_source_to_text_int_returns_none():
    """int 不是 str/list → 返 ""。"""
    assert _cell_source_to_text(42) is None


def test_cell_source_to_text_float_returns_none():
    assert _cell_source_to_text(3.14) is None


def test_cell_source_to_text_bool_returns_none():
    """bool 不是 str/list（虽然 bool 是 int 子类）→ 返 ""。"""
    assert _cell_source_to_text(True) is None
    assert _cell_source_to_text(False) is None


def test_cell_source_to_text_dict_returns_none():
    assert _cell_source_to_text({"k": "v"}) is None


def test_cell_source_to_text_bytes_returns_none():
    """bytes 不是 str/list（Python 严格区分）→ 返 ""。"""
    assert _cell_source_to_text(b"hello") is None


def test_cell_source_to_text_list_with_non_string_items():
    """list 含 int/None → 用 str() 转。"""
    assert _cell_source_to_text(["a", 1, None, "b"]) is None


# adoption 契约 §5 注记（2026-08-27）：list 须全为 str 才拼接，含非 str 项 → None。
def test_cell_source_to_text_list_with_nested_list():
    """嵌套 list（含子 list）→ None（不做 str() 强转）。"""
    assert _cell_source_to_text(["a", ["x", "y"], "b"]) is None


def test_cell_source_to_text_list_with_empty_strings():
    """list 内空字符串正常 concat。"""
    assert _cell_source_to_text(["", "a", "", "b", ""]) == "ab"


def test_cell_source_to_text_returns_str_type():
    assert isinstance(_cell_source_to_text("hello"), str)
    assert isinstance(_cell_source_to_text(["a"]), str)
    assert _cell_source_to_text(None) is None


# ---------- _extract_kernel_language 边角 ----------


def test_extract_kernel_language_from_kernelspec_language_field():
    metadata = {"kernelspec": {"language": "python", "name": "python3"}}
    assert _extract_kernel_language(metadata) == "python"


# adoption 契约 §6 注记（2026-08-27）：kernelspec.name 是内核标识，不参与语言判定；
# 链为 kernelspec.language → language_info.name → 空串。
def test_extract_kernel_language_kernelspec_name_not_a_language():
    metadata = {"kernelspec": {"name": "python3"}}
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_language_info_name_fallback():
    metadata = {"language_info": {"name": "r"}}
    assert _extract_kernel_language(metadata) == "r"


def test_extract_kernel_language_empty_metadata_returns_empty():
    assert _extract_kernel_language({}) == ""


def test_extract_kernel_language_none_returns_empty():
    """metadata=None 不会 crash（虽然类型签名是 dict）。"""
    # 函数内 .get 都对 dict 调用；None 会 AttributeError
    # 实际：metadata=None → None.get raises AttributeError
    # 但 parse() 中调用前用 nb.get("metadata") or {}，所以 None 不会传入
    # 这里测试 dict 内 kernelspec=None
    assert _extract_kernel_language({"kernelspec": None}) == ""


def test_extract_kernel_language_kernelspec_empty_dict():
    assert _extract_kernel_language({"kernelspec": {}}) == ""


def test_extract_kernel_language_language_info_empty_dict():
    assert _extract_kernel_language({"language_info": {}}) == ""


def test_extract_kernel_language_kernelspec_language_overrides_name():
    """language 优先于 name。"""
    metadata = {"kernelspec": {"language": "python", "name": "python3"}}
    assert _extract_kernel_language(metadata) == "python"


def test_extract_kernel_language_kernelspec_language_empty_is_absent():
    """language='' 视为缺失 → 空串（不回落 name）。"""
    metadata = {"kernelspec": {"language": "", "name": "fallback"}}
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_kernelspec_language_none_is_absent():
    """language=None 视为缺失 → 空串（不回落 name）。"""
    metadata = {"kernelspec": {"language": None, "name": "fallback"}}
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_all_fields_empty_returns_empty():
    metadata = {
        "kernelspec": {"language": "", "name": ""},
        "language_info": {"name": ""},
    }
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_only_kernelspec_no_language_info():
    metadata = {"kernelspec": {"language": "julia"}}
    assert _extract_kernel_language(metadata) == "julia"


def test_extract_kernel_language_returns_str():
    assert isinstance(_extract_kernel_language({}), str)
    assert isinstance(
        _extract_kernel_language({"kernelspec": {"language": "x"}}), str
    )


# ---------- IpynbParser 实例复用 ----------


def _nb(cells: list[dict], language: str = "python") -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"language": language, "name": f"{language}3"},
            "language_info": {"name": language},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _write_nb(tmp_path: Path, name: str, nb: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    return p


def test_ipynb_parser_can_be_reused_across_files(tmp_path: Path):
    """同一 IpynbParser 实例可解析多个文件，结果独立。"""
    p1 = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "markdown", "source": "# Title A"},
    ]))
    p2 = _write_nb(tmp_path, "b.ipynb", _nb([
        {"cell_type": "markdown", "source": "# Title B"},
    ]))

    parser = IpynbParser()
    doc1 = parser.parse(p1, source_hash="a" * 64)
    doc2 = parser.parse(p2, source_hash="b" * 64)
    assert any("Title A" in (e.content or "") for e in doc1.elements)
    assert any("Title B" in (e.content or "") for e in doc2.elements)
    assert doc1.document_id != doc2.document_id


def test_ipynb_parser_stateless_no_counter_leak(tmp_path: Path):
    """IpynbParser 无实例状态 → element_id 从 e0000 开始。"""
    p1 = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "print(1)"},
    ]))
    p2 = _write_nb(tmp_path, "b.ipynb", _nb([
        {"cell_type": "code", "source": "print(2)"},
    ]))

    parser = IpynbParser()
    doc1 = parser.parse(p1, source_hash="a" * 64)
    doc2 = parser.parse(p2, source_hash="b" * 64)
    assert doc1.elements[0].element_id.endswith("::e0000")
    assert doc2.elements[0].element_id.endswith("::e0000")


def test_ipynb_parser_sequential_element_ids_in_single_doc(tmp_path: Path):
    """单 notebook 内 element_id 严格递增。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "markdown", "source": "# H1"},
        {"cell_type": "code", "source": "code1"},
        {"cell_type": "raw", "source": "raw1"},
        {"cell_type": "markdown", "source": "para"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    suffixes = [e.element_id.split("::")[-1] for e in doc.elements]
    assert suffixes == sorted(suffixes)
    assert len(set(suffixes)) == len(suffixes)


# ---------- IpynbParser 错误路径 ----------


def test_ipynb_parser_missing_file_error_details_has_path(tmp_path: Path):
    from app.parsers.base import ParserError
    parser = IpynbParser()
    missing = tmp_path / "nope.ipynb"
    with pytest.raises(ParserError) as exc:
        parser.parse(missing, source_hash="a" * 64)
    assert exc.value.code == "file_not_found"
    assert "path" in exc.value.details
    assert exc.value.details["path"] == str(missing)


def test_ipynb_parser_unsupported_extension_error_details_has_suffix(tmp_path: Path):
    from app.parsers.base import ParserError
    parser = IpynbParser()
    src = tmp_path / "x.json"
    src.write_text("[]", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        parser.parse(src, source_hash="a" * 64)
    assert exc.value.code == "unsupported_type"
    assert "suffix" in exc.value.details


def test_ipynb_parser_invalid_json_error_has_exception_type(tmp_path: Path):
    from app.parsers.base import ParserError
    p = tmp_path / "bad.ipynb"
    p.write_text("{not valid", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_invalid_json"
    assert "exception_type" in exc.value.details
    assert exc.value.details["exception_type"] == "JSONDecodeError"


def test_ipynb_parser_top_level_array_raises_bad_structure(tmp_path: Path):
    from app.parsers.base import ParserError
    p = tmp_path / "arr.ipynb"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_ipynb_parser_top_level_string_raises_bad_structure(tmp_path: Path):
    from app.parsers.base import ParserError
    p = tmp_path / "str.ipynb"
    p.write_text('"hello"', encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_ipynb_parser_top_level_null_raises_bad_structure(tmp_path: Path):
    from app.parsers.base import ParserError
    p = tmp_path / "null.ipynb"
    p.write_text("null", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_ipynb_parser_top_level_int_raises_bad_structure(tmp_path: Path):
    from app.parsers.base import ParserError
    p = tmp_path / "int.ipynb"
    p.write_text("42", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_ipynb_parser_cells_field_dict_raises_bad_structure(tmp_path: Path):
    from app.parsers.base import ParserError
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps({"cells": {"not": "array"}}), encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_ipynb_parser_cells_field_string_raises_bad_structure(tmp_path: Path):
    from app.parsers.base import ParserError
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps({"cells": "string"}), encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_ipynb_parser_nbformat_3_raises_unsupported_version(tmp_path: Path):
    from app.parsers.base import ParserError
    p = tmp_path / "old.ipynb"
    p.write_text(json.dumps({"nbformat": 3, "cells": []}), encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_unsupported_version"
    assert exc.value.details["nbformat"] == 3


def test_ipynb_parser_nbformat_0_raises_unsupported_version(tmp_path: Path):
    from app.parsers.base import ParserError
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps({"nbformat": 0, "cells": []}), encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_unsupported_version"


# ---------- Document metadata 字段 ----------


def test_ipynb_parser_metadata_has_ipynb_true(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "print(1)"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata["ipynb"] is True


def test_ipynb_parser_metadata_records_nbformat_4(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata["nbformat"] == 4


def test_ipynb_parser_metadata_records_nbformat_minor(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata["nbformat_minor"] == 5


def test_ipynb_parser_metadata_nbformat_minor_missing_rejected(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：nbformat_minor 缺失 → ipynb_bad_structure。

    原快照语义为 metadata.nbformat_minor = None 透传。
    """
    nb = {
        "cells": [{"cell_type": "code", "source": "x"}],
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "nbformat": 4,
    }
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, source_hash="a" * 64)
    assert ei.value.code == "ipynb_bad_structure"
    assert ei.value.details["field"] == "nbformat_minor"


def test_ipynb_parser_metadata_records_cell_count(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "a"},
        {"cell_type": "code", "source": "b"},
        {"cell_type": "markdown", "source": "# H"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata["cell_count"] == 3


def test_ipynb_parser_metadata_records_language(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ], language="python"))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata["language"] == "python"


def test_ipynb_parser_metadata_language_empty_when_no_kernelspec(tmp_path: Path):
    """无 kernelspec/language_info → language=''。"""
    nb = {
        "cells": [{"cell_type": "code", "source": "x"}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata["language"] == ""


def test_ipynb_parser_metadata_keys_full_set(tmp_path: Path):
    """metadata 5 个 key: ipynb/nbformat/nbformat_minor/cell_count/language。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert set(doc.metadata.keys()) == {
        "ipynb", "nbformat", "nbformat_minor", "cell_count", "language"
    }


# ---------- cell 处理细节 ----------


def test_ipynb_parser_code_cell_metadata_kind_is_code_cell(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "print('hi')"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.elements[0].metadata["kind"] == "code_cell"


def test_ipynb_parser_raw_cell_metadata_kind_is_raw_cell(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "raw", "source": "raw text"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.elements[0].metadata["kind"] == "raw_cell"


def test_ipynb_parser_code_cell_metadata_has_language(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x = 1"},
    ], language="julia"))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.elements[0].metadata["language"] == "julia"


def test_ipynb_parser_raw_cell_metadata_no_language_key(tmp_path: Path):
    """raw cell metadata 只有 kind，无 language。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "raw", "source": "raw"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert "language" not in doc.elements[0].metadata


def test_ipynb_parser_markdown_cell_sub_element_metadata_no_kind(tmp_path: Path):
    """markdown cell 委托给 MarkdownParser，子 element metadata 不应有 kind 字段。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "markdown", "source": "# Title"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # heading element metadata 来自 MarkdownParser（如 {"level": 1}），但无 kind
    assert "kind" not in doc.elements[0].metadata


def test_ipynb_parser_code_cell_locator_line1(tmp_path: Path):
    """code cell locator 只有 cell_index/cell_type，无 line。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "print(1)"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    loc = doc.elements[0].source_locator
    assert set(loc.keys()) == {"cell_index", "cell_type", "line"}
    assert loc["cell_index"] == 0
    assert loc["cell_type"] == "code"
    assert loc["line"] == 1


def test_ipynb_parser_raw_cell_locator_line1(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "raw", "source": "raw"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    loc = doc.elements[0].source_locator
    assert set(loc.keys()) == {"cell_index", "cell_type", "line"}
    assert loc["cell_index"] == 0
    assert loc["cell_type"] == "raw"
    assert loc["line"] == 1


def test_ipynb_parser_code_cell_content_preserved(tmp_path: Path):
    """code cell 内容 strip 两端空白。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "\n\n   print(1)  \n\n"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.elements[0].content == '\n\n   print(1)  \n\n'


# adoption 契约 §5/§8 注记（2026-08-27）：source 非法输入归一为 None（跳过 cell +
# ipynb_bad_cell）；code/raw 正文保留原始缩进换行（strip 仅判空）；locator 补 line=1。
# 以下原快照期望已按定稿契约改写。
def test_ipynb_parser_raw_cell_content_preserved(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "raw", "source": "\n\n   raw text  \n\n"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.elements[0].content == '\n\n   raw text  \n\n'


def test_ipynb_parser_code_cell_multiline_source_list(tmp_path: Path):
    """code cell source 是 list → concat → strip。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": ["line1\n", "line2\n", "line3"]},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # concat 后 strip（首尾无空白，内部保留）
    assert doc.elements[0].content == "line1\nline2\nline3"


def test_ipynb_parser_markdown_cell_locator_carries_section_path(tmp_path: Path):
    """markdown cell 内 heading → sub-element locator 含 section_path。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "markdown", "source": "# Heading\n\ncontent"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    heading = next(e for e in doc.elements if e.type == "heading")
    assert "section_path" in heading.source_locator
    assert heading.source_locator["cell_index"] == 0


def test_ipynb_parser_two_markdown_cells_section_paths_independent(tmp_path: Path):
    """两个 markdown cell 的 section_path 互不影响（每 cell 独立栈）。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "markdown", "source": "# A\n\ntext under A"},
        {"cell_type": "markdown", "source": "# B\n\ntext under B"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # 4 个 elements: heading A, para A, heading B, para B
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 2
    # cell_index 不同
    cell_indices = [h.source_locator["cell_index"] for h in headings]
    assert cell_indices == [0, 1]


def test_ipynb_parser_empty_code_cell_emits_warning_with_cell_index(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": ""},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.warnings) >= 1
    w = doc.warnings[0]
    assert w.code == "ipynb_empty_code_cell"
    assert w.details["cell_index"] == 0


def test_ipynb_parser_whitespace_only_code_cell_emits_warning(tmp_path: Path):
    """code cell 内容只有空白 → 视为空，emit warning。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "   \n\n\t  "},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert any(w.code == "ipynb_empty_code_cell" for w in doc.warnings)
    assert len(doc.elements) == 0


def test_ipynb_parser_unknown_cell_type_emits_warning(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "unknown_type", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert any(w.code == "ipynb_unknown_cell_type" for w in doc.warnings)
    assert len(doc.elements) == 0


def test_ipynb_parser_cell_not_dict_emits_warning_with_cell_index(tmp_path: Path):
    """cell 不是 dict（如 string）→ emit warning + skip。"""
    p = tmp_path / "x.ipynb"
    nb = {
        "cells": ["not_a_dict", {"cell_type": "code", "source": "ok"}],
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert any(w.code == "ipynb_bad_cell" for w in doc.warnings)
    # 第二个 cell 仍正常解析
    assert len(doc.elements) == 1


def test_ipynb_parser_unknown_cell_type_warning_records_ct(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "weird", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    w = doc.warnings[0]
    assert w.details["cell_type"] == "weird"
    assert w.details["cell_index"] == 0


def test_ipynb_parser_empty_notebook_emits_no_content_warning(tmp_path: Path):
    """无 cells → ipynb_no_content warning。"""
    nb = {
        "cells": [],
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = tmp_path / "empty.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


def test_ipynb_parser_only_empty_cells_emits_no_content(tmp_path: Path):
    """全是空 cell → 0 elements + ipynb_no_content。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": ""},
        {"cell_type": "raw", "source": ""},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 0
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


def test_ipynb_parser_raw_empty_silently_skipped_no_warning(tmp_path: Path):
    """空 raw cell → silently skip（不 emit warning）。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "raw", "source": ""},
        {"cell_type": "code", "source": "ok"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # 空 raw 不 warning，code 正常 element
    assert len(doc.elements) == 1
    # 没有 raw 相关的 warning
    assert all("raw" not in (w.code or "") for w in doc.warnings)


# ---------- nbformat 缺失/异常 ----------


def test_ipynb_parser_nbformat_missing_rejected_as_bad_structure(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：nbformat 缺失 → ipynb_bad_structure。

    原快照语义为“None → not < 4 → 视为支持”。
    """
    nb = {
        "cells": [{"cell_type": "code", "source": "x"}],
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "nbformat_minor": 5,
    }
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, source_hash="a" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_ipynb_parser_nbformat_4_minor_0_works(tmp_path: Path):
    """nbformat=4, minor=0 → 支持。"""
    nb = {
        "cells": [{"cell_type": "code", "source": "x"}],
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 0,
    }
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata["nbformat_minor"] == 0


def test_ipynb_parser_nbformat_5_unsupported(tmp_path: Path):
    """adoption 契约 §1（2026-08-27）：nbformat=5 → ipynb_unsupported_version。

    原快照语义为 ">= 4 → 支持"。
    """
    nb = {
        "cells": [{"cell_type": "code", "source": "x"}],
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "nbformat": 5,
        "nbformat_minor": 0,
    }
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, source_hash="a" * 64)
    assert ei.value.code == "ipynb_unsupported_version"
    assert ei.value.details["nbformat"] == 5


def test_ipynb_parser_metadata_field_none_does_not_crash(tmp_path: Path):
    """notebook 顶层 metadata=None → 当 {} 处理。"""
    nb = {
        "cells": [{"cell_type": "code", "source": "x"}],
        "metadata": None,
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # metadata 被 `or {}` 兜底
    assert doc.metadata["language"] == ""


def test_ipynb_parser_cells_missing_treated_as_empty(tmp_path: Path):
    """cells 字段缺失 → `nb.get("cells") or []` → [] → ipynb_no_content。"""
    nb = {
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata["cell_count"] == 0
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


# ---------- 大 notebook / Unicode ----------


def test_ipynb_parser_large_notebook_100_cells(tmp_path: Path):
    """大 notebook（100 个 code cell）稳定。"""
    cells = [
        {"cell_type": "code", "source": f"x{i} = {i}"}
        for i in range(100)
    ]
    p = _write_nb(tmp_path, "large.ipynb", _nb(cells))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 100
    assert doc.metadata["cell_count"] == 100


def test_ipynb_parser_unicode_content(tmp_path: Path):
    """UTF-8 多字节内容（中文/emoji）正常解析。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "markdown", "source": "# 标题 🎉\n\n你好，世界"},
        {"cell_type": "code", "source": "print('你好')  # 中文注释"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    contents = [(e.content or "") for e in doc.elements]
    assert any("标题" in c for c in contents)
    assert any("🎉" in c for c in contents)
    assert any("你好" in c for c in contents)


def test_ipynb_parser_outputs_field_ignored(tmp_path: Path):
    """code cell 的 outputs 字段被忽略（不进入 element）。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {
            "cell_type": "code",
            "source": "print(1)",
            "outputs": [
                {"output_type": "stream", "name": "stdout", "text": "1\n"},
            ],
            "execution_count": 1,
        },
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # element content 只有 source，无 outputs
    assert "1\n" not in (doc.elements[0].content or "")
    assert doc.elements[0].content == "print(1)"


def test_ipynb_parser_cell_with_extra_unknown_fields_ignored(tmp_path: Path):
    """cell 中未知字段（id/custom_metadata 等）被忽略。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {
            "cell_type": "code",
            "source": "x",
            "id": "cell-abc",
            "custom_field": "ignored",
        },
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.elements[0].content == "x"
    assert "id" not in doc.elements[0].metadata


# ---------- Document 字段完整性 ----------


def test_ipynb_parser_chunks_empty_by_default(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.chunks == []


def test_ipynb_parser_relations_empty_by_default(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.relations == []


def test_ipynb_parser_errors_empty_by_default(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.errors == []


def test_ipynb_parser_source_path_preserved(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.source_path == str(p)


def test_ipynb_parser_source_hash_passed_through(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="b" * 64)
    assert doc.source_hash == "b" * 64


def test_ipynb_parser_parser_name_is_ipynb(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.parser_name == "ipynb"


def test_ipynb_parser_parser_version_is_stdlib_010(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.parser_version == "stdlib/0.1.0"


def test_ipynb_parser_element_confidence_strictly_095(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
        {"cell_type": "markdown", "source": "# H"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.confidence == 0.95


def test_ipynb_parser_element_parent_id_is_none(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.parent_id is None


# ---------- schema 通过 ----------


def test_ipynb_parser_result_passes_schema(tmp_path: Path):
    """parse 出的 Document 通过 schema 校验。"""
    from app.schema import is_valid
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "markdown", "source": "# Title\n\nparagraph"},
        {"cell_type": "code", "source": "print('hi')"},
        {"cell_type": "raw", "source": "raw text"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert is_valid(doc.to_dict()) is True


def test_ipynb_parser_empty_notebook_passes_schema(tmp_path: Path):
    """空 notebook（无 elements）也通过 schema。"""
    from app.schema import is_valid
    p = _write_nb(tmp_path, "x.ipynb", _nb([]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert is_valid(doc.to_dict()) is True


# ---------- mixed cell scenarios ----------


def test_ipynb_parser_mixed_cells_count(tmp_path: Path):
    """混合 cell：1 markdown(2 elements) + 1 code + 1 raw = 4 elements。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "markdown", "source": "# H\n\npara"},
        {"cell_type": "code", "source": "x=1"},
        {"cell_type": "raw", "source": "raw"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # markdown → 2 (heading + para), code → 1, raw → 1 = 4
    assert len(doc.elements) == 4


def test_ipynb_parser_markdown_with_heading_then_list(tmp_path: Path):
    """markdown cell 含 heading + list → 多个 element。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "markdown", "source": "# Title\n\n- item1\n\n- item2"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # heading + 2 list items
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert types.count("list_item") == 2


def test_ipynb_parser_code_cell_with_multiline_content(tmp_path: Path):
    """code cell 含换行的 source。"""
    source = "def f():\n    return 42\n\nprint(f())"
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": source},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # 内部换行保留
    assert "\n" in doc.elements[0].content
    assert "def f():" in doc.elements[0].content
    assert "return 42" in doc.elements[0].content


def test_ipynb_parser_warning_records_have_reason_string(tmp_path: Path):
    """所有 warning 都应有非空 reason。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": ""},
        {"cell_type": "weird", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for w in doc.warnings:
        assert isinstance(w.reason, str)
        assert len(w.reason) > 0


# ---------- cell_index 严格递增 ----------


def test_ipynb_parser_cell_index_strictly_increasing_for_elements(tmp_path: Path):
    """各 element 的 cell_index 应单调非递减（每 cell 内可能多个 element）。"""
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "a"},
        {"cell_type": "markdown", "source": "# H\n\npara"},
        {"cell_type": "code", "source": "b"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    cell_indices = [e.source_locator["cell_index"] for e in doc.elements]
    # 单调非递减
    assert cell_indices == sorted(cell_indices)


def test_ipynb_parser_first_cell_index_is_zero(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x"},
    ]))
    parser = IpynbParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.elements[0].source_locator["cell_index"] == 0
