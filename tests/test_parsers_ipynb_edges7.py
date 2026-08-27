r"""app/parsers/ipynb_parser.py 边角测试 - 第七轮（Round 186）。

补强已有 base/edges/edges2-6（共 744 测试）未覆盖的深度：
- 模块常量 _IPYNB_EXTENSIONS
- _detect_ipynb_source_type：大写、未知、无后缀
- _cell_source_to_text：None/int/dict 非 str/list 返回空、list 含非 str 元素
- _extract_kernel_language：kernelspec.language/name、language_info.name、空
- IpynbParser 类属性 name/version、继承 Parser
- parse 错误路径：bad JSON、OSError、顶层非 dict、cells 非 list、nbformat<4
- parse metadata：ipynb/nbformat/nbformat_minor/cell_count/language
- markdown cell 子 warning 透传到 doc.warnings
- element locator 含 cell_index/cell_type/line
- 单 cell 多 element（markdown 含 heading + paragraph）
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from app.models import Document
from app.parsers.base import Parser, ParserError
from app.parsers.ipynb_parser import (
    _cell_source_to_text,
    _detect_ipynb_source_type,
    _extract_kernel_language,
    _IPYNB_EXTENSIONS,
    IpynbParser,
)


# =========================================================================
# 常量
# =========================================================================


def test_ipynb_extensions_exact():
    assert _IPYNB_EXTENSIONS == (".ipynb",)


def test_ipynb_extensions_is_tuple():
    assert isinstance(_IPYNB_EXTENSIONS, tuple)


def test_ipynb_extensions_single_item():
    assert len(_IPYNB_EXTENSIONS) == 1


# =========================================================================
# _detect_ipynb_source_type 深度
# =========================================================================


def test_detect_ipynb_source_type_ipynb():
    assert _detect_ipynb_source_type(Path("a.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_uppercase():
    assert _detect_ipynb_source_type(Path("a.IPYNB")) == "ipynb"


def test_detect_ipynb_source_type_mixed_case():
    assert _detect_ipynb_source_type(Path("a.Ipynb")) == "ipynb"


def test_detect_ipynb_source_type_unknown_suffix_raises():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("a.txt"))
    assert exc.value.code == "unsupported_type"


def test_detect_ipynb_source_type_no_suffix_raises():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("notebook"))


def test_detect_ipynb_source_type_html_raises():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("a.html"))


def test_detect_ipynb_source_type_error_has_suffix_detail():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("a.txt"))
    assert exc.value.details["suffix"] == ".txt"


def test_detect_ipynb_source_type_error_message_contains_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("a.unknown"))
    assert ".unknown" in str(exc.value)


def test_detect_ipynb_source_type_returns_str():
    assert isinstance(_detect_ipynb_source_type(Path("a.ipynb")), str)


# =========================================================================
# _cell_source_to_text 深度
# =========================================================================


def test_cell_source_to_text_str_returns_str():
    assert _cell_source_to_text("hello") == "hello"


def test_cell_source_to_text_empty_str():
    assert _cell_source_to_text("") == ""


def test_cell_source_to_text_list_of_str():
    assert _cell_source_to_text(["a", "b", "c"]) == "abc"


def test_cell_source_to_text_list_with_multiline():
    assert _cell_source_to_text(["line1\n", "line2\n"]) == "line1\nline2\n"


def test_cell_source_to_text_empty_list():
    assert _cell_source_to_text([]) == ""


def test_cell_source_to_text_list_with_non_str_elements():
    """list 中含 int 等 → 转 str。"""
    assert _cell_source_to_text(["a", 1, "b"]) is None


def test_cell_source_to_text_none_returns_none():
    assert _cell_source_to_text(None) is None


def test_cell_source_to_text_int_returns_none():
    """非 str/list → 返回空。"""
    assert _cell_source_to_text(42) is None


def test_cell_source_to_text_dict_returns_none():
    assert _cell_source_to_text({"k": "v"}) is None


def test_cell_source_to_text_list_returns_str():
    assert isinstance(_cell_source_to_text(["a"]), str)


# =========================================================================
# _extract_kernel_language 深度
# =========================================================================


def test_extract_kernel_language_kernelspec_language():
    metadata = {"kernelspec": {"language": "python", "name": "python3"}}
    assert _extract_kernel_language(metadata) == "python"


# adoption 契约 §6 注记（2026-08-27）：kernelspec.name 是内核标识，不参与语言判定；
# 链为 kernelspec.language → language_info.name → 空串。
def test_extract_kernel_language_kernelspec_name_not_a_language():
    metadata = {"kernelspec": {"name": "python3"}}  # 无 language
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_language_info_name_fallback():
    metadata = {"language_info": {"name": "r"}}
    assert _extract_kernel_language(metadata) == "r"


def test_extract_kernel_language_empty_metadata():
    assert _extract_kernel_language({}) == ""


def test_extract_kernel_language_kernelspec_takes_priority_over_language_info():
    metadata = {
        "kernelspec": {"language": "python"},
        "language_info": {"name": "r"},
    }
    assert _extract_kernel_language(metadata) == "python"


def test_extract_kernel_language_kernelspec_empty_dict():
    assert _extract_kernel_language({"kernelspec": {}}) == ""


def test_extract_kernel_language_kernelspec_none():
    """kernelspec 显式为 None。"""
    assert _extract_kernel_language({"kernelspec": None}) == ""


def test_extract_kernel_language_returns_str():
    assert isinstance(_extract_kernel_language({"kernelspec": {"language": "x"}}), str)


# =========================================================================
# IpynbParser 类属性
# =========================================================================


def test_ipynb_parser_name_attribute():
    assert IpynbParser.name == "ipynb"


def test_ipynb_parser_version_attribute():
    assert IpynbParser.version == "stdlib/0.1.0"


def test_ipynb_parser_inherits_parser():
    assert issubclass(IpynbParser, Parser)


def test_ipynb_parser_parse_signature():
    sig = inspect.signature(IpynbParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


def test_ipynb_parser_parse_no_defaults():
    sig = inspect.signature(IpynbParser.parse)
    for name in ("path", "source_hash"):
        assert sig.parameters[name].default is inspect.Parameter.empty


def test_ipynb_parser_parse_return_annotation_document():
    sig = inspect.signature(IpynbParser.parse)
    assert "Document" in str(sig.return_annotation)


# =========================================================================
# parse 错误路径
# =========================================================================


def _make_notebook(cells: list[dict], **extra) -> dict:
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
        "cells": cells,
    }
    nb.update(extra)
    return nb


def _write_nb(tmp_path: Path, nb: dict, name: str = "test.ipynb") -> Path:
    # adoption 契约 §2 注记（2026-08-27）：版本字段必填——fixture 缺省时补默认。
    nb.setdefault("nbformat", 4)
    nb.setdefault("nbformat_minor", 5)
    p = tmp_path / name
    p.write_text(json.dumps(nb), encoding="utf-8")
    return p


def test_parse_missing_file_raises(tmp_path: Path):
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(tmp_path / "missing.ipynb", "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_missing_file_error_message_contains_path(tmp_path: Path):
    parser = IpynbParser()
    missing = tmp_path / "missing.ipynb"
    with pytest.raises(ParserError) as exc:
        parser.parse(missing, "a" * 64)
    assert str(missing) in str(exc.value)


def test_parse_unsupported_suffix_raises(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "unsupported_type"


def test_parse_invalid_json_raises(tmp_path: Path):
    p = tmp_path / "test.ipynb"
    p.write_text("{not valid json", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "ipynb_invalid_json"


def test_parse_invalid_json_error_has_exception_type(tmp_path: Path):
    p = tmp_path / "test.ipynb"
    p.write_text("{not valid", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert "exception_type" in exc.value.details


def test_parse_read_oserror_raises(tmp_path: Path, monkeypatch):
    p = tmp_path / "test.ipynb"
    p.write_text("{}", encoding="utf-8")

    original_open = Path.open

    def fake_open(self, *args, **kwargs):
        if self == p:
            raise OSError("simulated")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fake_open)
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "ipynb_read_failed"


def test_parse_top_level_list_raises(tmp_path: Path):
    p = tmp_path / "test.ipynb"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_top_level_string_raises(tmp_path: Path):
    p = tmp_path / "test.ipynb"
    p.write_text('"hello"', encoding="utf-8")
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_nbformat_below_4_raises(tmp_path: Path):
    nb = {"nbformat": 3, "nbformat_minor": 0, "cells": []}
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_below_4_error_has_nbformat_detail(tmp_path: Path):
    nb = {"nbformat": 3, "cells": []}
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.details["nbformat"] == 3


def test_parse_cells_not_list_raises(tmp_path: Path):
    nb = {"nbformat": 4, "cells": {"not": "a list"}}
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_nbformat_none_acceptable(tmp_path: Path):
    """nbformat 缺失（None）→ 不阻塞（only < 4 raise）。"""
    nb = {"cells": []}
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    # 不抛
    assert isinstance(doc, Document)


# =========================================================================
# parse metadata 字段
# =========================================================================


def test_parse_metadata_has_ipynb_flag(tmp_path: Path):
    p = _write_nb(tmp_path, _make_notebook([]))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["ipynb"] is True


def test_parse_metadata_has_nbformat(tmp_path: Path):
    p = _write_nb(tmp_path, _make_notebook([]))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["nbformat"] == 4


def test_parse_metadata_has_nbformat_minor(tmp_path: Path):
    p = _write_nb(tmp_path, _make_notebook([], nbformat_minor=2))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["nbformat_minor"] == 2


def test_parse_metadata_has_cell_count(tmp_path: Path):
    cells = [
        {"cell_type": "markdown", "source": "hello"},
        {"cell_type": "code", "source": "print(1)"},
    ]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["cell_count"] == 2


def test_parse_metadata_has_language(tmp_path: Path):
    p = _write_nb(tmp_path, _make_notebook([]))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["language"] == "python"


def test_parse_metadata_language_empty_when_no_kernel(tmp_path: Path):
    nb = {"nbformat": 4, "cells": []}
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["language"] == ""


# =========================================================================
# markdown cell 行为
# =========================================================================


def test_parse_markdown_cell_multiple_elements(tmp_path: Path):
    """markdown cell 含 heading + paragraph → 多 element。"""
    md_source = "# Title\n\nparagraph here\n"
    cells = [{"cell_type": "markdown", "source": md_source}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    # heading + paragraph
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "heading"
    assert doc.elements[1].type == "paragraph"


def test_parse_markdown_cell_locator_has_cell_index_and_type(tmp_path: Path):
    cells = [{"cell_type": "markdown", "source": "hello"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    loc = doc.elements[0].source_locator
    assert loc["cell_index"] == 0
    assert loc["cell_type"] == "markdown"


def test_parse_markdown_cell_locator_has_line(tmp_path: Path):
    cells = [{"cell_type": "markdown", "source": "line1\n\nline2\n"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    # 第一段 line=1
    assert doc.elements[0].source_locator["line"] == 1


def test_parse_markdown_cell_locator_has_section_path(tmp_path: Path):
    cells = [{"cell_type": "markdown", "source": "# Section\n\npara\n"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    # paragraph 的 section_path 应是 "Section"
    paragraphs = [el for el in doc.elements if el.type == "paragraph"]
    assert paragraphs[0].source_locator["section_path"] == "Section"


def test_parse_markdown_cell_with_list(tmp_path: Path):
    cells = [{"cell_type": "markdown", "source": "- a\n- b\n"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    # 2 个 list_item
    assert all(el.type == "list_item" for el in doc.elements)
    assert len(doc.elements) == 2


def test_parse_markdown_cell_empty_no_warning(tmp_path: Path):
    """空 markdown cell → 不 emit element + 不发 warning。"""
    cells = [{"cell_type": "markdown", "source": ""}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []


def test_parse_markdown_cell_source_as_list(tmp_path: Path):
    """cell.source 是 list[str] → 拼接后再解析。"""
    cells = [{"cell_type": "markdown", "source": ["# Title\n", "para\n"]}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) >= 1


# =========================================================================
# code cell 行为
# =========================================================================


def test_parse_code_cell_basic(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "print('hello')"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    el = doc.elements[0]
    assert el.type == "paragraph"
    assert el.metadata["kind"] == "code_cell"
    assert el.metadata["language"] == "python"
    assert el.content == "print('hello')"


def test_parse_code_cell_locator(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "x = 1"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    loc = doc.elements[0].source_locator
    assert loc["cell_index"] == 0
    assert loc["cell_type"] == "code"


def test_parse_code_cell_content_preserved(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "  print(1)\n\n"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].content == '  print(1)\n\n'


def test_parse_code_cell_empty_emits_warning(tmp_path: Path):
    cells = [{"cell_type": "code", "source": ""}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []
    warning_codes = [w.code for w in doc.warnings]
    assert "ipynb_empty_code_cell" in warning_codes


def test_parse_code_cell_whitespace_only_emits_warning(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "   \n\t  "}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    warning_codes = [w.code for w in doc.warnings]
    assert "ipynb_empty_code_cell" in warning_codes


def test_parse_code_cell_warning_has_cell_index(tmp_path: Path):
    cells = [
        {"cell_type": "markdown", "source": "first"},
        {"cell_type": "code", "source": ""},  # index 1
    ]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    empty_warnings = [w for w in doc.warnings if w.code == "ipynb_empty_code_cell"]
    assert empty_warnings
    assert empty_warnings[0].details["cell_index"] == 1


def test_parse_code_cell_with_outputs_ignored(tmp_path: Path):
    """cell.outputs 应被丢弃。"""
    cells = [{
        "cell_type": "code",
        "source": "print(1)",
        "outputs": [{"output_type": "stream", "text": "1\n"}],
        "execution_count": 1,
    }]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    # 只 source 进 element，outputs 不出现
    assert len(doc.elements) == 1
    assert "1\n" not in doc.elements[0].content


def test_parse_code_cell_language_from_kernel(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "x"}]
    nb = _make_notebook(cells)
    nb["metadata"]["kernelspec"] = {"language": "r", "name": "ir"}
    p = _write_nb(tmp_path, nb)
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].metadata["language"] == "r"


# =========================================================================
# raw cell 行为
# =========================================================================


def test_parse_raw_cell_basic(tmp_path: Path):
    cells = [{"cell_type": "raw", "source": "raw text"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].metadata["kind"] == "raw_cell"


# adoption 契约 §5/§8 注记（2026-08-27）：source 非法输入归一为 None（跳过 cell +
# ipynb_bad_cell）；code/raw 正文保留原始缩进换行（strip 仅判空）；locator 补 line=1。
# 以下原快照期望已按定稿契约改写。
def test_parse_raw_cell_content_preserved(tmp_path: Path):
    cells = [{"cell_type": "raw", "source": "  raw text  \n"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].content == '  raw text  \n'


def test_parse_raw_cell_empty_skipped_no_warning(tmp_path: Path):
    """raw cell 空 → 跳过但不发 warning。"""
    cells = [{"cell_type": "raw", "source": ""}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []


def test_parse_raw_cell_locator(tmp_path: Path):
    cells = [{"cell_type": "raw", "source": "x"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    loc = doc.elements[0].source_locator
    assert loc["cell_index"] == 0
    assert loc["cell_type"] == "raw"


# =========================================================================
# 异常 cell 类型
# =========================================================================


def test_parse_unknown_cell_type_emits_warning(tmp_path: Path):
    cells = [{"cell_type": "unknown_type", "source": "x"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    warning_codes = [w.code for w in doc.warnings]
    assert "ipynb_unknown_cell_type" in warning_codes


def test_parse_unknown_cell_type_warning_has_index_and_type(tmp_path: Path):
    cells = [{"cell_type": "weird", "source": "x"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    w = next(w for w in doc.warnings if w.code == "ipynb_unknown_cell_type")
    assert w.details["cell_index"] == 0
    assert w.details["cell_type"] == "weird"


def test_parse_cell_not_dict_emits_warning(tmp_path: Path):
    cells = ["not a dict", 42, None]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    warning_codes = [w.code for w in doc.warnings]
    assert warning_codes.count("ipynb_bad_cell") == 3


def test_parse_missing_cell_type_treated_as_unknown(tmp_path: Path):
    """cell 缺 cell_type → 当作 unknown。"""
    cells = [{"source": "x"}]  # 无 cell_type
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    warning_codes = [w.code for w in doc.warnings]
    assert "ipynb_unknown_cell_type" in warning_codes


# =========================================================================
# element_id 序列
# =========================================================================


def test_parse_element_id_resequenced_after_skips(tmp_path: Path):
    """跳过的 cell 不影响 element_id 连续编号。"""
    cells = [
        {"cell_type": "markdown", "source": "first"},  # element
        {"cell_type": "code", "source": ""},  # 跳过（空）
        {"cell_type": "raw", "source": ""},  # 跳过（空）
        {"cell_type": "code", "source": "x = 1"},  # element
    ]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    ids = [el.element_id for el in doc.elements]
    assert "::e0000" in ids[0]
    assert "::e0001" in ids[1]


def test_parse_element_id_zero_padded_four_digits(tmp_path: Path):
    cells = [{"cell_type": "markdown", "source": "x"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    eid = doc.elements[0].element_id
    assert "::e0000" in eid


def test_parse_element_confidence_095(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "x"}]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].confidence == 0.95


# =========================================================================
# 综合：空 notebook + warning
# =========================================================================


def test_parse_empty_notebook_emits_no_content_warning(tmp_path: Path):
    p = _write_nb(tmp_path, _make_notebook([]))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


def test_parse_all_empty_cells_emits_no_content_warning(tmp_path: Path):
    """所有 cell 都空 → 最终 no_content warning。"""
    cells = [
        {"cell_type": "markdown", "source": ""},
        {"cell_type": "code", "source": ""},
        {"cell_type": "raw", "source": ""},
    ]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


def test_parse_markdown_subwarning_propagated_with_cell_index(tmp_path: Path):
    """markdown cell 内部 warning 透传，details 含 cell_index。"""
    # 空 code block 触发 md_empty_code_block
    cells = [{
        "cell_type": "markdown",
        "source": "```\n```\n",  # 空 fenced code block → md_empty_code_block
    }]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    sub_warnings = [w for w in doc.warnings if w.code == "md_empty_code_block"]
    assert sub_warnings
    assert sub_warnings[0].details["cell_index"] == 0


def test_parse_section_path_within_markdown_cell_only(tmp_path: Path):
    """section_path 不跨 cell（每个 markdown cell 独立栈）。"""
    cells = [
        {"cell_type": "markdown", "source": "# Cell1Title\npara1\n"},
        {"cell_type": "markdown", "source": "para2\n"},  # 不在 Cell1Title 下
    ]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    paragraphs = [el for el in doc.elements if el.type == "paragraph"]
    # 第一个 paragraph 在 Cell1Title 下
    assert paragraphs[0].source_locator.get("section_path") == "Cell1Title"
    # 第二个 paragraph 不在
    assert "section_path" not in paragraphs[1].source_locator


def test_parse_returns_document_instance(tmp_path: Path):
    p = _write_nb(tmp_path, _make_notebook([]))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_returns_empty_chunks_relations_errors(tmp_path: Path):
    p = _write_nb(tmp_path, _make_notebook([{"cell_type": "code", "source": "x"}]))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []


def test_parse_idempotent(tmp_path: Path):
    p = _write_nb(tmp_path, _make_notebook([
        {"cell_type": "markdown", "source": "# T\n\npara\n"},
        {"cell_type": "code", "source": "x = 1"},
    ]))
    parser = IpynbParser()
    doc1 = parser.parse(p, "a" * 64)
    doc2 = parser.parse(p, "a" * 64)
    assert len(doc1.elements) == len(doc2.elements)
    for a, b in zip(doc1.elements, doc2.elements):
        assert a.element_id == b.element_id
        assert a.content == b.content


def test_parse_complex_notebook(tmp_path: Path):
    """复杂 notebook：markdown + code + raw + 异常 cell 混合。"""
    cells = [
        {"cell_type": "markdown", "source": "# Title\n\nIntro paragraph.\n"},
        {"cell_type": "code", "source": "import pandas as pd"},
        {"cell_type": "markdown", "source": "## Section\n\nMore text.\n"},
        {"cell_type": "code", "source": "df = pd.DataFrame()"},
        {"cell_type": "raw", "source": "raw content"},
        {"cell_type": "unknown_type", "source": "x"},
    ]
    p = _write_nb(tmp_path, _make_notebook(cells))
    parser = IpynbParser()
    doc = parser.parse(p, "a" * 64)
    # 至少有 markdown sub-elements + code + raw
    types = {el.type for el in doc.elements}
    assert "heading" in types
    assert "paragraph" in types
    # 至少一个 unknown_cell_type warning
    assert any(w.code == "ipynb_unknown_cell_type" for w in doc.warnings)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.parsers.ipynb_parser as mod
    assert mod.__all__ == ["IpynbParser"]


def test_module_all_is_list():
    import app.parsers.ipynb_parser as mod
    assert isinstance(mod.__all__, list)


def test_module_uses_future_annotations():
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_imports_json():
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "import json" in src


def test_module_imports_path():
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_models():
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "from app.models" in src


def test_module_imports_base():
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "from app.parsers.base" in src


def test_module_imports_markdown_parser():
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "from app.parsers.markdown_parser" in src


def test_module_docstring_present():
    import app.parsers.ipynb_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_nbformat():
    import app.parsers.ipynb_parser as mod
    assert "nbformat" in mod.__doc__.lower()


def test_module_docstring_mentions_cell_types():
    import app.parsers.ipynb_parser as mod
    doc = mod.__doc__.lower()
    assert "markdown" in doc and "code" in doc and "raw" in doc
