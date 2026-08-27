r"""app/parsers/ipynb_parser.py 边角测试 - 第五轮（Round 138）。

补强已有 base/edges/edges2/edges3/edges4（共 544 测试）未覆盖的深度：
- _cell_source_to_text 边界（int list, None, mixed）
- _extract_kernel_language 边界（kernelspec.name, language_info.name fallback）
- _detect_ipynb_source_type 大小写、错误 details
- IpynbParser 类属性与签名
- 综合行为：多 cell 类型混合、空 notebook、nbformat 校验
- 模块结构与 docstring 深度
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
    IpynbParser,
    _cell_source_to_text,
    _detect_ipynb_source_type,
    _extract_kernel_language,
    _IPYNB_EXTENSIONS,
)


# =========================================================================
# _IPYNB_EXTENSIONS 常量
# =========================================================================


def test_ipynb_extensions_count_one():
    assert len(_IPYNB_EXTENSIONS) == 1


def test_ipynb_extensions_contains_ipynb():
    assert ".ipynb" in _IPYNB_EXTENSIONS


def test_ipynb_extensions_is_tuple():
    assert isinstance(_IPYNB_EXTENSIONS, tuple)


# =========================================================================
# _detect_ipynb_source_type 深度
# =========================================================================


def test_detect_ipynb_source_type_lowercase():
    assert _detect_ipynb_source_type(Path("test.ipynb")) == "ipynb"


def test_detect_ipynb_source_type_uppercase():
    assert _detect_ipynb_source_type(Path("test.IPYNB")) == "ipynb"


def test_detect_ipynb_source_type_mixed_case():
    assert _detect_ipynb_source_type(Path("test.IpYnB")) == "ipynb"


def test_detect_ipynb_source_type_rejects_pdf():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("test.pdf"))
    assert exc.value.code == "unsupported_type"


def test_detect_ipynb_source_type_rejects_html():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("test.html"))


def test_detect_ipynb_source_type_rejects_md():
    with pytest.raises(ParserError):
        _detect_ipynb_source_type(Path("test.md"))


def test_detect_ipynb_source_type_rejects_no_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("notebook"))
    assert "(无)" in exc.value.message or "suffix" in str(exc.value.details)


def test_detect_ipynb_source_type_error_details_suffix_value():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("test.txt"))
    assert exc.value.details == {"suffix": ".txt"}


def test_detect_ipynb_source_type_error_details_empty_when_no_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_ipynb_source_type(Path("notebook"))
    assert exc.value.details == {"suffix": ""}


# =========================================================================
# _cell_source_to_text 深度
# =========================================================================


def test_cell_source_to_text_str_passthrough():
    assert _cell_source_to_text("hello") == "hello"


def test_cell_source_to_text_empty_str():
    assert _cell_source_to_text("") == ""


def test_cell_source_to_text_list_of_str():
    assert _cell_source_to_text(["a", "b", "c"]) == "abc"


def test_cell_source_to_text_list_of_str_with_newlines():
    """nbformat 标准：list 元素含 \n。"""
    assert _cell_source_to_text(["line1\n", "line2\n"]) == "line1\nline2\n"


def test_cell_source_to_text_list_with_int():
    """list 含非 str 元素 → str() 转换。"""
    assert _cell_source_to_text(["a", 1, "b"]) == "a1b"


def test_cell_source_to_text_empty_list():
    assert _cell_source_to_text([]) == ""


def test_cell_source_to_text_none_returns_empty():
    assert _cell_source_to_text(None) == ""


def test_cell_source_to_text_int_returns_empty():
    """非 str/list → 空字符串。"""
    assert _cell_source_to_text(42) == ""


def test_cell_source_to_text_dict_returns_empty():
    assert _cell_source_to_text({"k": "v"}) == ""


def test_cell_source_to_text_list_of_dicts():
    """list 含 dict → 每个 dict str() 化。"""
    result = _cell_source_to_text([{"a": 1}])
    assert "a" in result and "1" in result


def test_cell_source_to_text_nested_list():
    """list 含 list → 整个嵌套 str() 化。"""
    result = _cell_source_to_text([["nested"]])
    assert "nested" in result


# =========================================================================
# _extract_kernel_language 深度
# =========================================================================


def test_extract_kernel_language_kernelspec_language_priority():
    """kernelspec.language 优先于 kernelspec.name。"""
    meta = {"kernelspec": {"language": "python", "name": "ir"}}
    assert _extract_kernel_language(meta) == "python"


def test_extract_kernel_language_kernelspec_name_fallback():
    """无 language → 用 name。"""
    meta = {"kernelspec": {"name": "ir"}}
    assert _extract_kernel_language(meta) == "ir"


def test_extract_kernel_language_language_info_fallback():
    """无 kernelspec → 用 language_info.name。"""
    meta = {"language_info": {"name": "julia"}}
    assert _extract_kernel_language(meta) == "julia"


def test_extract_kernel_language_empty_metadata():
    assert _extract_kernel_language({}) == ""


def test_extract_kernel_language_none_metadata_raises():
    """None metadata → AttributeError（实际行为，函数不防御 None）。"""
    with pytest.raises(AttributeError):
        _extract_kernel_language(None)  # type: ignore[arg-type]


def test_extract_kernel_language_kernelspec_empty():
    assert _extract_kernel_language({"kernelspec": {}}) == ""


def test_extract_kernel_language_kernelspec_language_empty_string():
    """language='' → 视为 falsy，回落到 name。"""
    meta = {"kernelspec": {"language": "", "name": "python3"}}
    assert _extract_kernel_language(meta) == "python3"


def test_extract_kernel_language_kernelspec_name_empty_string():
    """language='' + name='' → 回落到 language_info。"""
    meta = {
        "kernelspec": {"language": "", "name": ""},
        "language_info": {"name": "python"},
    }
    assert _extract_kernel_language(meta) == "python"


# =========================================================================
# IpynbParser 类属性
# =========================================================================


def test_ipynb_parser_name_value():
    assert IpynbParser.name == "ipynb"


def test_ipynb_parser_version_value():
    assert IpynbParser.version == "stdlib/0.1.0"


def test_ipynb_parser_name_is_str():
    assert isinstance(IpynbParser.name, str)


def test_ipynb_parser_version_is_str():
    assert isinstance(IpynbParser.version, str)


def test_ipynb_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(IpynbParser, Parser)


# =========================================================================
# 解析全流程：基础场景
# =========================================================================


def _make_notebook(cells: list[dict], metadata: dict | None = None) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": metadata or {},
        "cells": cells,
    }


def test_parse_simple_markdown_cell(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "markdown", "source": ["# Title\n", "body"]}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    # markdown cell 应产生 heading + paragraph
    types = [e.type for e in doc.elements]
    assert "heading" in types


def test_parse_code_cell(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "code", "source": "print('hi')"}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    para = doc.elements[0]
    assert para.type == "paragraph"
    assert para.metadata.get("kind") == "code_cell"


def test_parse_code_cell_inherits_language(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook(
        [{"cell_type": "code", "source": "x = 1"}],
        metadata={"kernelspec": {"language": "r", "name": "ir"}},
    )
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].metadata.get("language") == "r"


def test_parse_raw_cell(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "raw", "source": "raw text"}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    para = doc.elements[0]
    assert para.type == "paragraph"
    assert para.metadata.get("kind") == "raw_cell"


def test_parse_empty_code_cell_emits_warning(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "code", "source": "   "}  # 仅空白
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert any(w.code == "ipynb_empty_code_cell" for w in doc.warnings)


def test_parse_empty_raw_cell_skipped_no_warning(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "raw", "source": ""}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    # raw 空被静默跳过
    assert not any("raw" in w.code for w in doc.warnings)


def test_parse_unknown_cell_type_emits_warning(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "weird", "source": "data"}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert any(w.code == "ipynb_unknown_cell_type" for w in doc.warnings)


def test_parse_non_dict_cell_emits_warning(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook(["not a dict"])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert any(w.code == "ipynb_bad_cell" for w in doc.warnings)


def test_parse_empty_notebook_emits_no_content_warning(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert any(w.code == "ipynb_no_content" for w in doc.warnings)
    assert doc.elements == []


# =========================================================================
# nbformat 校验
# =========================================================================


def test_parse_nbformat_3_rejected(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = {"nbformat": 3, "cells": []}
    p.write_text(json.dumps(nb), encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "ipynb_unsupported_version"


def test_parse_nbformat_none_rejected(tmp_path: Path):
    """adoption 契约 §2（2026-08-27）：nbformat 缺失 → ipynb_bad_structure。"""
    p = tmp_path / "t.ipynb"
    nb = {"cells": []}
    p.write_text(json.dumps(nb), encoding="utf-8")
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_parse_nbformat_4_accepted(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = {"nbformat": 4, "nbformat_minor": 0, "cells": []}
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.metadata.get("nbformat") == 4


def test_parse_nbformat_5_unsupported(tmp_path: Path):
    """adoption 契约 §1（2026-08-27）：nbformat=5 → ipynb_unsupported_version。"""
    p = tmp_path / "t.ipynb"
    nb = {"nbformat": 5, "nbformat_minor": 0, "cells": []}
    p.write_text(json.dumps(nb), encoding="utf-8")
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert ei.value.code == "ipynb_unsupported_version"


def test_parse_top_level_not_dict_raises(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    p.write_text("[1, 2, 3]", encoding="utf-8")  # JSON list
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_cells_not_list_raises(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = {"nbformat": 4, "cells": "not a list"}
    p.write_text(json.dumps(nb), encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "ipynb_bad_structure"


def test_parse_invalid_json_raises(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "ipynb_invalid_json"


# =========================================================================
# locator 深度
# =========================================================================


def test_markdown_cell_locator_has_cell_index_and_type(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "markdown", "source": "# Title"}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    head = doc.elements[0]
    assert head.source_locator["cell_index"] == 0
    assert head.source_locator["cell_type"] == "markdown"


def test_code_cell_locator_no_line(tmp_path: Path):
    """code cell locator 只含 cell_index/cell_type，无 line。"""
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "code", "source": "x = 1"}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    loc = doc.elements[0].source_locator
    assert "line" not in loc
    assert loc["cell_index"] == 0
    assert loc["cell_type"] == "code"


def test_markdown_cell_locator_section_path_local_to_cell(tmp_path: Path):
    """markdown cell 的 section_path 是该 cell 内的标题栈。"""
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "markdown", "source": "# A\n\n## B\n\nbody"}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    para = next(e for e in doc.elements if e.type == "paragraph")
    assert para.source_locator.get("section_path") == "A > B"


def test_markdown_cells_have_independent_section_paths(tmp_path: Path):
    """两个 markdown cell 的 section_path 不跨 cell 累积。"""
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "markdown", "source": "# A"},
        {"cell_type": "markdown", "source": "# B\n\nbody"},
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    bodies = [e for e in doc.elements if e.type == "paragraph"]
    if bodies:
        # 第二个 cell 的 body，section_path 应只有 B
        assert bodies[0].source_locator.get("section_path") == "B"


# =========================================================================
# element_id 格式
# =========================================================================


def test_element_id_zero_padded(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "code", "source": "a"},
        {"cell_type": "code", "source": "b"},
        {"cell_type": "code", "source": "c"},
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    ids = [e.element_id for e in doc.elements]
    assert ids[0].endswith("::e0000")
    assert ids[1].endswith("::e0001")
    assert ids[2].endswith("::e0002")


def test_element_id_starts_with_document_id(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "code", "source": "x"}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].element_id.startswith(doc.document_id)


def test_element_confidence_095(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "code", "source": "x"}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].confidence == 0.95


# =========================================================================
# Document metadata
# =========================================================================


def test_document_metadata_ipynb_true(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.metadata.get("ipynb") is True


def test_document_metadata_cell_count(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "code", "source": "a"},
        {"cell_type": "code", "source": "b"},
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.metadata.get("cell_count") == 2


def test_document_metadata_language(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook(
        [],
        metadata={"kernelspec": {"language": "python"}},
    )
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.metadata.get("language") == "python"


def test_document_metadata_nbformat_minor(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = {"nbformat": 4, "nbformat_minor": 2, "cells": []}
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.metadata.get("nbformat_minor") == 2


def test_document_metadata_keys_count(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    expected = {"ipynb", "nbformat", "nbformat_minor", "cell_count", "language"}
    assert expected.issubset(set(doc.metadata.keys()))


def test_document_chunks_relations_errors_empty(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "code", "source": "x"}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []


# =========================================================================
# 综合行为：多 cell 类型混合
# =========================================================================


def test_mixed_cell_types(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "markdown", "source": "# Title"},
        {"cell_type": "code", "source": "x = 1"},
        {"cell_type": "raw", "source": "raw"},
        {"cell_type": "markdown", "source": "## Section"},
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    types = [e.type for e in doc.elements]
    # heading + paragraph (code) + paragraph (raw) + heading
    assert types.count("heading") == 2
    assert types.count("paragraph") == 2


def test_code_cell_text_is_stripped(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "code", "source": "  x = 1  \n"}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].content == "x = 1"


def test_raw_cell_text_is_stripped(tmp_path: Path):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([
        {"cell_type": "raw", "source": "  raw text  "}
    ])
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc = IpynbParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].content == "raw text"


# =========================================================================
# 文件 IO 失败
# =========================================================================


def test_parse_file_not_found_raises(tmp_path: Path):
    p = tmp_path / "missing.ipynb"
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_unsupported_suffix_raises(tmp_path: Path):
    p = tmp_path / "t.txt"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "unsupported_type"


def test_parse_oserror_raises_read_failed(tmp_path: Path, monkeypatch):
    p = tmp_path / "t.ipynb"
    nb = _make_notebook([])
    p.write_text(json.dumps(nb), encoding="utf-8")

    def _raise(*args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "open", _raise)
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "ipynb_read_failed"


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_all_only_ipynb_parser():
    from app.parsers.ipynb_parser import __all__
    assert __all__ == ["IpynbParser"]


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
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "MarkdownParser" in src


def test_module_imports_parser_base():
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "from app.parsers.base import" in src


def test_module_uses_future_annotations():
    import app.parsers.ipynb_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.parsers.ipynb_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_jupyter():
    import app.parsers.ipynb_parser as mod
    assert "Jupyter" in mod.__doc__ or "Notebook" in mod.__doc__


def test_module_docstring_mentions_markdown():
    import app.parsers.ipynb_parser as mod
    assert "markdown" in mod.__doc__.lower() or "Markdown" in mod.__doc__


def test_module_docstring_mentions_nbformat():
    import app.parsers.ipynb_parser as mod
    assert "nbformat" in mod.__doc__.lower()


def test_module_docstring_mentions_cell_type():
    import app.parsers.ipynb_parser as mod
    assert "cell" in mod.__doc__.lower()


# =========================================================================
# 签名深度
# =========================================================================


def test_detect_ipynb_source_type_signature_one_param():
    sig = inspect.signature(_detect_ipynb_source_type)
    assert len(sig.parameters) == 1


def test_cell_source_to_text_signature_one_param():
    sig = inspect.signature(_cell_source_to_text)
    assert len(sig.parameters) == 1


def test_extract_kernel_language_signature_one_param():
    sig = inspect.signature(_extract_kernel_language)
    assert len(sig.parameters) == 1


def test_ipynb_parser_parse_signature_three_params():
    sig = inspect.signature(IpynbParser.parse)
    # self, path, source_hash
    assert len(sig.parameters) == 3


def test_ipynb_parser_parse_no_defaults():
    sig = inspect.signature(IpynbParser.parse)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty
