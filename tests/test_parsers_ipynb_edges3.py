"""app/parsers/ipynb_parser.py 边角测试 - 第三轮（Round 103）。

补强已有 base/edges/edges2（共 323 个测试）未覆盖的深度路径：
- _cell_source_to_text：list[str]/str/None/int-in-list/empty-list 各路径
- _extract_kernel_language 优先级链：kernelspec.language > kernelspec.name >
  language_info.name > ""
- 多 markdown cell 的 cell_index 独立追踪、section_path 各自重置
- markdown cell 警告透传：cell_index 注入 details
- code cell：multilingual source、language 来自 kernelspec
- raw cell：content stripped、empty 静默跳过
- nbformat 字段：missing/0/3/4/5/None、minor missing
- metadata 字段：kernelspec.language_info.name 各种组合
- _detect_ipynb_source_type 大写扩展名、拒绝其他
- 错误码：ipynb_invalid_json、ipynb_read_failed、ipynb_bad_structure（非 dict 顶层、
  cells 非 list）、ipynb_unsupported_version、ipynb_bad_cell、ipynb_unknown_cell_type、
  ipynb_empty_code_cell、ipynb_no_content

不修改任何源码。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.parsers.base import ParserError
from app.parsers.ipynb_parser import (
    _IPYNB_EXTENSIONS,
    IpynbParser,
    _cell_source_to_text,
    _detect_ipynb_source_type,
    _extract_kernel_language,
)


# =========================================================================
# 辅助
# =========================================================================


def _write_ipynb(tmp_path: Path, nb: dict, name: str = "test.ipynb") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(nb), encoding="utf-8")
    return p


def _minimal_nb(cells: list, metadata: dict | None = None) -> dict:
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": metadata or {},
        "cells": cells,
    }
    return nb


def _parse(tmp_path: Path, nb: dict, name: str = "test.ipynb"):
    p = _write_ipynb(tmp_path, nb, name)
    return IpynbParser().parse(p, source_hash="a" * 64)


# =========================================================================
# _cell_source_to_text 深度
# =========================================================================


def test_cell_source_str_returns_str():
    assert _cell_source_to_text("hello") == "hello"


def test_cell_source_list_returns_joined():
    assert _cell_source_to_text(["a", "b", "c"]) == "abc"


def test_cell_source_list_with_newline_parts():
    parts = ["line1\n", "line2\n", "line3"]
    assert _cell_source_to_text(parts) == "line1\nline2\nline3"


def test_cell_source_empty_list():
    assert _cell_source_to_text([]) == ""


def test_cell_source_none_returns_empty():
    assert _cell_source_to_text(None) == ""


def test_cell_source_int_returns_empty():
    """非 str/list → 空。"""
    assert _cell_source_to_text(42) == ""


def test_cell_source_list_with_non_str_elements():
    """list[str|non-str] → 全部转 str 再 join。"""
    assert _cell_source_to_text([1, 2, 3]) == "123"


def test_cell_source_list_with_mixed_types():
    assert _cell_source_to_text(["a", 1, True]) == "a1True"


# =========================================================================
# _extract_kernel_language 深度
# =========================================================================


def test_extract_lang_prio_kernelspec_language_first():
    md = {"kernelspec": {"language": "python", "name": "irrelevant"}}
    assert _extract_kernel_language(md) == "python"


def test_extract_lang_prio_kernelspec_name_when_no_language():
    md = {"kernelspec": {"name": "fallback-name"}}
    assert _extract_kernel_language(md) == "fallback-name"


def test_extract_lang_prio_language_info_when_no_kernelspec():
    md = {"language_info": {"name": "ruby"}}
    assert _extract_kernel_language(md) == "ruby"


def test_extract_lang_returns_empty_for_empty_metadata():
    assert _extract_kernel_language({}) == ""


def test_extract_lang_returns_empty_for_none_metadata():
    """_extract_kernel_language 不接受 None（实际调用方传 dict）。

    验证：parse() 总是用 nb.get('metadata') or {} 兜底，
    所以 _extract_kernel_language 内部假设 dict。
    """
    # 这个测试记录函数的契约：不接受 None
    with pytest.raises(AttributeError):
        _extract_kernel_language(None)


def test_extract_lang_returns_empty_when_called_from_parse_with_none_metadata(tmp_path: Path):
    """parse() 路径：metadata=None 会被 nb.get('metadata') or {} 兜底为 {}。"""
    nb = _minimal_nb([])
    nb["metadata"] = None
    doc = _parse(tmp_path, nb)
    # 不抛异常，language 为 ""
    assert doc.metadata["language"] == ""


def test_extract_lang_returns_empty_for_kernelspec_no_lang_no_name():
    md = {"kernelspec": {}}
    assert _extract_kernel_language(md) == ""


def test_extract_lang_returns_empty_for_language_info_no_name():
    md = {"language_info": {}}
    assert _extract_kernel_language(md) == ""


def test_extract_lang_kernelspec_language_overrides_language_info():
    """kernelspec.language 优先于 language_info.name。"""
    md = {
        "kernelspec": {"language": "python", "name": "py"},
        "language_info": {"name": "ruby"},
    }
    assert _extract_kernel_language(md) == "python"


def test_extract_lang_kernelspec_name_overrides_language_info():
    """kernelspec.name 优先于 language_info.name。"""
    md = {
        "kernelspec": {"name": "julia"},
        "language_info": {"name": "ruby"},
    }
    assert _extract_kernel_language(md) == "julia"


def test_extract_lang_empty_kernelspec_falls_back_to_language_info():
    md = {
        "kernelspec": {},
        "language_info": {"name": "go"},
    }
    assert _extract_kernel_language(md) == "go"


# =========================================================================
# _detect_ipynb_source_type 深度
# =========================================================================


def test_detect_ipynb_source_type_accepts_lowercase():
    assert _detect_ipynb_source_type(Path("test.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_accepts_uppercase():
    assert _detect_ipynb_source_type(Path("test.IPYNB")) == "ipynb"


def test_detect_ipynb_source_type_accepts_mixed_case():
    assert _detect_ipynb_source_type(Path("test.Ipynb")) == "ipynb"


def test_detect_ipynb_source_type_rejects_html():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("test.html"))


def test_detect_ipynb_source_type_rejects_md():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("test.md"))


def test_detect_ipynb_source_type_rejects_no_suffix():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("noext"))


def test_detect_ipynb_source_type_error_code():
    with pytest.raises(ParserError) as ei:
        _detect_ipynb_source_type(Path("test.unknown"))
    assert ei.value.code == "unsupported_type"


def test_ipynb_extensions_exact_one_entry():
    assert _IPYNB_EXTENSIONS == (".ipynb",)


# =========================================================================
# parse: nbformat 字段
# =========================================================================


def test_parse_nbformat_3_raises(tmp_path: Path):
    nb = _minimal_nb([])
    nb["nbformat"] = 3
    with pytest.raises(ParserError) as ei:
        _parse(tmp_path, nb)
    assert ei.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_0_raises(tmp_path: Path):
    nb = _minimal_nb([])
    nb["nbformat"] = 0
    with pytest.raises(ParserError) as ei:
        _parse(tmp_path, nb)
    assert ei.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_negative_raises(tmp_path: Path):
    nb = _minimal_nb([])
    nb["nbformat"] = -1
    with pytest.raises(ParserError) as ei:
        _parse(tmp_path, nb)
    assert ei.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_4_supported(tmp_path: Path):
    doc = _parse(tmp_path, _minimal_nb([]))
    assert doc.metadata["nbformat"] == 4


def test_parse_nbformat_5_supported(tmp_path: Path):
    nb = _minimal_nb([])
    nb["nbformat"] = 5
    doc = _parse(tmp_path, nb)
    assert doc.metadata["nbformat"] == 5


def test_parse_nbformat_10_supported(tmp_path: Path):
    """任何 nbformat >= 4 都支持。"""
    nb = _minimal_nb([])
    nb["nbformat"] = 10
    doc = _parse(tmp_path, nb)
    assert doc.metadata["nbformat"] == 10


def test_parse_nbformat_missing_supported(tmp_path: Path):
    nb = _minimal_nb([])
    del nb["nbformat"]
    doc = _parse(tmp_path, nb)
    # nbformat 缺失 → metadata.nbformat = None
    assert doc.metadata["nbformat"] is None


def test_parse_nbformat_minor_missing_is_none(tmp_path: Path):
    nb = _minimal_nb([])
    del nb["nbformat_minor"]
    doc = _parse(tmp_path, nb)
    assert doc.metadata["nbformat_minor"] is None


def test_parse_nbformat_minor_value_preserved(tmp_path: Path):
    nb = _minimal_nb([])
    nb["nbformat_minor"] = 4
    doc = _parse(tmp_path, nb)
    assert doc.metadata["nbformat_minor"] == 4


# =========================================================================
# parse: 顶层结构
# =========================================================================


def test_parse_top_level_not_dict_raises(tmp_path: Path):
    """JSON 顶层是 list → ipynb_bad_structure。"""
    p = tmp_path / "test.ipynb"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_top_level_string_raises(tmp_path: Path):
    p = tmp_path / "test.ipynb"
    p.write_text('"hello"', encoding="utf-8")
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_top_level_int_raises(tmp_path: Path):
    p = tmp_path / "test.ipynb"
    p.write_text("42", encoding="utf-8")
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_top_level_null_raises(tmp_path: Path):
    p = tmp_path / "test.ipynb"
    p.write_text("null", encoding="utf-8")
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_cells_not_list_raises(tmp_path: Path):
    nb = _minimal_nb([])
    nb["cells"] = "not a list"
    with pytest.raises(ParserError) as ei:
        _parse(tmp_path, nb)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_cells_dict_raises(tmp_path: Path):
    nb = _minimal_nb([])
    nb["cells"] = {"key": "value"}
    with pytest.raises(ParserError) as ei:
        _parse(tmp_path, nb)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_cells_null_treated_as_empty(tmp_path: Path):
    nb = _minimal_nb([])
    nb["cells"] = None
    doc = _parse(tmp_path, nb)
    no_content = [w for w in doc.warnings if w.code == "ipynb_no_content"]
    assert len(no_content) == 1


def test_parse_cells_missing_treated_as_empty(tmp_path: Path):
    nb = _minimal_nb([])
    del nb["cells"]
    doc = _parse(tmp_path, nb)
    no_content = [w for w in doc.warnings if w.code == "ipynb_no_content"]
    assert len(no_content) == 1


# =========================================================================
# parse: markdown cell 深度
# =========================================================================


def test_parse_markdown_cell_emits_multiple_elements(tmp_path: Path):
    nb = _minimal_nb([
        {
            "cell_type": "markdown",
            "source": "# Title\n\nparagraph text\n",
        },
    ])
    doc = _parse(tmp_path, nb)
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types


def test_parse_markdown_cell_locator_has_cell_index_and_type(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "markdown", "source": "# H1\n"},
    ])
    doc = _parse(tmp_path, nb)
    h = [e for e in doc.elements if e.type == "heading"][0]
    assert h.source_locator["cell_index"] == 0
    assert h.source_locator["cell_type"] == "markdown"


def test_parse_two_markdown_cells_independent_section_path(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "markdown", "source": "# Cell1 Title\npara1\n"},
        {"cell_type": "markdown", "source": "# Cell2 Title\npara2\n"},
    ])
    doc = _parse(tmp_path, nb)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 2
    # 各自的 section_path 只含本 cell 的标题
    assert paras[0].source_locator["cell_index"] == 0
    assert paras[0].source_locator["section_path"] == "Cell1 Title"
    assert paras[1].source_locator["cell_index"] == 1
    assert paras[1].source_locator["section_path"] == "Cell2 Title"


def test_parse_markdown_cell_warning_propagates_with_cell_index(tmp_path: Path):
    """markdown cell 内的 warning（如 empty code block）应透传到 doc.warnings。"""
    nb = _minimal_nb([
        {"cell_type": "markdown", "source": "```\n```\n"},
    ])
    doc = _parse(tmp_path, nb)
    empty_warnings = [w for w in doc.warnings if w.code == "md_empty_code_block"]
    assert len(empty_warnings) == 1
    # details 含 cell_index
    assert empty_warnings[0].details.get("cell_index") == 0


def test_parse_markdown_cell_warning_reason_includes_cell_index(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "markdown", "source": "```\n```\n"},
    ])
    doc = _parse(tmp_path, nb)
    w = [w for w in doc.warnings if w.code == "md_empty_code_block"][0]
    assert "cell #0" in w.reason


def test_parse_markdown_cell_with_table(tmp_path: Path):
    nb = _minimal_nb([
        {
            "cell_type": "markdown",
            "source": "| h1 | h2 |\n| --- | --- |\n| a | b |\n",
        },
    ])
    doc = _parse(tmp_path, nb)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1


def test_parse_markdown_cell_with_image(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "markdown", "source": "![alt](url.png)\n"},
    ])
    doc = _parse(tmp_path, nb)
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 1


def test_parse_markdown_cell_empty_source_no_elements(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "markdown", "source": ""},
    ])
    doc = _parse(tmp_path, nb)
    assert doc.elements == []
    no_content = [w for w in doc.warnings if w.code == "ipynb_no_content"]
    assert len(no_content) == 1


def test_parse_markdown_cell_source_as_list(tmp_path: Path):
    nb = _minimal_nb([
        {
            "cell_type": "markdown",
            "source": ["# Title\n", "para text"],
        },
    ])
    doc = _parse(tmp_path, nb)
    types = [e.type for e in doc.elements]
    assert "heading" in types


# =========================================================================
# parse: code cell 深度
# =========================================================================


def test_parse_code_cell_basic(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "code", "source": "print('hello')\n"},
    ])
    doc = _parse(tmp_path, nb)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].metadata["kind"] == "code_cell"


def test_parse_code_cell_language_from_kernelspec(tmp_path: Path):
    nb = _minimal_nb(
        [{"cell_type": "code", "source": "x = 1\n"}],
        metadata={"kernelspec": {"language": "python", "name": "python3"}},
    )
    doc = _parse(tmp_path, nb)
    code = [e for e in doc.elements if e.metadata.get("kind") == "code_cell"][0]
    assert code.metadata["language"] == "python"


def test_parse_code_cell_language_from_language_info(tmp_path: Path):
    nb = _minimal_nb(
        [{"cell_type": "code", "source": "x = 1\n"}],
        metadata={"language_info": {"name": "julia"}},
    )
    doc = _parse(tmp_path, nb)
    code = [e for e in doc.elements if e.metadata.get("kind") == "code_cell"][0]
    assert code.metadata["language"] == "julia"


def test_parse_code_cell_no_metadata_language_empty(tmp_path: Path):
    nb = _minimal_nb(
        [{"cell_type": "code", "source": "x = 1\n"}],
        metadata={},
    )
    doc = _parse(tmp_path, nb)
    code = [e for e in doc.elements if e.metadata.get("kind") == "code_cell"][0]
    assert code.metadata["language"] == ""


def test_parse_code_cell_locator_has_no_line(tmp_path: Path):
    """code cell 不进 MarkdownParser，locator 只有 cell_index + cell_type。"""
    nb = _minimal_nb([
        {"cell_type": "code", "source": "x = 1\n"},
    ])
    doc = _parse(tmp_path, nb)
    code = doc.elements[0]
    assert "line" not in code.source_locator


def test_parse_code_cell_locator_has_cell_index_and_type(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "code", "source": "x = 1\n"},
    ])
    doc = _parse(tmp_path, nb)
    code = doc.elements[0]
    assert code.source_locator["cell_index"] == 0
    assert code.source_locator["cell_type"] == "code"


def test_parse_empty_code_cell_emits_warning(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "code", "source": ""},
    ])
    doc = _parse(tmp_path, nb)
    empty_code_warnings = [w for w in doc.warnings if w.code == "ipynb_empty_code_cell"]
    assert len(empty_code_warnings) == 1


def test_parse_whitespace_only_code_cell_emits_warning(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "code", "source": "   \n\t  "},
    ])
    doc = _parse(tmp_path, nb)
    empty_code_warnings = [w for w in doc.warnings if w.code == "ipynb_empty_code_cell"]
    assert len(empty_code_warnings) == 1


def test_parse_empty_code_cell_skipped_no_element(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "code", "source": ""},
    ])
    doc = _parse(tmp_path, nb)
    # 空代码 cell 跳过，不 emit element
    assert doc.elements == []
    # no_content 触发
    no_content = [w for w in doc.warnings if w.code == "ipynb_no_content"]
    assert len(no_content) == 1


# =========================================================================
# parse: raw cell 深度
# =========================================================================


def test_parse_raw_cell_basic(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "raw", "source": "raw content\n"},
    ])
    doc = _parse(tmp_path, nb)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].metadata["kind"] == "raw_cell"


def test_parse_raw_cell_locator_has_cell_index_and_type(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "raw", "source": "raw\n"},
    ])
    doc = _parse(tmp_path, nb)
    raw = doc.elements[0]
    assert raw.source_locator["cell_index"] == 0
    assert raw.source_locator["cell_type"] == "raw"


def test_parse_raw_cell_content_stripped(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "raw", "source": "  raw with spaces  \n"},
    ])
    doc = _parse(tmp_path, nb)
    raw = doc.elements[0]
    assert raw.content == "raw with spaces"


def test_parse_raw_cell_empty_skipped_silently(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "raw", "source": ""},
    ])
    doc = _parse(tmp_path, nb)
    # 空 raw cell 静默跳过（不警告）
    raw_warnings = [w for w in doc.warnings if "raw" in w.code.lower()]
    assert raw_warnings == []
    # 但 no_content 触发
    no_content = [w for w in doc.warnings if w.code == "ipynb_no_content"]
    assert len(no_content) == 1


def test_parse_raw_cell_whitespace_only_skipped(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "raw", "source": "  \n  "},
    ])
    doc = _parse(tmp_path, nb)
    raw_warnings = [w for w in doc.warnings if "raw" in w.code.lower()]
    assert raw_warnings == []


# =========================================================================
# parse: cell 错误处理
# =========================================================================


def test_parse_cell_not_dict_emits_warning(tmp_path: Path):
    nb = _minimal_nb([
        "not a dict",  # cell 不是 dict
    ])
    doc = _parse(tmp_path, nb)
    bad_cell_warnings = [w for w in doc.warnings if w.code == "ipynb_bad_cell"]
    assert len(bad_cell_warnings) == 1


def test_parse_cell_not_dict_warning_has_cell_index(tmp_path: Path):
    nb = _minimal_nb(["str cell"])
    doc = _parse(tmp_path, nb)
    w = [w for w in doc.warnings if w.code == "ipynb_bad_cell"][0]
    assert w.details.get("cell_index") == 0


def test_parse_unknown_cell_type_emits_warning(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "unknown_type", "source": "x"},
    ])
    doc = _parse(tmp_path, nb)
    unknown_warnings = [w for w in doc.warnings if w.code == "ipynb_unknown_cell_type"]
    assert len(unknown_warnings) == 1


def test_parse_unknown_cell_type_warning_has_cell_type_in_details(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "weird", "source": "x"},
    ])
    doc = _parse(tmp_path, nb)
    w = [w for w in doc.warnings if w.code == "ipynb_unknown_cell_type"][0]
    assert w.details.get("cell_type") == "weird"


def test_parse_cell_missing_cell_type_defaults_unknown(tmp_path: Path):
    """cell 没 cell_type 字段 → ct = 'unknown'。"""
    nb = _minimal_nb([
        {"source": "x"},
    ])
    doc = _parse(tmp_path, nb)
    unknown_warnings = [w for w in doc.warnings if w.code == "ipynb_unknown_cell_type"]
    assert len(unknown_warnings) == 1


def test_parse_cell_cell_type_null_defaults_unknown(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": None, "source": "x"},
    ])
    doc = _parse(tmp_path, nb)
    unknown_warnings = [w for w in doc.warnings if w.code == "ipynb_unknown_cell_type"]
    assert len(unknown_warnings) == 1


# =========================================================================
# parse: pipeline 错误
# =========================================================================


def test_parse_missing_file_raises_file_not_found(tmp_path: Path):
    p = tmp_path / "no.ipynb"
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "file_not_found"


def test_parse_invalid_json_raises(tmp_path: Path):
    p = tmp_path / "test.ipynb"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "ipynb_invalid_json"


def test_parse_oserror_raises_read_failed(tmp_path: Path, monkeypatch):
    p = _write_ipynb(tmp_path, _minimal_nb([]))

    real_open = Path.open

    def _raise_os(self, *args, **kwargs):
        if self == p:
            raise OSError("disk error")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _raise_os)
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "ipynb_read_failed"


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello")
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "unsupported_type"


# =========================================================================
# parse: 返回 Document 不变量
# =========================================================================


def test_parse_returns_document_with_empty_chunks(tmp_path: Path):
    doc = _parse(tmp_path, _minimal_nb([]))
    assert doc.chunks == []


def test_parse_returns_document_with_empty_relations(tmp_path: Path):
    doc = _parse(tmp_path, _minimal_nb([]))
    assert doc.relations == []


def test_parse_returns_document_with_empty_errors(tmp_path: Path):
    doc = _parse(tmp_path, _minimal_nb([]))
    assert doc.errors == []


def test_parse_metadata_has_ipynb_flag(tmp_path: Path):
    doc = _parse(tmp_path, _minimal_nb([]))
    assert doc.metadata.get("ipynb") is True


def test_parse_metadata_has_cell_count(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "markdown", "source": "x"},
        {"cell_type": "code", "source": "y"},
        {"cell_type": "raw", "source": "z"},
    ])
    doc = _parse(tmp_path, nb)
    assert doc.metadata["cell_count"] == 3


def test_parse_metadata_has_language(tmp_path: Path):
    nb = _minimal_nb(
        [],
        metadata={"kernelspec": {"language": "python"}},
    )
    doc = _parse(tmp_path, nb)
    assert doc.metadata["language"] == "python"


def test_parse_source_type_ipynb(tmp_path: Path):
    doc = _parse(tmp_path, _minimal_nb([]))
    assert doc.source_type == "ipynb"


def test_parse_parser_name_attribute(tmp_path: Path):
    doc = _parse(tmp_path, _minimal_nb([]))
    assert doc.parser_name == "ipynb"


def test_parse_parser_version_attribute(tmp_path: Path):
    doc = _parse(tmp_path, _minimal_nb([]))
    assert doc.parser_version == "stdlib/0.1.0"


# =========================================================================
# parse: element_id 连续编号
# =========================================================================


def test_parse_element_ids_continuous_across_cells(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "markdown", "source": "# H1\npara1\n"},
        {"cell_type": "code", "source": "x = 1\n"},
        {"cell_type": "raw", "source": "raw text\n"},
    ])
    doc = _parse(tmp_path, nb)
    ids = [e.element_id for e in doc.elements]
    # 提取末尾的 4 位数字
    nums = [int(eid.split("::e")[1]) for eid in ids]
    assert nums == sorted(nums)
    assert nums[0] == 0


def test_parse_element_ids_unique(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "markdown", "source": "# H1\npara1\n"},
        {"cell_type": "code", "source": "x = 1\n"},
    ])
    doc = _parse(tmp_path, nb)
    ids = [e.element_id for e in doc.elements]
    assert len(set(ids)) == len(ids)


# =========================================================================
# 完整 notebook e2e
# =========================================================================


def test_parse_complex_notebook_emits_mixed_types(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "markdown", "source": "# Title\nintro text\n"},
        {"cell_type": "code", "source": "print(1)\n"},
        {"cell_type": "raw", "source": "raw\n"},
        {"cell_type": "markdown", "source": "## Sub\n- item\n"},
    ])
    doc = _parse(tmp_path, nb)
    types = set(e.type for e in doc.elements)
    assert "heading" in types
    assert "paragraph" in types
    assert "list_item" in types


def test_parse_complex_notebook_locator_correctness(tmp_path: Path):
    nb = _minimal_nb([
        {"cell_type": "code", "source": "x = 1\n"},
        {"cell_type": "markdown", "source": "# H1\n"},
    ])
    doc = _parse(tmp_path, nb)
    code_el = [e for e in doc.elements if e.source_locator["cell_type"] == "code"][0]
    md_el = [e for e in doc.elements if e.source_locator["cell_type"] == "markdown"][0]
    # code_el 在 cell 0
    assert code_el.source_locator["cell_index"] == 0
    # md_el 在 cell 1
    assert md_el.source_locator["cell_index"] == 1


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_contains_ipynb_parser():
    from app.parsers import ipynb_parser
    assert "IpynbParser" in ipynb_parser.__all__


def test_module_all_only_lists_ipynb_parser():
    from app.parsers import ipynb_parser
    assert set(ipynb_parser.__all__) == {"IpynbParser"}


def test_module_imports_json():
    from app.parsers import ipynb_parser
    assert hasattr(ipynb_parser, "json")


def test_module_imports_path():
    from app.parsers import ipynb_parser
    assert hasattr(ipynb_parser, "Path")


def test_module_imports_document():
    from app.parsers import ipynb_parser
    assert hasattr(ipynb_parser, "Document")


def test_module_imports_element():
    from app.parsers import ipynb_parser
    assert hasattr(ipynb_parser, "Element")


def test_module_imports_warning_record():
    from app.parsers import ipynb_parser
    assert hasattr(ipynb_parser, "WarningRecord")


def test_module_imports_parser_base():
    from app.parsers import ipynb_parser
    assert hasattr(ipynb_parser, "Parser")


def test_module_imports_parser_error():
    from app.parsers import ipynb_parser
    assert hasattr(ipynb_parser, "ParserError")


def test_module_imports_make_document_id():
    from app.parsers import ipynb_parser
    assert hasattr(ipynb_parser, "make_document_id")


def test_module_imports_markdown_parser():
    from app.parsers import ipynb_parser
    assert hasattr(ipynb_parser, "MarkdownParser")


def test_ipynb_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(IpynbParser, Parser)


def test_ipynb_parser_name_value():
    assert IpynbParser.name == "ipynb"


def test_ipynb_parser_version_value():
    assert IpynbParser.version == "stdlib/0.1.0"


def test_ipynb_parser_has_parse_callable():
    assert callable(IpynbParser.parse)
