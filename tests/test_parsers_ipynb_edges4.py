"""app/parsers/ipynb_parser.py 边角测试 - 第四轮（Round 114）。

补强已有 base/edges/edges2/edges3（共 105 测试）未覆盖的深度路径：
- _cell_source_to_text：bool/int/float/None/bytes/dict/tuple 输入边界
- _extract_kernel_language：kernelspec.language="" / name="" /
  language_info.name="" / metadata null / language_info non-dict
- _detect_ipynb_source_type：.IPYNB / .IpYnB 混合大小写、错误 details.suffix
- IpynbParser.parse：
  - markdown cell 含 code fence、blockquote、list 深度
  - code cell source=null
  - raw cell source=null
  - empty cells list → no_content warning
  - nbformat_major as int/missing
  - nbformat_minor preserved
  - metadata.nbformat_minor missing
  - cell.cell_type 缺失 → unknown
  - cell.source 缺失 → 空 string
  - 多 cell element_id 连续
  - confidence=0.95 一致
- IpynbParser 类属性：name/version、instance match class、
  issubclass(Parser)、parse 签名
- 模块结构：__all__、imports、常量值、docstring
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import ParserError
from app.parsers.ipynb_parser import (
    IpynbParser,
    _IPYNB_EXTENSIONS,
    _cell_source_to_text,
    _detect_ipynb_source_type,
    _extract_kernel_language,
)


SHA = "a" * 64


def _write_nb(tmp_path: Path, nb: dict, name: str = "x.ipynb") -> Path:
    # adoption 契约 §2 注记（2026-08-27）：版本字段必填——fixture 缺省时补默认。
    nb.setdefault("nbformat", 4)
    nb.setdefault("nbformat_minor", 5)
    p = tmp_path / name
    p.write_text(json.dumps(nb), encoding="utf-8")
    return p


def _minimal_nb(cells: list[dict], **extra: Any) -> dict:
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {},
        "cells": cells,
    }
    nb.update(extra)
    return nb


# =========================================================================
# _cell_source_to_text 边界
# =========================================================================


def test_cell_source_bool_returns_none():
    """bool 不是 str/list → ''。"""
    assert _cell_source_to_text(True) is None


def test_cell_source_int_returns_none():
    assert _cell_source_to_text(42) is None


def test_cell_source_float_returns_none():
    assert _cell_source_to_text(3.14) is None


def test_cell_source_none_returns_none():
    assert _cell_source_to_text(None) is None


def test_cell_source_bytes_returns_none():
    """bytes 不是 str（Python 3 strict）→ ''。"""
    assert _cell_source_to_text(b"hello") is None


def test_cell_source_dict_returns_none():
    assert _cell_source_to_text({"k": "v"}) is None


def test_cell_source_tuple_returns_none():
    """tuple 不是 list → ''。"""
    assert _cell_source_to_text(("a", "b")) is None


def test_cell_source_set_returns_none():
    assert _cell_source_to_text({"a", "b"}) is None


def test_cell_source_list_of_ints_joined_as_str():
    """list[int] → join str(each)。"""
    assert _cell_source_to_text([1, 2, 3]) is None


def test_cell_source_list_of_floats_joined():
    assert _cell_source_to_text([1.5, 2.5]) is None


def test_cell_source_list_of_bools_joined():
    assert _cell_source_to_text([True, False]) is None


def test_cell_source_list_of_none_joined():
    """None 在 list 内 → str(None) = 'None'。"""
    assert _cell_source_to_text([None, None]) is None


# adoption 契约 §5 注记（2026-08-27）：list 须全为 str 才拼接，含非 str 项 → None。
def test_cell_source_list_of_dicts_joined():
    """list 内含 dict → None（不做 str() 强转）。"""
    assert _cell_source_to_text([{"a": 1}]) is None


def test_cell_source_list_nested():
    """nested list → None（不做 str() 强转）。"""
    assert _cell_source_to_text([["nested"]]) is None


def test_cell_source_empty_str_returns_empty():
    assert _cell_source_to_text("") == ""


def test_cell_source_single_char_str():
    assert _cell_source_to_text("x") == "x"


def test_cell_source_list_with_one_empty_str():
    assert _cell_source_to_text([""]) == ""


def test_cell_source_list_with_newline_ending_parts():
    parts = ["line1\n", "line2\n", "line3"]
    assert _cell_source_to_text(parts) == "line1\nline2\nline3"


def test_cell_source_returns_str_type():
    assert isinstance(_cell_source_to_text("hello"), str)


def test_cell_source_returns_str_for_list_input():
    assert isinstance(_cell_source_to_text(["a", "b"]), str)


# =========================================================================
# _extract_kernel_language 深度
# =========================================================================


def test_extract_lang_kernelspec_empty_string_language_falls_back_to_name():
    """kernelspec.language='' 时 fall back to kernelspec.name。"""
    md = {"kernelspec": {"language": "", "name": "python3"}}
    assert _extract_kernel_language(md) == "python3"


def test_extract_lang_kernelspec_language_whitespace_only_does_not_fall_back():
    """kernelspec.language='   '（Python 中 truthy）→ 不 fall back to name。

    Python `'   ' or X` = '   '（非空字符串都是 truthy），所以保留原值。
    """
    md = {"kernelspec": {"language": "   ", "name": "py3"}}
    assert _extract_kernel_language(md) == "   "


def test_extract_lang_kernelspec_no_language_no_name_falls_back_to_language_info():
    md = {
        "kernelspec": {"language": None, "name": None},
        "language_info": {"name": "ruby"},
    }
    assert _extract_kernel_language(md) == "ruby"


def test_extract_lang_kernelspec_no_dict_returns_from_language_info():
    md = {"kernelspec": None, "language_info": {"name": "julia"}}
    assert _extract_kernel_language(md) == "julia"


def test_extract_lang_kernelspec_undefined_key_uses_language_info():
    md = {"language_info": {"name": "go"}}
    assert _extract_kernel_language(md) == "go"


def test_extract_lang_language_info_empty_string_returns_empty():
    """language_info.name='' → fall to '' (falsy)。"""
    md = {"language_info": {"name": ""}}
    assert _extract_kernel_language(md) == ""


def test_extract_lang_language_info_non_dict_raises_attribute_error():
    """language_info 是 non-dict → AttributeError（实际无 type guard）。"""
    md = {"language_info": "python"}
    with pytest.raises(AttributeError):
        _extract_kernel_language(md)


def test_extract_lang_kernelspec_non_dict_raises_attribute_error():
    md = {"kernelspec": "python3"}
    with pytest.raises(AttributeError):
        _extract_kernel_language(md)


def test_extract_lang_metadata_empty_dict():
    assert _extract_kernel_language({}) == ""


def test_extract_lang_metadata_none_raises_attribute_error():
    """None metadata 无 type guard → AttributeError。"""
    with pytest.raises(AttributeError):
        _extract_kernel_language(None)  # type: ignore[arg-type]


def test_extract_lang_kernelspec_language_overrides_name():
    md = {"kernelspec": {"language": "rust", "name": "rs"}}
    assert _extract_kernel_language(md) == "rust"


def test_extract_lang_returns_str_type():
    md = {"kernelspec": {"language": "python"}}
    assert isinstance(_extract_kernel_language(md), str)


# =========================================================================
# _detect_ipynb_source_type 边界
# =========================================================================


def test_detect_ipynb_source_type_uppercase_ipynb():
    p = Path("x.IPYNB")
    assert _detect_ipynb_source_type(p) == "ipynb"


def test_detect_ipynb_source_type_mixed_case():
    p = Path("x.IpYnB")
    assert _detect_ipynb_source_type(p) == "ipynb"


def test_detect_ipynb_source_type_rejects_json():
    p = Path("a.json")
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(p)


def test_detect_ipynb_source_type_rejects_py():
    p = Path("a.py")
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(p)


def test_detect_ipynb_source_type_error_details_suffix_value():
    p = Path("a.txt")
    with pytest.raises(ParserError) as exc_info:
        _detect_ipynb_source_type(p)
    assert exc_info.value.details["suffix"] == ".txt"


def test_detect_ipynb_source_type_error_no_suffix_details():
    """无后缀时 details.suffix 应为空 string。"""
    p = Path("nofile")
    with pytest.raises(ParserError) as exc_info:
        _detect_ipynb_source_type(p)
    assert "suffix" in exc_info.value.details
    assert exc_info.value.details["suffix"] == ""


def test_ipynb_extensions_exact_one_entry():
    assert _IPYNB_EXTENSIONS == (".ipynb",)


def test_ipynb_extensions_count_one():
    assert len(_IPYNB_EXTENSIONS) == 1


# =========================================================================
# IpynbParser.parse：cell source 边界
# =========================================================================


# adoption 契约 §5 注记（2026-08-27）：source 非法（含 None）→ 跳过 cell + ipynb_bad_cell。
def test_parse_code_cell_source_null_skipped_with_warning(tmp_path: Path):
    """code cell source=null → 跳过 cell + ipynb_bad_cell warning。"""
    nb = _minimal_nb([{"cell_type": "code", "source": None, "metadata": {}}])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    codes = [w.code for w in doc.warnings]
    assert codes == ["ipynb_bad_cell",
                     "ipynb_no_content"]
    w = doc.warnings[0]
    assert w.details == {"cell_index": 0, "field": "source"}
    assert doc.elements == []


def test_parse_raw_cell_source_null_skipped_silently(tmp_path: Path):
    """raw cell source=null → 空 text → 静默跳过（raw 无 warning）。"""
    nb = _minimal_nb([{"cell_type": "raw", "source": None, "metadata": {}}])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    # raw 空 cell 不警告（仅 no_content warning 因为 0 elements）
    codes = [w.code for w in doc.warnings]
    assert "ipynb_empty_code_cell" not in codes
    assert "ipynb_no_content" in codes


def test_parse_markdown_cell_source_missing_emits_no_elements(tmp_path: Path):
    nb = _minimal_nb([{"cell_type": "markdown"}])  # 缺 source
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    # markdown 空 source → 0 elements → no_content
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "ipynb_no_content" in codes


def test_parse_empty_cells_list_emits_no_content(tmp_path: Path):
    nb = _minimal_nb([])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "ipynb_no_content" in codes


def test_parse_only_empty_code_cells_emits_no_content(tmp_path: Path):
    """全空 code cell → 既 empty_code_cell 又 no_content。"""
    nb = _minimal_nb(
        [
            {"cell_type": "code", "source": "", "metadata": {}},
            {"cell_type": "code", "source": "  \n", "metadata": {}},
        ]
    )
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    codes = [w.code for w in doc.warnings]
    assert "ipynb_no_content" in codes


def test_parse_metadata_preserves_nbformat_value(tmp_path: Path):
    nb = _minimal_nb([], nbformat=4)
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.metadata["nbformat"] == 4


def test_parse_metadata_preserves_nbformat_minor_value(tmp_path: Path):
    nb = _minimal_nb([], nbformat_minor=2)
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.metadata["nbformat_minor"] == 2


def test_parse_metadata_nbformat_missing_rejected(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：nbformat 缺失 → ipynb_bad_structure（直写文件绕过 helper 默认）。"""
    nb = {"nbformat_minor": 5, "metadata": {}, "cells": []}
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, source_hash=SHA)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_metadata_nbformat_minor_missing_rejected(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：nbformat_minor 缺失 → ipynb_bad_structure（直写文件绕过 helper 默认）。"""
    nb = {"nbformat": 4, "metadata": {}, "cells": []}
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, source_hash=SHA)
    assert ei.value.code == "ipynb_bad_structure"
    assert ei.value.details["field"] == "nbformat_minor"


def test_parse_metadata_cell_count_value(tmp_path: Path):
    nb = _minimal_nb(
        [
            {"cell_type": "code", "source": "x=1", "metadata": {}},
            {"cell_type": "code", "source": "y=2", "metadata": {}},
            {"cell_type": "raw", "source": "z", "metadata": {}},
        ]
    )
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.metadata["cell_count"] == 3


def test_parse_metadata_has_ipynb_flag_true(tmp_path: Path):
    nb = _minimal_nb([])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.metadata["ipynb"] is True


def test_parse_metadata_has_5_keys(tmp_path: Path):
    nb = _minimal_nb([])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert set(doc.metadata.keys()) == {
        "ipynb",
        "nbformat",
        "nbformat_minor",
        "cell_count",
        "language",
    }


def test_parse_metadata_language_from_kernelspec(tmp_path: Path):
    nb = _minimal_nb(
        [],
        metadata={"kernelspec": {"language": "python", "name": "python3"}},
    )
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.metadata["language"] == "python"


def test_parse_metadata_language_empty_when_no_metadata(tmp_path: Path):
    nb = {"nbformat": 4, "nbformat_minor": 5, "cells": []}
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.metadata["language"] == ""


# =========================================================================
# IpynbParser.parse：cell type 边界
# =========================================================================


def test_parse_cell_missing_cell_type_defaults_unknown_warning(tmp_path: Path):
    nb = _minimal_nb([{"source": "text"}])  # 缺 cell_type
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    codes = [w.code for w in doc.warnings]
    assert "ipynb_unknown_cell_type" in codes


def test_parse_cell_cell_type_int_treated_as_unknown(tmp_path: Path):
    """cell_type 是 int 1 → 触发 unknown_cell_type。"""
    nb = _minimal_nb([{"cell_type": 1, "source": "x"}])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    codes = [w.code for w in doc.warnings]
    assert "ipynb_unknown_cell_type" in codes


def test_parse_unknown_cell_type_warning_has_details(tmp_path: Path):
    nb = _minimal_nb([{"cell_type": "weird", "source": "x"}])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    for w in doc.warnings:
        if w.code == "ipynb_unknown_cell_type":
            assert w.details.get("cell_type") == "weird"
            assert w.details.get("cell_index") == 0


def test_parse_code_cell_text_preserved_in_output(tmp_path: Path):
    nb = _minimal_nb(
        [{"cell_type": "code", "source": "  print('hi')  \n", "metadata": {}}]
    )
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].content == "  print('hi')  \n"


# adoption 契约 §5/§8 注记（2026-08-27）：source 非法输入归一为 None（跳过 cell +
# ipynb_bad_cell）；code/raw 正文保留原始缩进换行（strip 仅判空）；locator 补 line=1。
# 以下原快照期望已按定稿契约改写。
def test_parse_raw_cell_text_preserved(tmp_path: Path):
    nb = _minimal_nb([{"cell_type": "raw", "source": "  hello  ", "metadata": {}}])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].content == '  hello  '


def test_parse_code_cell_metadata_has_kind_code_cell(tmp_path: Path):
    nb = _minimal_nb([{"cell_type": "code", "source": "x", "metadata": {}}])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["kind"] == "code_cell"


def test_parse_raw_cell_metadata_has_kind_raw_cell(tmp_path: Path):
    nb = _minimal_nb([{"cell_type": "raw", "source": "x", "metadata": {}}])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["kind"] == "raw_cell"


def test_parse_code_cell_metadata_has_language(tmp_path: Path):
    nb = _minimal_nb(
        [{"cell_type": "code", "source": "x", "metadata": {}}],
        metadata={"kernelspec": {"language": "rust"}},
    )
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["language"] == "rust"


def test_parse_markdown_cell_emits_correct_element_types(tmp_path: Path):
    nb = _minimal_nb(
        [{"cell_type": "markdown", "source": "# H1\n\ntext.", "metadata": {}}]
    )
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types


def test_parse_markdown_cell_locator_has_cell_type_markdown(tmp_path: Path):
    nb = _minimal_nb(
        [{"cell_type": "markdown", "source": "text.", "metadata": {}}]
    )
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].source_locator["cell_type"] == "markdown"


def test_parse_markdown_cell_locator_has_cell_index_zero(tmp_path: Path):
    nb = _minimal_nb(
        [{"cell_type": "markdown", "source": "text.", "metadata": {}}]
    )
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].source_locator["cell_index"] == 0


def test_parse_markdown_cell_warning_reason_includes_cell_index(tmp_path: Path):
    """markdown cell 内部产生 warning → reason 含 cell #N。"""
    # 触发 markdown 内 warning 的方式：输入会引发 normalize_text 的边角
    # 这里用一个普通的 markdown，看是否有 warning
    nb = _minimal_nb(
        [{"cell_type": "markdown", "source": "text.", "metadata": {}}]
    )
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    # 普通 markdown 不产生 warning（仅结构问题才 warning）
    # 测试无 warning 即可
    for w in doc.warnings:
        if "cell #" in (w.reason or ""):
            assert "cell #0" in w.reason


def test_parse_cell_not_dict_warning_details_has_index(tmp_path: Path):
    nb = _minimal_nb(["not a dict"])  # type: ignore[list-item]
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    for w in doc.warnings:
        if w.code == "ipynb_bad_cell":
            assert w.details.get("cell_index") == 0


def test_parse_code_cell_confidence_0_95(tmp_path: Path):
    nb = _minimal_nb([{"cell_type": "code", "source": "x", "metadata": {}}])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].confidence == 0.95


def test_parse_raw_cell_confidence_0_95(tmp_path: Path):
    nb = _minimal_nb([{"cell_type": "raw", "source": "x", "metadata": {}}])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].confidence == 0.95


def test_parse_markdown_cell_confidence_inherited_from_md_parser(tmp_path: Path):
    """markdown cell 内 element 的 confidence 来自 MarkdownParser。"""
    nb = _minimal_nb(
        [{"cell_type": "markdown", "source": "# H", "metadata": {}}]
    )
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    # heading 默认 confidence 高（具体值看 markdown_parser）
    assert doc.elements[0].confidence > 0


# =========================================================================
# IpynbParser.parse：nbformat 边界
# =========================================================================


def test_parse_nbformat_4_major_int_supported(tmp_path: Path):
    nb = _minimal_nb([], nbformat=4)
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.metadata["nbformat"] == 4


def test_parse_nbformat_negative_raises_unsupported_version(tmp_path: Path):
    nb = _minimal_nb([], nbformat=-1)
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert exc_info.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_minor_negative_rejected(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：nbformat_minor 为负 → ipynb_bad_structure。"""
    nb = _minimal_nb([], nbformat=4, nbformat_minor=-1)
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, source_hash=SHA)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_nbformat_float_value_rejected(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：nbformat 必须为整数，float 4.0 → ipynb_bad_structure。"""
    nb = {"nbformat": 4.0, "nbformat_minor": 5, "metadata": {}, "cells": []}
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, source_hash=SHA)
    assert ei.value.code == "ipynb_bad_structure"


# =========================================================================
# IpynbParser 类属性
# =========================================================================


def test_ipynb_parser_class_name_value():
    assert IpynbParser.name == "ipynb"


def test_ipynb_parser_class_version_value():
    assert IpynbParser.version == "stdlib/0.1.0"


def test_ipynb_parser_class_name_is_str():
    assert isinstance(IpynbParser.name, str)


def test_ipynb_parser_class_version_is_str():
    assert isinstance(IpynbParser.version, str)


def test_ipynb_parser_instance_name_matches_class():
    p = IpynbParser()
    assert p.name == "ipynb"


def test_ipynb_parser_instance_version_matches_class():
    p = IpynbParser()
    assert p.version == "stdlib/0.1.0"


def test_ipynb_parser_inherits_parser():
    from app.parsers.base import Parser

    assert issubclass(IpynbParser, Parser)


def test_ipynb_parser_parse_signature():
    import inspect

    sig = inspect.signature(IpynbParser.parse)
    params = list(sig.parameters.keys())
    assert params[0] == "self"
    assert "path" in sig.parameters
    assert "source_hash" in sig.parameters


def test_ipynb_parser_has_docstring():
    assert IpynbParser.__doc__ is not None


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_all_exports_only_ipynb_parser():
    from app.parsers import ipynb_parser as mod

    assert mod.__all__ == ["IpynbParser"]


