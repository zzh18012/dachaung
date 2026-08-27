"""Jupyter Notebook (.ipynb) parser 的单元测试 + 端到端 pipeline 测试。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.models import Document
from app.parsers import ParserError
from app.parsers.ipynb_parser import IpynbParser


VENV_PYTHON = str(
    Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PYTHON = VENV_PYTHON if Path(VENV_PYTHON).is_file() else sys.executable


def _nb(cells: list[dict], language: str = "python") -> dict:
    """构造最小 nbformat 4 notebook。"""
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": f"{language.capitalize()} 3",
                "language": language,
                "name": f"{language}3",
            },
            "language_info": {"name": language},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _write_nb(tmp_path: Path, name: str, nb: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    return p


# ---------- 基础 cell 类型 ----------


def test_ipynb_markdown_cell_emits_heading_and_paragraph(tmp_path: Path):
    nb = _nb([
        {"cell_type": "markdown", "source": ["# Title\n", "Body text."], "metadata": {}},
    ])
    p = _write_nb(tmp_path, "a.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.source_type == "ipynb"
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types
    # heading 内容
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 1
    assert headings[0].content == "Title"


def test_ipynb_code_cell_emits_paragraph_with_kind(tmp_path: Path):
    nb = _nb([
        {"cell_type": "code", "source": "print('hi')\nx = 1", "metadata": {}, "outputs": [], "execution_count": 1},
    ])
    p = _write_nb(tmp_path, "b.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="b" * 64)
    code = [e for e in doc.elements if e.metadata.get("kind") == "code_cell"]
    assert len(code) == 1
    assert "print('hi')" in code[0].content
    assert code[0].metadata["language"] == "python"


def test_ipynb_raw_cell_emits_paragraph_with_kind(tmp_path: Path):
    nb = _nb([
        {"cell_type": "raw", "source": "raw content", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "c.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="c" * 64)
    raws = [e for e in doc.elements if e.metadata.get("kind") == "raw_cell"]
    assert len(raws) == 1
    assert raws[0].content == "raw content"


def test_ipynb_mixed_cells(tmp_path: Path):
    nb = _nb([
        {"cell_type": "markdown", "source": "# Section", "metadata": {}},
        {"cell_type": "code", "source": "x = 1", "metadata": {}},
        {"cell_type": "markdown", "source": "More text.", "metadata": {}},
        {"cell_type": "raw", "source": "raw", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "d.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="d" * 64)
    assert doc.metadata["cell_count"] == 4
    # markdown cell 1: 1 heading
    # code cell 2: 1 paragraph (code_cell)
    # markdown cell 3: 1 paragraph
    # raw cell 4: 1 paragraph (raw_cell)
    assert len(doc.elements) == 4


# ---------- source_locator ----------


def test_ipynb_locator_markdown_carries_cell_index_and_line(tmp_path: Path):
    nb = _nb([
        {"cell_type": "markdown", "source": "# H\n\nbody", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "e.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="e" * 64)
    heading = doc.elements[0]
    assert heading.source_locator["cell_index"] == 0
    assert heading.source_locator["cell_type"] == "markdown"
    assert heading.source_locator["line"] == 1
    # section_path 在该 cell 内
    assert heading.source_locator["section_path"] == "H"


def test_ipynb_locator_code_cell_basic(tmp_path: Path):
    nb = _nb([
        {"cell_type": "code", "source": "x = 1", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "f.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="10" * 32)
    code = doc.elements[0]
    assert code.source_locator["cell_index"] == 0
    assert code.source_locator["cell_type"] == "code"
    # code cell 没有 line / section_path
    assert code.source_locator["line"] == 1
    assert "section_path" not in code.source_locator


def test_ipynb_element_ids_consecutive_across_cells(tmp_path: Path):
    """跨 cell 的 element_id 连续编号。"""
    nb = _nb([
        {"cell_type": "markdown", "source": "# A\n\nB\n\nC", "metadata": {}},  # 3 element
        {"cell_type": "markdown", "source": "D\n\nE", "metadata": {}},  # 2 element
    ])
    p = _write_nb(tmp_path, "g.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="11" * 32)
    ids = [e.element_id for e in doc.elements]
    suffixes = [eid.split("::e")[1] for eid in ids]
    assert suffixes == ["0000", "0001", "0002", "0003", "0004"]


def test_ipynb_metadata_records_language_and_counts(tmp_path: Path):
    nb = _nb([
        {"cell_type": "code", "source": "print('a')", "metadata": {}},
        {"cell_type": "code", "source": "print('b')", "metadata": {}},
    ], language="julia")
    p = _write_nb(tmp_path, "h.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="12" * 32)
    assert doc.metadata["cell_count"] == 2
    assert doc.metadata["language"] == "julia"
    assert doc.metadata["nbformat"] == 4


# ---------- 边界 ----------


def test_ipynb_source_as_list_concatenated(tmp_path: Path):
    """source 可以是 list[str]，需正确拼接。"""
    nb = _nb([
        {"cell_type": "code", "source": ["line1\n", "line2\n", "line3"], "metadata": {}},
    ])
    p = _write_nb(tmp_path, "i.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="13" * 32)
    code = [e for e in doc.elements if e.metadata.get("kind") == "code_cell"][0]
    assert "line1" in code.content
    assert "line2" in code.content
    assert "line3" in code.content


def test_ipynb_empty_code_cell_skipped_with_warning(tmp_path: Path):
    nb = _nb([
        {"cell_type": "code", "source": "", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "j.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="14" * 32)
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "ipynb_empty_code_cell" in codes


def test_ipynb_empty_notebook_yields_warning(tmp_path: Path):
    nb = _nb([])
    p = _write_nb(tmp_path, "k.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="15" * 32)
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "ipynb_no_content" in codes


def test_ipynb_unknown_cell_type_warning(tmp_path: Path):
    nb = _nb([
        {"cell_type": "weird", "source": "stuff", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "l.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="16" * 32)
    codes = [w.code for w in doc.warnings]
    assert "ipynb_unknown_cell_type" in codes


# ---------- 错误路径 ----------


def test_ipynb_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(tmp_path / "nope.ipynb", source_hash="x" * 64)
    assert exc.value.code == "file_not_found"


def test_ipynb_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hi")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="y" * 64)
    assert exc.value.code == "unsupported_type"


def test_ipynb_invalid_json_raises(tmp_path: Path):
    p = tmp_path / "bad.ipynb"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="z" * 64)
    assert exc.value.code == "ipynb_invalid_json"


def test_ipynb_unsupported_nbformat_version_raises(tmp_path: Path):
    nb = {
        "cells": [{"cell_type": "code", "source": "x", "metadata": {}}],
        "metadata": {},
        "nbformat": 3,
        "nbformat_minor": 0,
    }
    p = _write_nb(tmp_path, "old.ipynb", nb)
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "ipynb_unsupported_version"


# ---------- Document / schema ----------


def test_ipynb_parser_name_and_version(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.parser_name == "ipynb"
    assert doc.parser_version.startswith("stdlib/")
    assert doc.chunks == []
    assert doc.errors == []


def test_ipynb_full_document_schema_valid(tmp_path: Path):
    from app.schema import validate

    nb = _nb([
        {"cell_type": "markdown", "source": "# Title\n\nIntro paragraph.", "metadata": {}},
        {"cell_type": "code", "source": "x = 1\nprint(x)", "metadata": {}},
        {"cell_type": "markdown", "source": "## Sub\n\nMore.", "metadata": {}},
        {"cell_type": "raw", "source": "raw text", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "full.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="b" * 64)
    validate(doc.to_dict())


# adoption 裁切（2026-08-27，ipynb 机械搬运阶段）：以下两个测试经 pipeline /
# CLI 调用 ipynb，属注册启用阶段依赖（契约 §12 切分表），注册时原样搬回。
# --- CUT test_ipynb_pipeline_end_to_end（process_single parser_name="ipynb"）---
# --- CUT test_cli_parse_ipynb_end_to_end（app.cli parse --parser ipynb）---


# ---------- 边角与缺漏补强（Round 38） ----------


# _detect_ipynb_source_type 直接单测


def test_detect_ipynb_source_type_accepts_ipynb():
    from app.parsers.ipynb_parser import _detect_ipynb_source_type
    assert _detect_ipynb_source_type(Path("notebook.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_accepts_uppercase_extension():
    """扩展名 lower() 后比较，所以 .IPYNB 也接受。"""
    from app.parsers.ipynb_parser import _detect_ipynb_source_type
    assert _detect_ipynb_source_type(Path("notebook.IPYNB")) == "ipynb"
    assert _detect_ipynb_source_type(Path("notebook.Ipynb")) == "ipynb"


def test_detect_ipynb_source_type_rejects_json():
    from app.parsers.ipynb_parser import _detect_ipynb_source_type
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("notebook.json"))
    assert exc.value.code == "unsupported_type"


def test_detect_ipynb_source_type_rejects_no_suffix():
    from app.parsers.ipynb_parser import _detect_ipynb_source_type
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("notebook"))


# _cell_source_to_text 直接单测


def test_cell_source_to_text_string_passthrough():
    from app.parsers.ipynb_parser import _cell_source_to_text
    assert _cell_source_to_text("hello") == "hello"


def test_cell_source_to_text_empty_string():
    from app.parsers.ipynb_parser import _cell_source_to_text
    assert _cell_source_to_text("") == ""


def test_cell_source_to_text_list_of_strings_concatenated():
    from app.parsers.ipynb_parser import _cell_source_to_text
    result = _cell_source_to_text(["line1\n", "line2\n", "line3"])
    assert result == "line1\nline2\nline3"


def test_cell_source_to_text_empty_list_returns_empty():
    from app.parsers.ipynb_parser import _cell_source_to_text
    assert _cell_source_to_text([]) == ""


def test_cell_source_to_text_none_returns_none():
    from app.parsers.ipynb_parser import _cell_source_to_text
    assert _cell_source_to_text(None) is None


def test_cell_source_to_text_int_returns_none():
    """非 str/list 类型 → 空字符串。"""
    from app.parsers.ipynb_parser import _cell_source_to_text
    assert _cell_source_to_text(42) is None
    assert _cell_source_to_text(3.14) is None


def test_cell_source_to_text_list_with_non_string_items():
    """list 内部元素会被 str() 转换。"""
    from app.parsers.ipynb_parser import _cell_source_to_text
    # 纯字符串列表正常拼接
    assert _cell_source_to_text(["a", "b", "c"]) == "abc"


# _extract_kernel_language 直接单测


def test_extract_kernel_language_from_kernelspec_language():
    from app.parsers.ipynb_parser import _extract_kernel_language
    metadata = {"kernelspec": {"language": "python", "name": "python3"}}
    assert _extract_kernel_language(metadata) == "python"


# adoption 契约 §6 注记（2026-08-27）：kernelspec.name 是内核标识，不参与语言判定；
# 链为 kernelspec.language → language_info.name → 空串。
def test_extract_kernel_language_kernelspec_name_not_a_language():
    """kernelspec.name 不参与语言判定：仅含 name → 空串。"""
    from app.parsers.ipynb_parser import _extract_kernel_language
    metadata = {"kernelspec": {"name": "julia3"}}
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_falls_back_to_language_info_name():
    """kernelspec 完全缺失时，回退到 language_info.name。"""
    from app.parsers.ipynb_parser import _extract_kernel_language
    metadata = {"language_info": {"name": "r"}}
    assert _extract_kernel_language(metadata) == "r"


def test_extract_kernel_language_empty_metadata_returns_empty():
    from app.parsers.ipynb_parser import _extract_kernel_language
    assert _extract_kernel_language({}) == ""


def test_extract_kernel_language_none_metadata_returns_empty():
    """None 入参（实际不会出现，但要稳）。"""
    from app.parsers.ipynb_parser import _extract_kernel_language
    # 函数签名是 dict，但 .get 会报错；这里测空 dict 即可
    assert _extract_kernel_language({}) == ""


def test_extract_kernel_language_kernelspec_none_does_not_crash():
    """metadata.kernelspec 显式为 None → 视作空 dict。"""
    from app.parsers.ipynb_parser import _extract_kernel_language
    metadata = {"kernelspec": None}
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_language_info_none_does_not_crash():
    """metadata.language_info 显式为 None → 视作空 dict。"""
    from app.parsers.ipynb_parser import _extract_kernel_language
    metadata = {"kernelspec": {}, "language_info": None}
    assert _extract_kernel_language(metadata) == ""


def test_extract_kernel_language_prioritizes_kernelspec_language_over_name():
    """两者都存在时，language 优先。"""
    from app.parsers.ipynb_parser import _extract_kernel_language
    metadata = {"kernelspec": {"language": "python", "name": "python3"}}
    assert _extract_kernel_language(metadata) == "python"


# IpynbParser metadata / element 边角


def test_ipynb_parser_metadata_has_ipynb_true(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.metadata["ipynb"] is True


def test_ipynb_parser_metadata_records_nbformat_minor(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.metadata["nbformat"] == 4
    assert doc.metadata["nbformat_minor"] == 5


def test_ipynb_parser_element_confidence_is_095(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "markdown", "source": "# H\n\ntext", "metadata": {}},
        {"cell_type": "code", "source": "x=1", "metadata": {}},
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.confidence == 0.95


def test_ipynb_parser_element_id_format(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    expected_prefix = "doc-" + "a" * 16
    assert doc.elements[0].element_id == f"{expected_prefix}::e0000"


def test_ipynb_parser_element_parent_id_is_none(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.parent_id is None


def test_ipynb_parser_element_resource_path_is_none_for_code(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.resource_path is None


def test_ipynb_parser_source_path_preserved(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.source_path == str(p)


def test_ipynb_parser_source_hash_passed_through(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    custom_hash = "b" * 64
    doc = IpynbParser().parse(p, source_hash=custom_hash)
    assert doc.source_hash == custom_hash


def test_ipynb_parser_document_id_derived_from_hash(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.document_id == "doc-" + "a" * 16


def test_ipynb_parser_chunks_empty_by_default(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.chunks == []


def test_ipynb_parser_relations_empty_by_default(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.relations == []


def test_ipynb_parser_errors_empty_by_default(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.errors == []


def test_ipynb_parser_name_and_version_constants(tmp_path: Path):
    p = _write_nb(tmp_path, "a.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.parser_name == "ipynb"
    assert doc.parser_version == "stdlib/0.1.0"


# 错误路径补强


def test_ipynb_parser_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(tmp_path / "nope.ipynb", source_hash="a" * 64)
    assert exc.value.code == "file_not_found"


def test_ipynb_parser_top_level_not_dict_raises(tmp_path: Path):
    """顶层 JSON 是 list 而非 dict。"""
    p = tmp_path / "bad.ipynb"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_ipynb_parser_cells_not_list_raises(tmp_path: Path):
    """cells 字段不是数组。"""
    p = tmp_path / "bad.ipynb"
    p.write_text(json.dumps({"cells": "not a list", "nbformat": 4}), encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_ipynb_parser_cell_not_dict_emits_warning(tmp_path: Path):
    """cell 不是 dict → 跳过并发出 ipynb_bad_cell。"""
    nb = {
        "cells": ["not a dict", 42, {"cell_type": "code", "source": "x=1", "metadata": {}}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = _write_nb(tmp_path, "weird.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "ipynb_bad_cell" in codes
    # 第三个 cell 仍被处理
    assert len(doc.elements) == 1


def test_ipynb_parser_empty_raw_cell_skipped_silently(tmp_path: Path):
    """空 raw cell 不发出 warning（与空 code cell 不同）。"""
    nb = _nb([
        {"cell_type": "raw", "source": "   ", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "raw.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.elements == []
    # 没有 ipynb_empty_code_cell（因为是 raw）
    codes = [w.code for w in doc.warnings]
    assert "ipynb_empty_code_cell" not in codes
    # 但会有 ipynb_no_content（最终没 element）
    assert "ipynb_no_content" in codes


# adoption 契约 §5/§8 注记（2026-08-27）：code/raw 正文保留原始缩进换行（strip 仅判空）。
def test_ipynb_parser_preserve_whitespace_for_code_cell(tmp_path: Path):
    """code cell 的正文保留原始首尾空白（strip 仅用于判空）。"""
    nb = _nb([
        {"cell_type": "code", "source": "\n\n   print('hi')   \n\n", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "ws.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    code = [e for e in doc.elements if e.metadata.get("kind") == "code_cell"][0]
    assert code.content == "\n\n   print('hi')   \n\n"


# adoption 契约 §5/§8 注记（2026-08-27）：source 非法输入归一为 None（跳过 cell +
# ipynb_bad_cell）；code/raw 正文保留原始缩进换行（strip 仅判空）；locator 补 line=1。
# 以下原快照期望已按定稿契约改写。
def test_ipynb_parser_preserve_whitespace_for_raw_cell(tmp_path: Path):
    """raw cell 的正文保留原始首尾空白（strip 仅用于判空）。"""
    nb = _nb([
        {"cell_type": "raw", "source": "  raw text  ", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "raw2.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    raw = [e for e in doc.elements if e.metadata.get("kind") == "raw_cell"][0]
    assert raw.content == "  raw text  "


def test_ipynb_parser_default_cell_type_when_missing(tmp_path: Path):
    """cell 缺失 cell_type 字段 → 视作 unknown → 发 warning。"""
    nb = _nb([
        {"source": "text", "metadata": {}},  # 没有 cell_type
    ])
    p = _write_nb(tmp_path, "noct.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "ipynb_unknown_cell_type" in codes


def test_ipynb_parser_metadata_can_be_empty_dict(tmp_path: Path):
    """notebook 没有 metadata 字段也能解析（language 推断为空）。"""
    nb = {
        "cells": [{"cell_type": "code", "source": "x=1", "metadata": {}}],
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = _write_nb(tmp_path, "nohelp.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    # language 是空字符串
    assert doc.metadata["language"] == ""
    # code cell 的 language metadata 也是空
    code = doc.elements[0]
    assert code.metadata["language"] == ""


def test_ipynb_parser_nbformat_missing_rejected_as_bad_structure(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：nbformat 字段缺失 → ipynb_bad_structure。

    原快照语义为“缺失按 4+ 处理”，契约修订后版本字段必填。
    """
    nb = {
        "cells": [{"cell_type": "code", "source": "x=1", "metadata": {}}],
        "metadata": {},
        "nbformat_minor": 5,
    }
    p = _write_nb(tmp_path, "nofmt.ipynb", nb)
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "ipynb_bad_structure"
    assert ei.value.details["field"] == "nbformat"


def test_ipynb_parser_markdown_cell_with_only_whitespace_warns_no_content(tmp_path: Path):
    """markdown cell 内容为空白 → md parser 自己 warning；最终 ipynb_no_content。"""
    nb = _nb([
        {"cell_type": "markdown", "source": "   \n\n  ", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "wsmd.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "ipynb_no_content" in codes


def test_ipynb_parser_outputs_field_ignored(tmp_path: Path):
    """code cell 的 outputs 字段被丢弃，不出现在 element 中。"""
    nb = _nb([
        {
            "cell_type": "code",
            "source": "print('hi')",
            "metadata": {},
            "outputs": [
                {"output_type": "stream", "name": "stdout", "text": "hi\n"},
            ],
            "execution_count": 1,
        },
    ])
    p = _write_nb(tmp_path, "out.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    code = doc.elements[0]
    assert "hi" in code.content  # 来自 source
    # outputs 里的 "hi\n" 不会作为单独 element
    assert len(doc.elements) == 1


def test_ipynb_parser_invalid_utf8_propagates_unicode_error(tmp_path: Path):
    """非法 UTF-8 → json.load 走 fp.read() 时抛 UnicodeDecodeError（ValueError 子类）。
    当前 parser 没有兜底 UnicodeDecodeError，会向上抛出（行为契约）。"""
    p = tmp_path / "bad.ipynb"
    p.write_bytes(b"\xff\xfe{\"cells\": []}")
    with pytest.raises(UnicodeDecodeError):
        IpynbParser().parse(p, source_hash="a" * 64)
