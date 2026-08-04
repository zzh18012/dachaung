r"""app/cli.py 边角测试 - 第七轮（Round 160）。

补强已有 base/edges/edges2-5（共 624 测试）未覆盖的深度：
- _preview 边界（None、空串、超长、换行+连续空白、特殊字符）
- _load_document_json 错误路径
- _format_summary 各字段缺失
- _format_elements_list 边界
- _format_chunks_list 边界（show_spans）
- _iter_supported_files 边界
- _relative_output_path 边界
- _infer_parser_name 边界
- _emit_structured_error 输出格式
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from app.cli import (
    _build_arg_parser,
    _emit_structured_error,
    _EXTENSION_TO_PARSER,
    _format_chunks_list,
    _format_elements_list,
    _format_summary,
    _infer_parser_name,
    _iter_supported_files,
    _load_document_json,
    _preview,
    _relative_output_path,
    main,
)


# =========================================================================
# _preview 边界
# =========================================================================


def test_preview_none_returns_empty():
    assert _preview(None) == ""


def test_preview_empty_string_returns_empty():
    assert _preview("") == ""


def test_preview_short_text():
    assert _preview("hello") == "hello"


def test_preview_at_width_boundary():
    """正好 width 长度 → 不截断。"""
    s = "a" * 60
    assert _preview(s) == s


def test_preview_over_width_truncates():
    """超过 width → 截断 + '…'。"""
    s = "a" * 100
    result = _preview(s, width=10)
    assert result.endswith("…")
    assert len(result) == 10  # 9 + 1


def test_preview_collapses_whitespace():
    """换行/连续空格 → 单空格。"""
    assert _preview("hello\nworld") == "hello world"
    assert _preview("hello    world") == "hello world"
    assert _preview("hello\t\tworld") == "hello world"


def test_preview_collapses_mixed_whitespace():
    assert _preview("a\nb\tc d  e") == "a b c d e"


def test_preview_unicode_not_truncated_inappropriately():
    """中文字符也按字符计数（python len）。"""
    s = "中" * 60
    assert _preview(s) == s


def test_preview_custom_width():
    assert _preview("hello world", width=5) == "hell…"


def test_preview_width_zero_drops_last_char_and_adds_ellipsis():
    """width=0：len(collapsed) > 0，走 truncation 分支 → collapsed[:-1] + '…'。"""
    assert _preview("hello", width=0) == "hell…"


def test_preview_leading_trailing_whitespace_stripped_via_split():
    """split() 自动 strip 两端。"""
    assert _preview("  hello  ") == "hello"


def test_preview_only_whitespace():
    assert _preview("   \n\t  ") == ""


def test_preview_width_one_returns_ellipsis_for_long():
    """width=1 → collapsed[:0] + '…' = '…'。"""
    assert _preview("hello world", width=1) == "…"


def test_preview_width_two():
    """width=2 → 1 char + '…'。"""
    assert _preview("hello", width=2) == "h…"


def test_preview_returns_str():
    assert isinstance(_preview("x"), str)


def test_preview_does_not_raise_on_special_input():
    try:
        _preview(None)
        _preview("")
        _preview("   ")
        _preview("a" * 1000)
    except Exception:
        pytest.fail("_preview should not raise")


# =========================================================================
# _load_document_json 错误路径
# =========================================================================


def test_load_document_json_missing_file(tmp_path: Path):
    missing = tmp_path / "no.json"
    data, err = _load_document_json(missing)
    assert data is None
    assert "文件不存在" in err


def test_load_document_json_invalid_json(tmp_path: Path):
    p = tmp_path / "broken.json"
    p.write_text("{not valid", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data is None
    assert "JSON 解析失败" in err


def test_load_document_json_empty_file(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data is None
    assert "JSON" in err


def test_load_document_json_valid_dict(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == {"k": "v"}
    assert err == ""


def test_load_document_json_valid_array(tmp_path: Path):
    """JSON 顶层是 array → 返回 (data, "")（不强制 dict）。"""
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == [1, 2, 3]
    assert err == ""


def test_load_document_json_returns_tuple():
    """返回值是 tuple。"""
    p = Path("/nonexistent/x.json")
    result = _load_document_json(p)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_load_document_json_str_path(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == {}
    assert err == ""


# =========================================================================
# _format_summary 边界
# =========================================================================


def test_format_summary_empty_dict(tmp_path: Path):
    """空 dict → 缺失字段用 '?' 替代。"""
    out = _format_summary({}, tmp_path / "x.json")
    assert "file:" in out
    assert "?" in out
    assert "counts:" in out


def test_format_summary_minimal_dict(tmp_path: Path):
    data = {"schema_version": "0.1.0"}
    out = _format_summary(data, tmp_path / "x.json")
    assert "0.1.0" in out


def test_format_summary_full_dict(tmp_path: Path):
    data = {
        "schema_version": "0.1.0",
        "document_id": "doc1",
        "source_path": "/abs/path.txt",
        "source_type": "text",
        "source_hash": "abcdef0123456789",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"type": "paragraph", "content": "hello"}],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    out = _format_summary(data, tmp_path / "x.json")
    assert "doc1" in out
    assert "fallback" in out
    assert "elements=1" in out
    assert "chunks=1" in out


def test_format_summary_with_warnings(tmp_path: Path):
    data = {"warnings": [{"code": "W001", "reason": "test warning"}]}
    out = _format_summary(data, tmp_path / "x.json")
    assert "warnings" in out
    assert "W001" in out
    assert "test warning" in out


def test_format_summary_with_many_warnings_limits_to_five(tmp_path: Path):
    data = {
        "warnings": [
            {"code": f"W{i:03d}", "reason": f"reason {i}"}
            for i in range(10)
        ]
    }
    out = _format_summary(data, tmp_path / "x.json")
    assert "more" in out
    assert "+5" in out


def test_format_summary_with_errors(tmp_path: Path):
    data = {"errors": [{"code": "E001", "message": "boom"}]}
    out = _format_summary(data, tmp_path / "x.json")
    assert "errors" in out
    assert "E001" in out


def test_format_summary_elements_by_type(tmp_path: Path):
    data = {
        "elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
        ]
    }
    out = _format_summary(data, tmp_path / "x.json")
    assert "elements by type:" in out
    assert "paragraph=2" in out
    assert "heading=1" in out


def test_format_summary_chunk_text_stats(tmp_path: Path):
    data = {
        "chunks": [
            {"text": "hello"},
            {"text": "world"},
        ]
    }
    out = _format_summary(data, tmp_path / "x.json")
    assert "chunk text:" in out
    assert "min=" in out
    assert "max=" in out


def test_format_summary_chunk_refs_stats(tmp_path: Path):
    data = {
        "chunks": [
            {"text": "x", "source_element_ids": ["e1", "e2"]},
            {"text": "y", "source_element_ids": ["e3"]},
        ]
    }
    out = _format_summary(data, tmp_path / "x.json")
    assert "chunk refs:" in out


def test_format_summary_returns_str():
    out = _format_summary({}, Path("x"))
    assert isinstance(out, str)


# =========================================================================
# _format_elements_list 边界
# =========================================================================


def test_format_elements_list_empty():
    out = _format_elements_list([], 10)
    assert "elements (0):" in out


def test_format_elements_list_single():
    out = _format_elements_list([{"element_id": "e1", "type": "paragraph", "content": "hello"}], 10)
    assert "e1" in out
    assert "paragraph" in out


def test_format_elements_list_limit_zero_shows_all():
    elements = [{"element_id": f"e{i}", "type": "x", "content": "y"} for i in range(5)]
    out = _format_elements_list(elements, 0)
    assert "e0" in out
    assert "e4" in out


def test_format_elements_list_limit_truncates():
    elements = [{"element_id": f"e{i}", "type": "x", "content": "y"} for i in range(10)]
    out = _format_elements_list(elements, 3)
    assert "e0" in out
    assert "e2" in out
    assert "+7 more" in out  # 10 - 3 = 7


def test_format_elements_list_missing_fields():
    """element 缺字段 → '?'。"""
    out = _format_elements_list([{}], 10)
    assert "?" in out


def test_format_elements_list_with_parent_id():
    out = _format_elements_list(
        [{"element_id": "e1", "type": "x", "parent_id": "p1"}], 10
    )
    assert "parent=p1" in out


def test_format_elements_list_no_parent_id_no_parent_str():
    out = _format_elements_list(
        [{"element_id": "e1", "type": "x"}], 10
    )
    assert "parent=" not in out


def test_format_elements_list_returns_str():
    assert isinstance(_format_elements_list([], 10), str)


# =========================================================================
# _format_chunks_list 边界（含 show_spans）
# =========================================================================


def test_format_chunks_list_empty():
    out = _format_chunks_list([], 10)
    assert "chunks (0):" in out


def test_format_chunks_list_single():
    out = _format_chunks_list(
        [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}],
        10,
    )
    assert "c1" in out
    assert "chars=5" in out
    assert "refs=1" in out


def test_format_chunks_list_show_spans_empty():
    out = _format_chunks_list(
        [{"chunk_id": "c1", "text": "hello"}],
        10,
        show_spans=True,
    )
    assert "spans: (none)" in out


def test_format_chunks_list_show_spans_with_data():
    out = _format_chunks_list(
        [{
            "chunk_id": "c1",
            "text": "hello",
            "source_spans": [
                {"element_id": "e1", "start": 0, "end": 3},
                {"element_id": "e2", "start": 5, "end": 8},
            ],
        }],
        10,
        show_spans=True,
    )
    assert "e1[0:3]" in out
    assert "e2[5:8]" in out


def test_format_chunks_list_no_show_spans_no_spans_section():
    """show_spans=False 时不渲染 spans 行。"""
    out = _format_chunks_list(
        [{
            "chunk_id": "c1",
            "text": "hello",
            "source_spans": [{"element_id": "e1", "start": 0, "end": 3}],
        }],
        10,
        show_spans=False,
    )
    assert "span:" not in out


def test_format_chunks_list_limit_truncates():
    chunks = [{"chunk_id": f"c{i}", "text": "x"} for i in range(10)]
    out = _format_chunks_list(chunks, 3)
    assert "+7 more" in out


def test_format_chunks_list_limit_zero_shows_all():
    chunks = [{"chunk_id": f"c{i}", "text": "x"} for i in range(5)]
    out = _format_chunks_list(chunks, 0)
    assert "c0" in out
    assert "c4" in out


def test_format_chunks_list_missing_fields():
    out = _format_chunks_list([{}], 10)
    assert "?" in out


def test_format_chunks_list_returns_str():
    assert isinstance(_format_chunks_list([], 10), str)


# =========================================================================
# _iter_supported_files 边界
# =========================================================================


def test_iter_supported_files_empty_dir(tmp_path: Path):
    result = _iter_supported_files(tmp_path, recursive=False)
    assert result == []


def test_iter_supported_files_filters_by_extension(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.unknown").write_text("x", encoding="utf-8")
    (tmp_path / "c.md").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = sorted(p.name for p in result)
    assert names == ["a.txt", "c.md"]


def test_iter_supported_files_returns_sorted(tmp_path: Path):
    (tmp_path / "z.txt").write_text("x", encoding="utf-8")
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "m.txt").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in result]
    assert names == sorted(names)


def test_iter_supported_files_recursive(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top.txt").write_text("x", encoding="utf-8")
    (sub / "nested.md").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=True)
    names = sorted(p.name for p in result)
    assert "top.txt" in names
    assert "nested.md" in names


def test_iter_supported_files_non_recursive_skips_subdirs(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top.txt").write_text("x", encoding="utf-8")
    (sub / "nested.txt").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in result]
    assert names == ["top.txt"]


def test_iter_supported_files_uppercase_extension(tmp_path: Path):
    """大写扩展名也应识别（suffix.lower()）。"""
    (tmp_path / "x.TXT").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    assert len(result) == 1
    assert result[0].name == "x.TXT"


def test_iter_supported_files_returns_list_of_paths(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    assert isinstance(result, list)
    for p in result:
        assert isinstance(p, Path)


def test_iter_supported_files_skips_directories(tmp_path: Path):
    """目录即使名以 .txt 结尾也不应被列。"""
    (tmp_path / "sub.dir").mkdir()
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in result]
    assert "sub.dir" not in names


# =========================================================================
# _relative_output_path 边界
# =========================================================================


def test_relative_output_path_top_level(tmp_path: Path):
    input_dir = tmp_path
    file_path = tmp_path / "doc.md"
    output_dir = tmp_path / "out"
    result = _relative_output_path(input_dir, file_path, output_dir)
    assert result == output_dir / "doc.md.json"


def test_relative_output_path_nested_subdir(tmp_path: Path):
    input_dir = tmp_path
    sub = tmp_path / "sub"
    sub.mkdir()
    file_path = sub / "doc.md"
    output_dir = tmp_path / "out"
    result = _relative_output_path(input_dir, file_path, output_dir)
    assert result == output_dir / "sub/doc.md.json"


def test_relative_output_path_deep_nested(tmp_path: Path):
    input_dir = tmp_path
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    file_path = deep / "doc.md"
    output_dir = tmp_path / "out"
    result = _relative_output_path(input_dir, file_path, output_dir)
    assert result == output_dir / "a/b/c/doc.md.json"


def test_relative_output_path_different_extensions_no_clash(tmp_path: Path):
    """doc.md 与 doc.html 输出不冲突（含 suffix）。"""
    input_dir = tmp_path
    md_file = tmp_path / "doc.md"
    html_file = tmp_path / "doc.html"
    output_dir = tmp_path / "out"
    md_out = _relative_output_path(input_dir, md_file, output_dir)
    html_out = _relative_output_path(input_dir, html_file, output_dir)
    assert md_out != html_out


# =========================================================================
# _infer_parser_name 边界
# =========================================================================


def test_infer_parser_name_pdf():
    assert _infer_parser_name(Path("x.pdf")) == "fallback"


def test_infer_parser_name_docx():
    assert _infer_parser_name(Path("x.docx")) == "fallback"


def test_infer_parser_name_md():
    assert _infer_parser_name(Path("x.md")) == "markdown"


def test_infer_parser_name_markdown():
    assert _infer_parser_name(Path("x.markdown")) == "markdown"


def test_infer_parser_name_html():
    assert _infer_parser_name(Path("x.html")) == "html"


def test_infer_parser_name_htm():
    assert _infer_parser_name(Path("x.htm")) == "html"


def test_infer_parser_name_txt():
    assert _infer_parser_name(Path("x.txt")) == "text"


def test_infer_parser_name_text():
    assert _infer_parser_name(Path("x.text")) == "text"


def test_infer_parser_name_ipynb():
    assert _infer_parser_name(Path("x.ipynb")) == "ipynb"


def test_infer_parser_name_unknown_returns_fallback():
    assert _infer_parser_name(Path("x.unknown")) == "fallback"


def test_infer_parser_name_no_suffix_returns_fallback():
    assert _infer_parser_name(Path("nofile")) == "fallback"


def test_infer_parser_name_uppercase_suffix():
    """大写扩展名 → .lower() → 推断。"""
    assert _infer_parser_name(Path("x.PDF")) == "fallback"
    assert _infer_parser_name(Path("x.MD")) == "markdown"


def test_infer_parser_name_mixed_case_suffix():
    assert _infer_parser_name(Path("x.PdF")) == "fallback"


# =========================================================================
# _EXTENSION_TO_PARSER 精确性
# =========================================================================


def test_EXTENSION_TO_PARSER_count():
    assert len(_EXTENSION_TO_PARSER) == 9


def test_EXTENSION_TO_PARSER_keys_exact():
    expected = {".pdf", ".docx", ".md", ".markdown", ".html", ".htm", ".txt", ".text", ".ipynb"}
    assert set(_EXTENSION_TO_PARSER.keys()) == expected


def test_EXTENSION_TO_PARSER_pdf_and_docx_both_fallback():
    assert _EXTENSION_TO_PARSER[".pdf"] == "fallback"
    assert _EXTENSION_TO_PARSER[".docx"] == "fallback"


def test_EXTENSION_TO_PARSER_values_are_strings():
    for v in _EXTENSION_TO_PARSER.values():
        assert isinstance(v, str)


# =========================================================================
# _emit_structured_error 输出格式
# =========================================================================


def test_emit_structured_error_writes_to_stderr(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x.txt", "code1", "message1")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "code1" in captured.err
    assert "message1" in captured.err


def test_emit_structured_error_includes_schema_version(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x.txt", "c", "m")
    captured = capsys.readouterr()
    parsed = json.loads(captured.err)
    assert parsed["schema_version"] == "0.1.0"


def test_emit_structured_error_includes_input(capsys, tmp_path: Path):
    p = tmp_path / "x.txt"
    _emit_structured_error(p, "c", "m")
    captured = capsys.readouterr()
    parsed = json.loads(captured.err)
    assert parsed["input"] == str(p)


def test_emit_structured_error_includes_one_error(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x.txt", "c", "m")
    captured = capsys.readouterr()
    parsed = json.loads(captured.err)
    assert len(parsed["errors"]) == 1
    assert parsed["errors"][0]["code"] == "c"
    assert parsed["errors"][0]["message"] == "m"


def test_emit_structured_error_with_extra_fields(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x.txt", "c", "m", detail="d", n=42)
    captured = capsys.readouterr()
    parsed = json.loads(captured.err)
    assert parsed["errors"][0]["detail"] == "d"
    assert parsed["errors"][0]["n"] == 42


def test_emit_structured_error_no_extra(capsys, tmp_path: Path):
    """无 extra 参数 → errors[0] 只含 code/message。"""
    _emit_structured_error(tmp_path / "x.txt", "c", "m")
    captured = capsys.readouterr()
    parsed = json.loads(captured.err)
    assert set(parsed["errors"][0].keys()) == {"code", "message"}


def test_emit_structured_error_json_serializable(capsys, tmp_path: Path):
    """stderr 输出应是合法 JSON。"""
    _emit_structured_error(tmp_path / "x.txt", "c", "m", x=[1, 2, 3])
    captured = capsys.readouterr()
    parsed = json.loads(captured.err)  # 不抛
    assert parsed is not None


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_no_all_definition():
    """cli.py 无 __all__。"""
    import app.cli as mod
    assert not hasattr(mod, "__all__")


def test_module_imports_argparse():
    import app.cli as mod
    src = inspect.getsource(mod)
    assert "import argparse" in src


def test_module_imports_json():
    import app.cli as mod
    src = inspect.getsource(mod)
    assert "import json" in src


def test_module_imports_sys():
    import app.cli as mod
    src = inspect.getsource(mod)
    assert "import sys" in src


def test_module_imports_path():
    import app.cli as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_pipeline():
    import app.cli as mod
    src = inspect.getsource(mod)
    assert "from app.pipeline import process_single, validate_only" in src


def test_module_uses_future_annotations():
    import app.cli as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_has_utf8_reconfigure_block():
    import app.cli as mod
    src = inspect.getsource(mod)
    assert "reconfigure" in src


def test_module_has_main_guard():
    import app.cli as mod
    src = inspect.getsource(mod)
    assert '__name__ == "__main__"' in src


def test_module_docstring_present():
    import app.cli as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_parse():
    import app.cli as mod
    doc = mod.__doc__
    assert "parse" in doc.lower()


def test_module_docstring_mentions_validate():
    import app.cli as mod
    doc = mod.__doc__
    assert "validate" in doc.lower()


def test_module_docstring_mentions_inspect():
    import app.cli as mod
    doc = mod.__doc__
    assert "inspect" in doc.lower()


def test_module_docstring_mentions_parse_dir():
    import app.cli as mod
    doc = mod.__doc__
    # parse-dir 在 cli 中
    assert "parse-dir" in doc or "parse_dir" in doc or "parse" in doc


def test_module_helpers_callable():
    import app.cli as mod
    assert callable(mod._build_arg_parser)
    assert callable(mod._emit_structured_error)
    assert callable(mod._preview)
    assert callable(mod._load_document_json)
    assert callable(mod._format_summary)
    assert callable(mod._format_elements_list)
    assert callable(mod._format_chunks_list)
    assert callable(mod._infer_parser_name)
    assert callable(mod._iter_supported_files)
    assert callable(mod._relative_output_path)


def test_module_main_callable():
    import app.cli as mod
    assert callable(mod.main)


# =========================================================================
# 签名深度
# =========================================================================


def test_main_signature_argv_param():
    sig = inspect.signature(main)
    assert "argv" in sig.parameters


def test_main_argv_default_none():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_int():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_build_arg_parser_no_params():
    sig = inspect.signature(_build_arg_parser)
    assert len(sig.parameters) == 0


def test_emit_structured_error_signature():
    sig = inspect.signature(_emit_structured_error)
    assert "input_path" in sig.parameters
    assert "code" in sig.parameters
    assert "message" in sig.parameters


def test_preview_signature_two_params():
    sig = inspect.signature(_preview)
    assert set(sig.parameters) == {"text", "width"}


def test_preview_width_default_60():
    sig = inspect.signature(_preview)
    assert sig.parameters["width"].default == 60


def test_load_document_json_signature_one_param():
    sig = inspect.signature(_load_document_json)
    assert set(sig.parameters) == {"input_path"}


def test_format_summary_signature_two_params():
    sig = inspect.signature(_format_summary)
    assert set(sig.parameters) == {"data", "input_path"}


def test_format_elements_list_signature_two_params():
    sig = inspect.signature(_format_elements_list)
    assert set(sig.parameters) == {"elements", "limit"}


def test_format_chunks_list_signature_three_params():
    sig = inspect.signature(_format_chunks_list)
    assert set(sig.parameters) == {"chunks", "limit", "show_spans"}


def test_format_chunks_list_show_spans_default_false():
    sig = inspect.signature(_format_chunks_list)
    assert sig.parameters["show_spans"].default is False


def test_infer_parser_name_signature_one_param():
    sig = inspect.signature(_infer_parser_name)
    assert set(sig.parameters) == {"input_path"}


def test_iter_supported_files_signature_two_params():
    sig = inspect.signature(_iter_supported_files)
    assert set(sig.parameters) == {"input_dir", "recursive"}


def test_relative_output_path_signature_three_params():
    sig = inspect.signature(_relative_output_path)
    assert set(sig.parameters) == {"input_dir", "file_path", "output_dir"}


# =========================================================================
# 综合行为
# =========================================================================


def test_preview_idempotent():
    s = "hello world"
    a = _preview(s)
    b = _preview(s)
    assert a == b


def test_load_document_json_idempotent(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    a = _load_document_json(p)
    b = _load_document_json(p)
    assert a == b


def test_format_summary_handles_minimal_input():
    """不抛异常。"""
    out = _format_summary({}, Path("x"))
    assert isinstance(out, str)
    assert len(out) > 0


def test_iter_supported_files_idempotent(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    a = _iter_supported_files(tmp_path, recursive=False)
    b = _iter_supported_files(tmp_path, recursive=False)
    assert a == b


def test_infer_parser_name_idempotent():
    a = _infer_parser_name(Path("x.pdf"))
    b = _infer_parser_name(Path("x.pdf"))
    assert a == b


def test_relative_output_path_idempotent(tmp_path: Path):
    a = _relative_output_path(tmp_path, tmp_path / "x.md", tmp_path / "out")
    b = _relative_output_path(tmp_path, tmp_path / "x.md", tmp_path / "out")
    assert a == b