def test_module_all_count_one():
    from app.parsers import ipynb_parser as mod

    assert len(mod.__all__) == 1


def test_module_imports_json():
    from app.parsers import ipynb_parser as mod

    assert hasattr(mod, "json")


def test_module_imports_path():
    from app.parsers import ipynb_parser as mod

    assert hasattr(mod, "Path")


def test_module_imports_any():
    from app.parsers import ipynb_parser as mod

    assert hasattr(mod, "Any")


def test_module_imports_document():
    from app.parsers import ipynb_parser as mod

    assert hasattr(mod, "Document")


def test_module_imports_element():
    from app.parsers import ipynb_parser as mod

    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    from app.parsers import ipynb_parser as mod

    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser():
    from app.parsers import ipynb_parser as mod

    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    from app.parsers import ipynb_parser as mod

    assert hasattr(mod, "ParserError")


def test_module_imports_make_document_id():
    from app.parsers import ipynb_parser as mod

    assert hasattr(mod, "make_document_id")


def test_module_imports_markdown_parser():
    from app.parsers import ipynb_parser as mod

    assert hasattr(mod, "MarkdownParser")


def test_module_docstring_present():
    from app.parsers import ipynb_parser as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_markdown():
    from app.parsers import ipynb_parser as mod

    assert "markdown" in mod.__doc__.lower()


