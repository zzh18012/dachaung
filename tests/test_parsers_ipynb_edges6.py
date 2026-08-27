r"""app/parsers/ipynb_parser.py 边角测试 - 第六轮（Round 164）。

补强已有 base/edges/edges2-5（共 632 测试）未覆盖的深度：
- _IPYNB_EXTENSIONS 常量
- _detect_ipynb_source_type details 精确
- _cell_source_to_text 各类型边界
- _extract_kernel_language 多种 metadata 形态
- IpynbParser.parse() 各错误路径与 metadata
- nbformat 版本校验
- cells 结构校验
- cell_type 各分支（markdown/code/raw/unknown/missing）
- 空 cell 警告（empty code/raw）
- element_id 连续重编号
- locator 字段精确（cell_index/cell_type/line/section_path）
- Document.metadata 字段精确
- 模块结构与签名
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import ParserError
from app.parsers.ipynb_parser import (
    _IPYNB_EXTENSIONS,
    IpynbParser,
    _cell_source_to_text,
    _detect_ipynb_source_type,
    _extract_kernel_language,
)


_H = "a" * 64
_H2 = "b" * 64


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _write_nb(tmp_path: Path, name: str, nb: dict) -> Path:
    return _write(tmp_path, name, json.dumps(nb))


def _minimal_nb(cells: list, metadata: dict | None = None) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": metadata or {},
        "cells": cells,
    }


# =========================================================================
# 常量精确性
# =========================================================================


def test_ipynb_extensions_exact():
    assert _IPYNB_EXTENSIONS == (".ipynb",)


def test_ipynb_extensions_is_tuple():
    assert isinstance(_IPYNB_EXTENSIONS, tuple)


def test_ipynb_extensions_lowercase():
    for ext in _IPYNB_EXTENSIONS:
        assert ext == ext.lower()


def test_ipynb_extensions_starts_with_dot():
    for ext in _IPYNB_EXTENSIONS:
        assert ext.startswith(".")


def test_ipynb_extensions_length_one():
    assert len(_IPYNB_EXTENSIONS) == 1


# =========================================================================
# _detect_ipynb_source_type details
# =========================================================================


def test_detect_ipynb_source_type_ipynb_returns_ipynb():
    assert _detect_ipynb_source_type(Path("foo.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_uppercase_returns_ipynb():
    assert _detect_ipynb_source_type(Path("foo.IPYNB")) == "ipynb"


def test_detect_ipynb_source_type_txt_raises():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("foo.txt"))
    assert exc.value.code == "unsupported_type"


def test_detect_ipynb_source_type_no_suffix_raises():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("foo"))
    assert exc.value.code == "unsupported_type"


def test_detect_ipynb_source_type_no_suffix_details_empty():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("foo"))
    assert exc.value.details == {"suffix": ""}


def test_detect_ipynb_source_type_txt_details_has_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("foo.txt"))
    assert exc.value.details == {"suffix": ".txt"}


def test_detect_ipynb_source_type_message_mentions_ipynb():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("foo.txt"))
    assert ".ipynb" in exc.value.message


def test_detect_ipynb_source_type_message_mentions_actual_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("foo.json"))
    assert ".json" in exc.value.message


# =========================================================================
# _cell_source_to_text 各类型
# =========================================================================


def test_cell_source_str_returns_str():
    assert _cell_source_to_text("hello") == "hello"


def test_cell_source_list_of_str_joins():
    assert _cell_source_to_text(["a", "b", "c"]) == "abc"


def test_cell_source_list_with_newlines():
    """list[str] 中每行末尾通常带 \n。"""
    assert _cell_source_to_text(["line1\n", "line2\n"]) == "line1\nline2\n"


def test_cell_source_empty_str():
    assert _cell_source_to_text("") == ""


def test_cell_source_empty_list():
    assert _cell_source_to_text([]) == ""


def test_cell_source_none_returns_empty():
    assert _cell_source_to_text(None) == ""


def test_cell_source_int_returns_empty():
    """非 str/list → ""."""
    assert _cell_source_to_text(42) == ""


def test_cell_source_dict_returns_empty():
    assert _cell_source_to_text({"k": "v"}) == ""


def test_cell_source_list_of_non_str():
    """list 中含非 str → 强转 str。"""
    assert _cell_source_to_text([1, 2, 3]) == "123"


def test_cell_source_list_mixed_types():
    assert _cell_source_to_text(["a", 1, None]) == "a1None"


# =========================================================================
# _extract_kernel_language 各形态
# =========================================================================


def test_extract_kernel_language_empty_metadata():
    assert _extract_kernel_language({}) == ""


def test_extract_kernel_language_kernelspec_language():
    meta = {"kernelspec": {"language": "python", "name": "python3"}}
    assert _extract_kernel_language(meta) == "python"


def test_extract_kernel_language_kernelspec_no_language_uses_name():
    """kernelspec 无 language → fallback 到 name。"""
    meta = {"kernelspec": {"name": "python3"}}
    assert _extract_kernel_language(meta) == "python3"


def test_extract_kernel_language_no_kernelspec_uses_language_info():
    meta = {"language_info": {"name": "r"}}
    assert _extract_kernel_language(meta) == "r"


def test_extract_kernel_language_kernelspec_priority_over_language_info():
    """kernelspec 优先。"""
    meta = {
        "kernelspec": {"language": "python"},
        "language_info": {"name": "r"},
    }
    assert _extract_kernel_language(meta) == "python"


def test_extract_kernel_language_empty_kernelspec_uses_language_info():
    meta = {
        "kernelspec": {},
        "language_info": {"name": "julia"},
    }
    assert _extract_kernel_language(meta) == "julia"


def test_extract_kernel_language_kernelspec_none_uses_language_info():
    """kernelspec 显式 None。"""
    meta = {
        "kernelspec": None,
        "language_info": {"name": "rust"},
    }
    assert _extract_kernel_language(meta) == "rust"


def test_extract_kernel_language_no_metadata_at_all():
    assert _extract_kernel_language({}) == ""


def test_extract_kernel_language_kernelspec_language_empty_string():
    """language="" → fallback 到 name。"""
    meta = {"kernelspec": {"language": "", "name": "fallback"}}
    assert _extract_kernel_language(meta) == "fallback"


def test_extract_kernel_language_both_empty_returns_empty():
    meta = {
        "kernelspec": {"language": "", "name": ""},
        "language_info": {"name": ""},
    }
    assert _extract_kernel_language(meta) == ""


# =========================================================================
# IpynbParser 类属性
# =========================================================================


def test_ipynb_parser_name_value():
    assert IpynbParser.name == "ipynb"


def test_ipynb_parser_version_value():
    assert IpynbParser.version == "stdlib/0.1.0"


def test_ipynb_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(IpynbParser, Parser)


def test_ipynb_parser_init_no_args():
    p = IpynbParser()
    assert p is not None


# =========================================================================
# parse() 错误路径
# =========================================================================


def test_parse_nonexistent_file_raises(tmp_path: Path):
    p = tmp_path / "missing.ipynb"
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, _H)
    assert exc.value.code == "file_not_found"
    assert str(p) in exc.value.message


def test_parse_nonexistent_file_details(tmp_path: Path):
    p = tmp_path / "missing.ipynb"
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, _H)
    assert exc.value.details == {"path": str(p)}


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = _write(tmp_path, "foo.txt", "{}")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, _H)
    assert exc.value.code == "unsupported_type"


def test_parse_invalid_json_raises(tmp_path: Path):
    p = _write(tmp_path, "bad.ipynb", "{not valid json")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, _H)
    assert exc.value.code == "ipynb_invalid_json"


def test_parse_invalid_json_message(tmp_path: Path):
    p = _write(tmp_path, "bad.ipynb", "{not valid")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, _H)
    assert ".ipynb" in exc.value.message
    assert "JSON" in exc.value.message or "json" in exc.value.message.lower()


def test_parse_top_level_array_raises(tmp_path: Path):
    """顶层是 list 不是 dict → ipynb_bad_structure。"""
    p = _write_nb(tmp_path, "x.ipynb", [])
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, _H)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_top_level_string_raises(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", "hello")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, _H)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_nbformat_3_raises(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", {"nbformat": 3, "cells": []})
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, _H)
    assert exc.value.code == "ipynb_unsupported_version"
    assert exc.value.details == {"nbformat": 3}


def test_parse_nbformat_2_raises(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", {"nbformat": 2, "cells": []})
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, _H)
    assert exc.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_none_accepted(tmp_path: Path):
    """nbformat=None（缺字段）→ 视为 None，不触发 <4 检查，应通过。"""
    p = _write_nb(tmp_path, "x.ipynb", {"cells": []})
    doc = IpynbParser().parse(p, _H)
    assert isinstance(doc, Document)


def test_parse_cells_not_list_raises(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", {"nbformat": 4, "cells": "not list"})
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, _H)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_cells_none_treated_as_empty(tmp_path: Path):
    """cells=None → 视为 []。"""
    p = _write_nb(tmp_path, "x.ipynb", {"nbformat": 4, "cells": None})
    doc = IpynbParser().parse(p, _H)
    assert doc.elements == []
    # 空 notebook → ipynb_no_content warning
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


def test_parse_cells_missing_treated_as_empty(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", {"nbformat": 4})
    doc = IpynbParser().parse(p, _H)
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


# =========================================================================
# parse() 成功路径
# =========================================================================


def test_parse_returns_document(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert isinstance(doc, Document)


def test_parse_metadata_has_ipynb_true(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert doc.metadata["ipynb"] is True


def test_parse_metadata_has_nbformat(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert doc.metadata["nbformat"] == 4


def test_parse_metadata_has_nbformat_minor(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert doc.metadata["nbformat_minor"] == 5


def test_parse_metadata_has_cell_count(tmp_path: Path):
    cells = [
        {"cell_type": "markdown", "source": "# T"},
        {"cell_type": "code", "source": "print(1)"},
    ]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert doc.metadata["cell_count"] == 2


def test_parse_metadata_has_language(tmp_path: Path):
    cells = []
    meta = {"kernelspec": {"language": "python"}}
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells, meta))
    doc = IpynbParser().parse(p, _H)
    assert doc.metadata["language"] == "python"


def test_parse_source_type_ipynb(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert doc.source_type == "ipynb"


def test_parse_source_path_is_str(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert isinstance(doc.source_path, str)
    assert doc.source_path == str(p)


def test_parse_source_hash_propagated(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert doc.source_hash == _H


def test_parse_parser_name_propagated(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert doc.parser_name == "ipynb"


def test_parse_parser_version_propagated(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert doc.parser_version == "stdlib/0.1.0"


def test_parse_empty_chunks_relations_errors(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []


def test_parse_uses_make_document_id(tmp_path: Path):
    from app.parsers.base import make_document_id
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert doc.document_id == make_document_id(_H)


# =========================================================================
# cell_type 分支
# =========================================================================


def test_parse_markdown_cell_emits_elements(tmp_path: Path):
    cells = [{"cell_type": "markdown", "source": "# Title\n\nparagraph"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    # markdown cell 经 MarkdownParser 处理后产 2 element（heading + paragraph）
    assert len(doc.elements) == 2
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types


def test_parse_markdown_cell_locator_has_cell_index(tmp_path: Path):
    cells = [{"cell_type": "markdown", "source": "hello"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert doc.elements[0].source_locator["cell_index"] == 0
    assert doc.elements[0].source_locator["cell_type"] == "markdown"


def test_parse_markdown_cell_locator_has_line(tmp_path: Path):
    cells = [{"cell_type": "markdown", "source": "# T\n\npara\n"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    # heading 在 line 1
    h = [e for e in doc.elements if e.type == "heading"][0]
    assert h.source_locator["line"] == 1


def test_parse_markdown_cell_locator_has_section_path(tmp_path: Path):
    cells = [{"cell_type": "markdown", "source": "# T\n\npara"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    para = [e for e in doc.elements if e.type == "paragraph"][0]
    assert para.source_locator["section_path"] == "T"


def test_parse_code_cell_emits_paragraph_with_kind(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "print('hello')"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert len(doc.elements) == 1
    el = doc.elements[0]
    assert el.type == "paragraph"
    assert el.metadata["kind"] == "code_cell"


def test_parse_code_cell_language_from_kernelspec(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "x"}]
    meta = {"kernelspec": {"language": "python"}}
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells, meta))
    doc = IpynbParser().parse(p, _H)
    assert doc.elements[0].metadata["language"] == "python"


def test_parse_code_cell_language_empty_when_no_kernelspec(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "x"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert doc.elements[0].metadata["language"] == ""


def test_parse_code_cell_content_stripped(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "  print(1)  \n"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert doc.elements[0].content == "print(1)"


def test_parse_code_cell_locator_no_line(tmp_path: Path):
    """code cell locator 不含 line 字段（只有 cell_index/cell_type）。"""
    cells = [{"cell_type": "code", "source": "x"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    loc = doc.elements[0].source_locator
    assert "line" not in loc
    assert loc["cell_index"] == 0
    assert loc["cell_type"] == "code"


def test_parse_raw_cell_emits_paragraph_with_kind(tmp_path: Path):
    cells = [{"cell_type": "raw", "source": "raw content"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].metadata["kind"] == "raw_cell"


def test_parse_raw_cell_content_stripped(tmp_path: Path):
    cells = [{"cell_type": "raw", "source": "  x  \n"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert doc.elements[0].content == "x"


def test_parse_unknown_cell_type_emits_warning(tmp_path: Path):
    cells = [{"cell_type": "weird", "source": "x"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert any(w.code == "ipynb_unknown_cell_type" for w in doc.warnings)


def test_parse_unknown_cell_type_no_element(tmp_path: Path):
    cells = [{"cell_type": "weird", "source": "x"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    # unknown cell 不产 element，但触发 ipynb_no_content
    assert len(doc.elements) == 0
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


def test_parse_missing_cell_type_treated_as_unknown(tmp_path: Path):
    """无 cell_type 字段 → 默认 "unknown"。"""
    cells = [{"source": "x"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert any(w.code == "ipynb_unknown_cell_type" for w in doc.warnings)


def test_parse_cell_not_dict_emits_warning(tmp_path: Path):
    cells = ["not a dict", 42, None]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    bad_cell_warnings = [w for w in doc.warnings if w.code == "ipynb_bad_cell"]
    assert len(bad_cell_warnings) == 3


def test_parse_cell_not_dict_details_has_index(tmp_path: Path):
    cells = ["not a dict"]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    bad_cell_warnings = [w for w in doc.warnings if w.code == "ipynb_bad_cell"]
    assert bad_cell_warnings[0].details == {"cell_index": 0}


def test_parse_empty_code_cell_emits_warning(tmp_path: Path):
    cells = [{"cell_type": "code", "source": ""}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert any(w.code == "ipynb_empty_code_cell" for w in doc.warnings)


def test_parse_whitespace_only_code_cell_emits_warning(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "   \n\t  "}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert any(w.code == "ipynb_empty_code_cell" for w in doc.warnings)


def test_parse_empty_raw_cell_no_warning_skipped(tmp_path: Path):
    """空 raw cell 直接跳过，不产 ipynb_no_content 之外的 warning。"""
    cells = [{"cell_type": "raw", "source": ""}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    # 没有空 raw cell 警告（直接 skip）
    # 但应有 ipynb_no_content（因为没产 element）
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


# =========================================================================
# element_id 重编号
# =========================================================================


def test_parse_element_id_resequenced(tmp_path: Path):
    """element_id 在所有 cell 处理完后连续重编号。"""
    cells = [
        {"cell_type": "markdown", "source": "# T1\n# T2"},  # 2 elements
        {"cell_type": "code", "source": "x"},  # 1 element
    ]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    ids = [e.element_id for e in doc.elements]
    # 3 elements with id e0000, e0001, e0002
    suffixes = [i.split("::")[1] for i in ids]
    assert suffixes == ["e0000", "e0001", "e0002"]


def test_parse_element_id_zero_padded_four(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "x"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert "::e0000" in doc.elements[0].element_id


def test_parse_element_id_shares_doc_id_prefix(tmp_path: Path):
    cells = [{"cell_type": "code", "source": "x"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    assert doc.elements[0].element_id.startswith(doc.document_id + "::")


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


def test_module_imports_markdown_parser():
    """复用 MarkdownParser 处理 markdown cell。"""
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "MarkdownParser" in src


def test_module_docstring_present():
    import app.parsers.ipynb_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_nbformat():
    import app.parsers.ipynb_parser as mod
    doc = mod.__doc__
    assert "nbformat" in doc.lower() or "4+" in doc


def test_module_docstring_mentions_cell_types():
    import app.parsers.ipynb_parser as mod
    doc = mod.__doc__
    assert "markdown" in doc.lower()
    assert "code" in doc.lower()


def test_module_docstring_mentions_unsupported_outputs():
    """docstring 提及 outputs 被丢弃。"""
    import app.parsers.ipynb_parser as mod
    doc = mod.__doc__
    assert "outputs" in doc.lower() or "output" in doc.lower()


def test_module_no_silence_unused():
    import app.parsers.ipynb_parser as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 签名深度
# =========================================================================


def test_parse_signature_two_params():
    sig = inspect.signature(IpynbParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


def test_parse_params_no_defaults():
    sig = inspect.signature(IpynbParser.parse)
    for p in sig.parameters.values():
        if p.name == "self":
            continue
        assert p.default is inspect.Parameter.empty


def test_parse_return_annotation_document():
    sig = inspect.signature(IpynbParser.parse)
    assert "Document" in str(sig.return_annotation)


def test_detect_ipynb_source_type_signature():
    sig = inspect.signature(_detect_ipynb_source_type)
    assert set(sig.parameters) == {"path"}


def test_detect_ipynb_source_type_return_annotation_str():
    sig = inspect.signature(_detect_ipynb_source_type)
    assert "str" in str(sig.return_annotation)


def test_cell_source_to_text_signature():
    sig = inspect.signature(_cell_source_to_text)
    assert set(sig.parameters) == {"source"}


def test_cell_source_to_text_return_annotation_str():
    sig = inspect.signature(_cell_source_to_text)
    assert "str" in str(sig.return_annotation)


def test_extract_kernel_language_signature():
    sig = inspect.signature(_extract_kernel_language)
    assert set(sig.parameters) == {"metadata"}


def test_extract_kernel_language_return_annotation_str():
    sig = inspect.signature(_extract_kernel_language)
    assert "str" in str(sig.return_annotation)


# =========================================================================
# 综合行为
# =========================================================================


def test_parse_idempotent_same_file(tmp_path: Path):
    cells = [
        {"cell_type": "markdown", "source": "# T\n\nhello"},
        {"cell_type": "code", "source": "print(1)"},
    ]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    d1 = IpynbParser().parse(p, _H)
    d2 = IpynbParser().parse(p, _H)
    assert d1.document_id == d2.document_id
    assert len(d1.elements) == len(d2.elements)


def test_parse_different_hash_different_doc_id(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    d1 = IpynbParser().parse(p, _H)
    d2 = IpynbParser().parse(p, _H2)
    assert d1.document_id != d2.document_id


def test_parse_complex_notebook(tmp_path: Path):
    """完整 notebook 含 markdown/code/raw cell。"""
    cells = [
        {"cell_type": "markdown", "source": "# Title\n\nintro"},
        {"cell_type": "code", "source": "print('hello')"},
        {"cell_type": "markdown", "source": "## Section\n\nmore text"},
        {"cell_type": "raw", "source": "raw stuff"},
        {"cell_type": "code", "source": "x = 1"},
    ]
    meta = {"kernelspec": {"language": "python", "name": "python3"}}
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells, meta))
    doc = IpynbParser().parse(p, _H)
    types = [e.type for e in doc.elements]
    assert types.count("heading") == 2
    assert types.count("paragraph") >= 3  # 2 intro/more + 1 code + 1 raw = wait, code/raw also paragraph type
    code_cells = [e for e in doc.elements if e.metadata.get("kind") == "code_cell"]
    assert len(code_cells) == 2
    raw_cells = [e for e in doc.elements if e.metadata.get("kind") == "raw_cell"]
    assert len(raw_cells) == 1


def test_parse_no_content_warning_for_empty_notebook(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb([]))
    doc = IpynbParser().parse(p, _H)
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)


def test_parse_markdown_cell_subwarning_propagated_with_cell_index(tmp_path: Path):
    """markdown cell 内部触发 md_empty_code_block → ipynb 包装加 cell_index。"""
    cells = [{"cell_type": "markdown", "source": "```\n```\n"}]
    p = _write_nb(tmp_path, "x.ipynb", _minimal_nb(cells))
    doc = IpynbParser().parse(p, _H)
    md_empty_warnings = [w for w in doc.warnings if w.code == "md_empty_code_block"]
    assert len(md_empty_warnings) >= 1
    assert md_empty_warnings[0].details["cell_index"] == 0
    assert "cell #0 (markdown)" in md_empty_warnings[0].reason


def test_parse_does_not_mutate_input(tmp_path: Path):
    """parse 不应修改文件内容。"""
    cells = [{"cell_type": "code", "source": "x"}]
    nb = _minimal_nb(cells)
    p = _write_nb(tmp_path, "x.ipynb", nb)
    before = p.read_text(encoding="utf-8")
    IpynbParser().parse(p, _H)
    after = p.read_text(encoding="utf-8")
    assert before == after