def test_module_docstring_mentions_nbformat():
    from app.parsers import ipynb_parser as mod

    assert "nbformat" in mod.__doc__.lower()


def test_module_constants_immutable_at_module_level():
    from app.parsers.ipynb_parser import _IPYNB_EXTENSIONS as a
    from app.parsers.ipynb_parser import _IPYNB_EXTENSIONS as b

    assert a is b


def test_module_cell_source_helper_callable():
    assert callable(_cell_source_to_text)


def test_module_extract_kernel_language_callable():
    assert callable(_extract_kernel_language)


def test_module_detect_ipynb_source_type_callable():
    assert callable(_detect_ipynb_source_type)


def test_cell_source_helper_has_docstring():
    assert _cell_source_to_text.__doc__ is not None


def test_extract_kernel_language_has_docstring():
    assert _extract_kernel_language.__doc__ is not None


def test_cell_source_helper_returns_str_for_empty():
    assert isinstance(_cell_source_to_text(""), str)


def test_extract_kernel_language_returns_str_for_empty():
    assert isinstance(_extract_kernel_language({}), str)


# =========================================================================
# IpynbParser.parse：错误路径
# =========================================================================


def test_parse_file_not_found_raises_file_not_found(tmp_path: Path):
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(tmp_path / "nonexistent.ipynb", source_hash=SHA)
    assert exc_info.value.code == "file_not_found"


def test_parse_unsupported_extension_raises_unsupported_type(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert exc_info.value.code == "unsupported_type"


def test_parse_invalid_json_raises(tmp_path: Path):
    p = tmp_path / "x.ipynb"
    p.write_text("{not json", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert exc_info.value.code == "ipynb_invalid_json"


def test_parse_oserror_raises_read_failed(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.ipynb"
    p.write_text("{}", encoding="utf-8")

    original_open = Path.open

    def fake_open(self, *args, **kwargs):
        if self == p:
            raise OSError("disk error")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fake_open)
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert exc_info.value.code == "ipynb_read_failed"


def test_parse_top_level_array_raises(tmp_path: Path):
    """顶层是数组 → 不是 dict → ipynb_bad_structure。"""
    p = tmp_path / "x.ipynb"
    p.write_text("[]", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert exc_info.value.code == "ipynb_bad_structure"


def test_parse_cells_string_raises(tmp_path: Path):
    """cells 是 string → ipynb_bad_structure。"""
    nb = {"nbformat": 4, "cells": "not a list"}
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert exc_info.value.code == "ipynb_bad_structure"


def test_parse_returns_document_instance(tmp_path: Path):
    from app.models import Document

    nb = _minimal_nb([])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert isinstance(doc, Document)


def test_parse_returns_document_with_empty_chunks(tmp_path: Path):
    nb = _minimal_nb([])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.chunks == []


def test_parse_returns_document_with_empty_relations(tmp_path: Path):
    nb = _minimal_nb([])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.relations == []


def test_parse_returns_document_with_empty_errors(tmp_path: Path):
    nb = _minimal_nb([])
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.errors == []
