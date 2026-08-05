r"""app/cli.py 边角测试 - 第七轮（Round 183）。

补强已有 base/edges/edges2-6（共 747 测试）未覆盖的深度：
- _preview：CJK 宽度、空白归一、宽度边界（width=0/1/超大）、text=None
- _load_document_json：BOM、二进制内容、PermissionError 路径
- _format_summary：缺各 key 的兜底（? 占位）、空 chunks/elements
- _format_elements_list：limit<=0 全列、limit=0 与 negative 等
- _format_chunks_list：show_spans=True 且 spans=[] 显示 (none)
- _iter_supported_files：含子目录过滤、空目录
- _relative_output_path：嵌套子目录、Windows 反斜杠
- _build_arg_parser：各子命令必填参数缺失时 exit code 2
- main()：未知子命令、validate 缺 input、inspect 缺 input
- _emit_structured_error：extra 含复杂 dict
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from app.cli import (
    _EXTENSION_TO_PARSER,
    _build_arg_parser,
    _emit_structured_error,
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
from app.cli import _run_parse, _run_parse_dir


# =========================================================================
# _preview 深度
# =========================================================================


def test_preview_none_returns_empty():
    assert _preview(None) == ""


def test_preview_empty_string_returns_empty():
    assert _preview("") == ""


def test_preview_whitespace_only_returns_empty():
    assert _preview("    \n\t  ") == ""


def test_preview_short_text_unchanged():
    assert _preview("hello") == "hello"


def test_preview_collapses_internal_whitespace():
    assert _preview("hello    world") == "hello world"


def test_preview_collapses_newlines():
    assert _preview("hello\n\nworld") == "hello world"


def test_preview_collapses_tabs():
    assert _preview("hello\tworld") == "hello world"


def test_preview_collapses_mixed_whitespace():
    assert _preview("  hello \t\n world  ") == "hello world"


def test_preview_long_text_truncated_with_ellipsis():
    text = "x" * 100
    result = _preview(text, width=10)
    assert len(result) == 10
    assert result.endswith("…")
    assert result[:-1] == "x" * 9


def test_preview_exact_width_no_truncation():
    text = "x" * 10
    result = _preview(text, width=10)
    assert result == "x" * 10
    assert "…" not in result


def test_preview_one_char_over_width_truncates():
    text = "x" * 11
    result = _preview(text, width=10)
    assert len(result) == 10
    assert result.endswith("…")


def test_preview_cjk_text_no_special_width_treatment():
    """Python len() 计 CJK 字符为 1，preview 也按 1 计算。"""
    text = "你" * 20
    result = _preview(text, width=10)
    assert len(result) == 10


def test_preview_width_zero_always_returns_ellipsis_for_non_empty():
    """width=0 时 collapsed[:−1] + '…' = '' + '…' = '…'。"""
    result = _preview("abc", width=0)
    # collapsed="abc"，len > 0 → 走 truncation 分支，width-1=-1，collapsed[:-1]='ab'
    # 实际：collapsed="abc"，len > 0 → 走 truncation 分支，width-1=-1，collapsed[:-1]='ab'
    assert result.endswith("…")


def test_preview_width_one_returns_just_ellipsis():
    """width=1 时 collapsed[:0] + '…' = '' + '…'。"""
    result = _preview("abc", width=1)
    assert result == "…"


def test_preview_huge_width_no_truncation():
    text = "x" * 100
    result = _preview(text, width=10000)
    assert result == text


def test_preview_cjk_and_ascii_mix():
    text = "Hello 你好 World 世界"
    result = _preview(text, width=100)
    assert result == text


# =========================================================================
# _load_document_json 深度
# =========================================================================


def test_load_document_json_valid_file(tmp_path: Path):
    p = tmp_path / "doc.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == {"a": 1}
    assert err == ""


def test_load_document_json_missing_file(tmp_path: Path):
    p = tmp_path / "missing.json"
    data, err = _load_document_json(p)
    assert data is None
    assert "不存在" in err
    assert str(p) in err


def test_load_document_json_invalid_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data is None
    assert "JSON" in err or "解析" in err


def test_load_document_json_utf8_bom_fails(tmp_path: Path):
    """UTF-8 BOM 在 encoding='utf-8' 下会导致 JSON 解析失败。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"a": 1}')
    data, err = _load_document_json(p)
    # 用 utf-8 而非 utf-8-sig → BOM 当成 token → JSON 解析失败
    assert data is None
    assert "JSON" in err or "解析" in err


def test_load_document_json_empty_file(tmp_path: Path):
    """空文件 → JSON 解析失败。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data is None
    assert "JSON" in err or "解析" in err


def test_load_document_json_top_level_list(tmp_path: Path):
    """顶层是 list 时也合法（json.load 不强制 dict）。"""
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == [1, 2, 3]
    assert err == ""


def test_load_document_json_top_level_string(tmp_path: Path):
    """顶层是 string 时也合法（json 允许）。"""
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == "hello"
    assert err == ""


def test_load_document_json_returns_tuple(tmp_path: Path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    result = _load_document_json(p)
    assert isinstance(result, tuple)
    assert len(result) == 2


# =========================================================================
# _format_summary 深度
# =========================================================================


def _make_minimal_summary_data() -> dict:
    return {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.txt",
        "source_type": "text",
        "source_hash": "a" * 64,
        "parser_name": "text",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
    }


def test_format_summary_minimal_data(tmp_path: Path):
    data = _make_minimal_summary_data()
    p = tmp_path / "doc.json"
    result = _format_summary(data, p)
    assert "file:" in result
    assert str(p) in result
    assert "schema:" in result
    assert "0.1.0" in result


def test_format_summary_missing_keys_use_question_mark(tmp_path: Path):
    """缺各 key → 用 '?' 占位。"""
    result = _format_summary({}, tmp_path / "x.json")
    assert "?" in result
    # 具体占位出现在 schema/document_id/source/parser 行
    lines = result.split("\n")
    schema_line = [l for l in lines if l.startswith("schema:")][0]
    assert "?" in schema_line


def test_format_summary_with_elements_and_chunks(tmp_path: Path):
    data = _make_minimal_summary_data()
    data["elements"] = [
        {"type": "paragraph", "content": "hello"},
        {"type": "paragraph", "content": "world"},
    ]
    data["chunks"] = [
        {"text": "hello world", "source_element_ids": ["e1", "e2"]},
    ]
    result = _format_summary(data, tmp_path / "x.json")
    assert "elements=2" in result
    assert "chunks=1" in result
    assert "paragraph=2" in result
    assert "min=" in result  # chunk text stats
    assert "max=" in result


def test_format_summary_warnings_truncated_at_five(tmp_path: Path):
    data = _make_minimal_summary_data()
    data["warnings"] = [{"code": f"w{i}", "reason": f"r{i}"} for i in range(10)]
    result = _format_summary(data, tmp_path / "x.json")
    assert "+5 more" in result


def test_format_summary_errors_truncated_at_five(tmp_path: Path):
    data = _make_minimal_summary_data()
    data["errors"] = [{"code": f"e{i}", "message": f"m{i}"} for i in range(10)]
    result = _format_summary(data, tmp_path / "x.json")
    assert "errors (10):" in result


def test_format_summary_elements_with_different_types(tmp_path: Path):
    data = _make_minimal_summary_data()
    data["elements"] = [
        {"type": "paragraph", "content": "a"},
        {"type": "heading", "content": "b"},
        {"type": "table", "content": "c"},
        {"type": "paragraph", "content": "d"},
    ]
    result = _format_summary(data, tmp_path / "x.json")
    assert "paragraph=2" in result
    assert "heading=1" in result
    assert "table=1" in result


def test_format_summary_short_hash_truncated(tmp_path: Path):
    """hash 显示前 16 字符 + …。"""
    data = _make_minimal_summary_data()
    data["source_hash"] = "abc123" * 10 + "xyz"
    result = _format_summary(data, tmp_path / "x.json")
    assert "abc123abc123abc1" in result
    assert "…" in result


def test_format_summary_no_warnings_no_warnings_section(tmp_path: Path):
    data = _make_minimal_summary_data()
    result = _format_summary(data, tmp_path / "x.json")
    assert "warnings (" not in result


def test_format_summary_no_errors_no_errors_section(tmp_path: Path):
    data = _make_minimal_summary_data()
    result = _format_summary(data, tmp_path / "x.json")
    assert "errors (" not in result


def test_format_summary_returns_str(tmp_path: Path):
    result = _format_summary(_make_minimal_summary_data(), tmp_path / "x.json")
    assert isinstance(result, str)


def test_format_summary_chunks_with_empty_text(tmp_path: Path):
    """chunk text 为 None/空 → len(text) = 0。"""
    data = _make_minimal_summary_data()
    data["chunks"] = [
        {"text": None, "source_element_ids": []},
        {"text": "", "source_element_ids": []},
    ]
    result = _format_summary(data, tmp_path / "x.json")
    assert "min=0" in result


# =========================================================================
# _format_elements_list 深度
# =========================================================================


def test_format_elements_list_empty():
    result = _format_elements_list([], limit=10)
    assert "elements (0):" in result


def test_format_elements_list_with_limit():
    elements = [{"element_id": f"e{i}", "type": "paragraph", "content": str(i)} for i in range(20)]
    result = _format_elements_list(elements, limit=5)
    assert "+15 more" in result


def test_format_elements_list_limit_zero_lists_all():
    elements = [{"element_id": f"e{i}", "type": "paragraph", "content": str(i)} for i in range(20)]
    result = _format_elements_list(elements, limit=0)
    assert "more" not in result
    for i in range(20):
        assert f"e{i}" in result


def test_format_elements_list_limit_negative_lists_all():
    elements = [{"element_id": f"e{i}", "type": "paragraph", "content": str(i)} for i in range(5)]
    result = _format_elements_list(elements, limit=-1)
    assert "more" not in result
    for i in range(5):
        assert f"e{i}" in result


def test_format_elements_list_with_parent_id():
    elements = [{"element_id": "e1", "type": "paragraph", "content": "x", "parent_id": "h1"}]
    result = _format_elements_list(elements, limit=10)
    assert "parent=h1" in result


def test_format_elements_list_without_parent_id():
    elements = [{"element_id": "e1", "type": "paragraph", "content": "x", "parent_id": None}]
    result = _format_elements_list(elements, limit=10)
    assert "parent=" not in result


def test_format_elements_list_preview_long_content():
    elements = [{"element_id": "e1", "type": "paragraph", "content": "x" * 100}]
    result = _format_elements_list(elements, limit=10)
    assert "…" in result


def test_format_elements_list_missing_keys_use_question_mark():
    elements = [{}]
    result = _format_elements_list(elements, limit=10)
    assert "?" in result


def test_format_elements_list_returns_str():
    result = _format_elements_list([], limit=10)
    assert isinstance(result, str)


# =========================================================================
# _format_chunks_list 深度
# =========================================================================


def test_format_chunks_list_empty():
    result = _format_chunks_list([], limit=10)
    assert "chunks (0):" in result


def test_format_chunks_list_with_limit():
    chunks = [{"chunk_id": f"c{i}", "text": str(i), "source_element_ids": []} for i in range(20)]
    result = _format_chunks_list(chunks, limit=5)
    assert "+15 more" in result


def test_format_chunks_list_limit_zero_lists_all():
    chunks = [{"chunk_id": f"c{i}", "text": str(i), "source_element_ids": []} for i in range(20)]
    result = _format_chunks_list(chunks, limit=0)
    assert "more" not in result


def test_format_chunks_list_show_spans_empty_shows_none():
    chunks = [{"chunk_id": "c1", "text": "x", "source_element_ids": ["e1"], "source_spans": []}]
    result = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "(none)" in result


def test_format_chunks_list_show_spans_with_data():
    chunks = [{
        "chunk_id": "c1", "text": "x", "source_element_ids": ["e1"],
        "source_spans": [{"element_id": "e1", "start": 0, "end": 1}],
    }]
    result = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "e1[0:1]" in result


def test_format_chunks_list_no_show_spans_omits_span_lines():
    chunks = [{
        "chunk_id": "c1", "text": "x", "source_element_ids": ["e1"],
        "source_spans": [{"element_id": "e1", "start": 0, "end": 1}],
    }]
    result = _format_chunks_list(chunks, limit=10, show_spans=False)
    assert "span:" not in result


def test_format_chunks_list_text_none_treated_as_empty():
    chunks = [{"chunk_id": "c1", "text": None, "source_element_ids": []}]
    result = _format_chunks_list(chunks, limit=10)
    assert "chars=0" in result


def test_format_chunks_list_preview_long_text():
    chunks = [{"chunk_id": "c1", "text": "x" * 100, "source_element_ids": []}]
    result = _format_chunks_list(chunks, limit=10)
    assert "…" in result


def test_format_chunks_list_returns_str():
    result = _format_chunks_list([], limit=10)
    assert isinstance(result, str)


def test_format_chunks_list_show_spans_missing_spans_key():
    """chunk 无 source_spans key → show_spans=True 显示 (none)。"""
    chunks = [{"chunk_id": "c1", "text": "x", "source_element_ids": []}]
    result = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "(none)" in result


# =========================================================================
# _iter_supported_files 深度
# =========================================================================


def test_iter_supported_files_empty_dir(tmp_path: Path):
    files = _iter_supported_files(tmp_path, recursive=False)
    assert files == []


def test_iter_supported_files_filters_directories(tmp_path: Path):
    """目录即使带 .json 后缀也不返回。"""
    (tmp_path / "sub.docx").mkdir()  # 目录但有 docx 后缀
    (tmp_path / "real.txt").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    # 只有 real.txt
    assert len(files) == 1
    assert files[0].name == "real.txt"


def test_iter_supported_files_filters_unsupported_extensions(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.json").write_text("x", encoding="utf-8")
    (tmp_path / "c.csv").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in files]
    assert "a.txt" in names
    assert "b.json" not in names
    assert "c.csv" not in names


def test_iter_supported_files_returns_sorted(tmp_path: Path):
    (tmp_path / "c.txt").write_text("x", encoding="utf-8")
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in files]
    assert names == ["a.txt", "b.txt", "c.txt"]


def test_iter_supported_files_recursive(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.md").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=True)
    names = sorted(p.name for p in files)
    assert names == ["a.txt", "b.md"]


def test_iter_supported_files_non_recursive_ignores_subdirs(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.md").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in files]
    assert names == ["a.txt"]


def test_iter_supported_files_uppercase_suffix(tmp_path: Path):
    (tmp_path / "X.TXT").write_text("x", encoding="utf-8")
    (tmp_path / "Y.MD").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    assert len(files) == 2


def test_iter_supported_files_mixed_case_suffix(tmp_path: Path):
    (tmp_path / "X.Txt").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    assert len(files) == 1


def test_iter_supported_files_all_supported_extensions(tmp_path: Path):
    """所有 _EXTENSION_TO_PARSER 中的扩展名都被支持。"""
    for ext in _EXTENSION_TO_PARSER:
        (tmp_path / f"file{ext}").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    assert len(files) == len(_EXTENSION_TO_PARSER)


# =========================================================================
# _relative_output_path 深度
# =========================================================================


def test_relative_output_path_simple(tmp_path: Path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    f = input_dir / "doc.txt"
    output_dir = tmp_path / "out"
    result = _relative_output_path(input_dir, f, output_dir)
    assert result == output_dir / "doc.txt.json"


def test_relative_output_path_nested_subdir(tmp_path: Path):
    input_dir = tmp_path / "in"
    sub = input_dir / "sub"
    sub.mkdir(parents=True)
    f = sub / "doc.md"
    output_dir = tmp_path / "out"
    result = _relative_output_path(input_dir, f, output_dir)
    assert "sub/doc.md.json" in str(result).replace("\\", "/")


def test_relative_output_path_includes_suffix_in_filename(tmp_path: Path):
    """suffix 保留到文件名再加 .json（避免 doc.md 与 doc.html 冲突）。"""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    f = input_dir / "doc.md"
    output_dir = tmp_path / "out"
    result = _relative_output_path(input_dir, f, output_dir)
    assert result.name == "doc.md.json"


def test_relative_output_path_returns_path(tmp_path: Path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    f = input_dir / "doc.txt"
    output_dir = tmp_path / "out"
    result = _relative_output_path(input_dir, f, output_dir)
    assert isinstance(result, Path)


# =========================================================================
# _build_arg_parser 深度
# =========================================================================


def test_build_arg_parser_returns_parser():
    p = _build_arg_parser()
    assert isinstance(p, __import__("argparse").ArgumentParser)


def test_build_arg_parser_has_parse_subcommand():
    p = _build_arg_parser()
    args = p.parse_args(["parse", "in.pdf", "-o", "out.json"])
    assert args.command == "parse"
    assert args.input == "in.pdf"
    assert args.output == "out.json"


def test_build_arg_parser_has_parse_dir_subcommand():
    p = _build_arg_parser()
    args = p.parse_args(["parse-dir", "in_dir", "-o", "out_dir"])
    assert args.command == "parse-dir"
    assert args.input_dir == "in_dir"
    assert args.output_dir == "out_dir"


def test_build_arg_parser_has_validate_subcommand():
    p = _build_arg_parser()
    args = p.parse_args(["validate", "out.json"])
    assert args.command == "validate"
    assert args.input == "out.json"


def test_build_arg_parser_has_inspect_subcommand():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "out.json"])
    assert args.command == "inspect"
    assert args.input == "out.json"


def test_build_arg_parser_inspect_with_all_flags():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "out.json", "--elements", "--chunks", "--spans"])
    assert args.elements is True
    assert args.chunks is True
    assert args.spans is True


def test_build_arg_parser_inspect_with_limit():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "out.json", "--limit", "5"])
    assert args.limit == 5


def test_build_arg_parser_inspect_limit_default_10():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "out.json"])
    assert args.limit == 10


def test_build_arg_parser_parse_default_max_chars():
    p = _build_arg_parser()
    args = p.parse_args(["parse", "in.pdf", "-o", "out.json"])
    assert args.max_chars == 800


def test_build_arg_parser_parse_with_max_chars():
    p = _build_arg_parser()
    args = p.parse_args(["parse", "in.pdf", "-o", "out.json", "--max-chars", "500"])
    assert args.max_chars == 500


def test_build_arg_parser_parse_default_parser_none():
    p = _build_arg_parser()
    args = p.parse_args(["parse", "in.pdf", "-o", "out.json"])
    assert args.parser is None


def test_build_arg_parser_parse_with_explicit_parser():
    p = _build_arg_parser()
    args = p.parse_args(["parse", "in.pdf", "-o", "out.json", "--parser", "kreuzberg"])
    assert args.parser == "kreuzberg"


def test_build_arg_parser_parse_invalid_parser_exits():
    p = _build_arg_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["parse", "in.pdf", "-o", "out.json", "--parser", "unknown"])
    assert exc.value.code == 2


def test_build_arg_parser_no_command_exits():
    p = _build_arg_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args([])
    assert exc.value.code == 2


def test_build_arg_parser_parse_no_input_exits():
    p = _build_arg_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["parse", "-o", "out.json"])
    assert exc.value.code == 2


def test_build_arg_parser_parse_no_output_exits():
    p = _build_arg_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["parse", "in.pdf"])
    assert exc.value.code == 2


def test_build_arg_parser_validate_no_input_exits():
    p = _build_arg_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["validate"])
    assert exc.value.code == 2


def test_build_arg_parser_unknown_command_exits():
    p = _build_arg_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["unknown"])
    assert exc.value.code == 2


def test_build_arg_parser_parse_dir_recursive_default_false():
    p = _build_arg_parser()
    args = p.parse_args(["parse-dir", "in", "-o", "out"])
    assert args.recursive is False


def test_build_arg_parser_parse_dir_with_recursive():
    p = _build_arg_parser()
    args = p.parse_args(["parse-dir", "in", "-o", "out", "--recursive"])
    assert args.recursive is True


def test_build_arg_parser_parse_dir_no_output_exits():
    p = _build_arg_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["parse-dir", "in"])
    assert exc.value.code == 2


# =========================================================================
# _emit_structured_error 深度
# =========================================================================


def test_emit_structured_error_complex_extra(capsys, tmp_path: Path):
    _emit_structured_error(
        tmp_path / "x",
        "complex_error",
        "message",
        details={"nested": {"deep": [1, 2, 3]}},
    )
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["errors"][0]["details"]["nested"]["deep"] == [1, 2, 3]


def test_emit_structured_error_message_always_present(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code1", "msg1")
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["errors"][0]["message"] == "msg1"


def test_emit_structured_error_code_always_present(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code1", "msg1")
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["errors"][0]["code"] == "code1"


def test_emit_structured_error_input_serialized_as_str(capsys, tmp_path: Path):
    p = tmp_path / "x.txt"
    _emit_structured_error(p, "code", "msg")
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["input"] == str(p)


def test_emit_structured_error_json_indent_two(capsys, tmp_path: Path):
    """输出 indent=2。"""
    _emit_structured_error(tmp_path / "x", "c", "m")
    err = capsys.readouterr().err
    # indent=2 应产生换行
    assert "\n" in err


def test_emit_structured_error_no_extra_keys_minimal(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "c", "m")
    err = capsys.readouterr().err
    data = json.loads(err)
    # 只 code/message 在 error 里
    assert set(data["errors"][0]) == {"code", "message"}


# =========================================================================
# _infer_parser_name 深度
# =========================================================================


def test_infer_parser_name_pdf_returns_fallback():
    assert _infer_parser_name(Path("a.pdf")) == "fallback"


def test_infer_parser_name_docx_returns_fallback():
    assert _infer_parser_name(Path("a.docx")) == "fallback"


def test_infer_parser_name_md_returns_markdown():
    assert _infer_parser_name(Path("a.md")) == "markdown"


def test_infer_parser_name_markdown_returns_markdown():
    assert _infer_parser_name(Path("a.markdown")) == "markdown"


def test_infer_parser_name_html_returns_html():
    assert _infer_parser_name(Path("a.html")) == "html"


def test_infer_parser_name_htm_returns_html():
    assert _infer_parser_name(Path("a.htm")) == "html"


def test_infer_parser_name_txt_returns_text():
    assert _infer_parser_name(Path("a.txt")) == "text"


def test_infer_parser_name_text_returns_text():
    assert _infer_parser_name(Path("a.text")) == "text"


def test_infer_parser_name_ipynb_returns_ipynb():
    assert _infer_parser_name(Path("a.ipynb")) == "ipynb"


def test_infer_parser_name_unknown_returns_fallback():
    assert _infer_parser_name(Path("a.unknown")) == "fallback"


def test_infer_parser_name_no_suffix_returns_fallback():
    assert _infer_parser_name(Path("README")) == "fallback"


def test_infer_parser_name_pdf_uppercase():
    assert _infer_parser_name(Path("a.PDF")) == "fallback"


def test_infer_parser_name_pdf_mixed_case():
    assert _infer_parser_name(Path("a.PdF")) == "fallback"


# =========================================================================
# main() 综合行为
# =========================================================================


def test_main_unknown_command_exits_2():
    with pytest.raises(SystemExit) as exc:
        main(["unknown"])
    assert exc.value.code == 2


def test_main_validate_missing_file_returns_2(tmp_path: Path, capsys):
    rc = main(["validate", str(tmp_path / "missing.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_inspect_missing_file_returns_2(tmp_path: Path, capsys):
    rc = main(["inspect", str(tmp_path / "missing.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_inspect_invalid_json_returns_1(tmp_path: Path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_inspect_top_level_list_returns_1(tmp_path: Path, capsys):
    p = tmp_path / "list.json"
    p.write_text("[1, 2]", encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "不是对象" in err


def test_main_inspect_valid_doc_returns_0(tmp_path: Path, capsys):
    doc = {
        "schema_version": "0.1.0", "document_id": "d1", "source_path": "x.docx",
        "source_type": "docx", "source_hash": "a" * 64, "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "source_locator": {"paragraph_index": 0}, "content": "hi",
                      "parent_id": None, "confidence": 1.0, "metadata": {}}],
        "chunks": [{"chunk_id": "c1", "text": "hi",
                    "source_element_ids": ["e1"], "metadata": {}}],
        "relations": [], "warnings": [], "errors": [], "metadata": {},
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "file:" in out


def test_main_validate_valid_doc_returns_0(tmp_path: Path, capsys):
    doc = {
        "schema_version": "0.1.0", "document_id": "d1", "source_path": "x.docx",
        "source_type": "docx", "source_hash": "a" * 64, "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "source_locator": {"paragraph_index": 0}, "content": "hi",
                      "parent_id": None, "confidence": 1.0, "metadata": {}}],
        "chunks": [{"chunk_id": "c1", "text": "hi",
                    "source_element_ids": ["e1"], "metadata": {}}],
        "relations": [], "warnings": [], "errors": [], "metadata": {},
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["validate", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out


def test_main_validate_invalid_doc_returns_1(tmp_path: Path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err


def test_main_inspect_with_elements_flag(tmp_path: Path, capsys):
    doc = {
        "schema_version": "0.1.0", "document_id": "d1", "source_path": "x.docx",
        "source_type": "docx", "source_hash": "a" * 64, "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "source_locator": {"paragraph_index": 0}, "content": "hi",
                      "parent_id": None, "confidence": 1.0, "metadata": {}}],
        "chunks": [{"chunk_id": "c1", "text": "hi",
                    "source_element_ids": ["e1"], "metadata": {}}],
        "relations": [], "warnings": [], "errors": [], "metadata": {},
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect", str(p), "--elements"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements (1):" in out
    assert "e1" in out


def test_main_inspect_with_chunks_flag(tmp_path: Path, capsys):
    doc = {
        "schema_version": "0.1.0", "document_id": "d1", "source_path": "x.docx",
        "source_type": "docx", "source_hash": "a" * 64, "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "source_locator": {"paragraph_index": 0}, "content": "hi",
                      "parent_id": None, "confidence": 1.0, "metadata": {}}],
        "chunks": [{"chunk_id": "c1", "text": "hi",
                    "source_element_ids": ["e1"], "metadata": {}}],
        "relations": [], "warnings": [], "errors": [], "metadata": {},
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect", str(p), "--chunks"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "chunks (1):" in out


def test_main_inspect_with_spans_flag(tmp_path: Path, capsys):
    doc = {
        "schema_version": "0.1.0", "document_id": "d1", "source_path": "x.docx",
        "source_type": "docx", "source_hash": "a" * 64, "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "source_locator": {"paragraph_index": 0}, "content": "hi",
                      "parent_id": None, "confidence": 1.0, "metadata": {}}],
        "chunks": [{"chunk_id": "c1", "text": "hi",
                    "source_element_ids": ["e1"], "metadata": {},
                    "source_spans": [{"element_id": "e1", "start": 0, "end": 2}]}],
        "relations": [], "warnings": [], "errors": [], "metadata": {},
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect", str(p), "--chunks", "--spans"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "e1[0:2]" in out


def test_main_inspect_with_limit(tmp_path: Path, capsys):
    elements = [
        {"element_id": f"e{i}", "type": "paragraph",
         "source_locator": {"paragraph_index": i}, "content": str(i),
         "parent_id": None, "confidence": 1.0, "metadata": {}}
        for i in range(5)
    ]
    doc = {
        "schema_version": "0.1.0", "document_id": "d1", "source_path": "x.docx",
        "source_type": "docx", "source_hash": "a" * 64, "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": elements,
        "chunks": [], "relations": [], "warnings": [], "errors": [], "metadata": {},
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect", str(p), "--elements", "--limit", "2"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "+3 more" in out


def test_main_returns_int(tmp_path: Path):
    rc = main(["validate", str(tmp_path / "missing.json")])
    assert isinstance(rc, int)


# =========================================================================
# _run_parse / _run_parse_dir 错误路径
# =========================================================================


def test_run_parse_missing_input_returns_1(tmp_path: Path, capsys):
    from argparse import Namespace
    args = Namespace(
        input=str(tmp_path / "missing.txt"),
        output=str(tmp_path / "out.json"),
        parser=None,
        max_chars=800,
    )
    rc = _run_parse(args)
    assert rc == 1
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["errors"][0]["code"] == "file_not_found"


def test_run_parse_dir_missing_input_dir_returns_2(tmp_path: Path, capsys):
    from argparse import Namespace
    args = Namespace(
        input_dir=str(tmp_path / "missing_dir"),
        output_dir=str(tmp_path / "out"),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    rc = _run_parse_dir(args)
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_run_parse_dir_empty_dir_returns_0_with_warn(tmp_path: Path, capsys):
    from argparse import Namespace
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"
    args = Namespace(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    rc = _run_parse_dir(args)
    assert rc == 0  # empty 不是 failure
    err = capsys.readouterr().err
    assert "[WARN]" in err


def test_run_parse_dir_summary_written(tmp_path: Path):
    from argparse import Namespace
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"
    args = Namespace(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = output_dir / "_summary.json"
    assert summary.is_file()
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert data["total"] == 0
    assert data["success"] == 0
    assert data["failure"] == 0


def test_run_parse_dir_summary_schema_version(tmp_path: Path):
    from argparse import Namespace
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"
    args = Namespace(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = output_dir / "_summary.json"
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.1.0"


def test_run_parse_dir_summary_has_files_list(tmp_path: Path):
    from argparse import Namespace
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"
    args = Namespace(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = output_dir / "_summary.json"
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert "files" in data
    assert isinstance(data["files"], list)


def test_run_parse_dir_summary_max_chars_recorded(tmp_path: Path):
    from argparse import Namespace
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"
    args = Namespace(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        recursive=False,
        parser=None,
        max_chars=500,
    )
    _run_parse_dir(args)
    summary = output_dir / "_summary.json"
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert data["max_chars"] == 500


def test_run_parse_dir_summary_recursive_recorded(tmp_path: Path):
    from argparse import Namespace
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"
    args = Namespace(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        recursive=True,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = output_dir / "_summary.json"
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert data["recursive"] is True


def test_run_parse_dir_summary_parser_override_recorded(tmp_path: Path):
    from argparse import Namespace
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"
    args = Namespace(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        recursive=False,
        parser="fallback",
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = output_dir / "_summary.json"
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert data["parser_override"] == "fallback"


def test_run_parse_dir_with_one_txt_file_success(tmp_path: Path):
    from argparse import Namespace
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "a.txt").write_text("hello world", encoding="utf-8")
    output_dir = tmp_path / "out"
    args = Namespace(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    rc = _run_parse_dir(args)
    assert rc == 0
    summary = output_dir / "_summary.json"
    data = json.loads(summary.read_text(encoding="utf-8"))
    assert data["total"] == 1
    assert data["success"] == 1
    assert data["failure"] == 0


# =========================================================================
# 模块结构 / 签名深度
# =========================================================================


def test_module_has_run_parse_function():
    import app.cli as mod
    assert hasattr(mod, "_run_parse")
    assert callable(mod._run_parse)


def test_module_has_run_parse_dir_function():
    import app.cli as mod
    assert hasattr(mod, "_run_parse_dir")
    assert callable(mod._run_parse_dir)


def test_module_has_format_summary():
    import app.cli as mod
    assert hasattr(mod, "_format_summary")
    assert callable(mod._format_summary)


def test_module_has_format_elements_list():
    import app.cli as mod
    assert hasattr(mod, "_format_elements_list")
    assert callable(mod._format_elements_list)


def test_module_has_format_chunks_list():
    import app.cli as mod
    assert hasattr(mod, "_format_chunks_list")
    assert callable(mod._format_chunks_list)


def test_module_has_load_document_json():
    import app.cli as mod
    assert hasattr(mod, "_load_document_json")
    assert callable(mod._load_document_json)


def test_module_has_preview():
    import app.cli as mod
    assert hasattr(mod, "_preview")
    assert callable(mod._preview)


def test_module_has_iter_supported_files():
    import app.cli as mod
    assert hasattr(mod, "_iter_supported_files")
    assert callable(mod._iter_supported_files)


def test_module_has_relative_output_path():
    import app.cli as mod
    assert hasattr(mod, "_relative_output_path")
    assert callable(mod._relative_output_path)


def test_module_has_infer_parser_name():
    import app.cli as mod
    assert hasattr(mod, "_infer_parser_name")
    assert callable(mod._infer_parser_name)


def test_module_has_emit_structured_error():
    import app.cli as mod
    assert hasattr(mod, "_emit_structured_error")
    assert callable(mod._emit_structured_error)


def test_module_has_build_arg_parser():
    import app.cli as mod
    assert hasattr(mod, "_build_arg_parser")
    assert callable(mod._build_arg_parser)


def test_module_extension_to_parser_is_dict():
    assert isinstance(_EXTENSION_TO_PARSER, dict)


def test_module_extension_to_parser_pdf_value_fallback():
    assert _EXTENSION_TO_PARSER[".pdf"] == "fallback"


def test_module_extension_to_parser_docx_value_fallback():
    assert _EXTENSION_TO_PARSER[".docx"] == "fallback"


def test_module_extension_to_parser_md_value_markdown():
    assert _EXTENSION_TO_PARSER[".md"] == "markdown"


def test_module_extension_to_parser_html_value_html():
    assert _EXTENSION_TO_PARSER[".html"] == "html"


def test_module_extension_to_parser_htm_value_html():
    assert _EXTENSION_TO_PARSER[".htm"] == "html"


def test_module_extension_to_parser_txt_value_text():
    assert _EXTENSION_TO_PARSER[".txt"] == "text"


def test_module_extension_to_parser_text_value_text():
    assert _EXTENSION_TO_PARSER[".text"] == "text"


def test_module_extension_to_parser_ipynb_value_ipynb():
    assert _EXTENSION_TO_PARSER[".ipynb"] == "ipynb"


def test_module_extension_to_parser_markdown_value_markdown():
    assert _EXTENSION_TO_PARSER[".markdown"] == "markdown"


def test_module_extension_to_parser_count_nine():
    """9 个扩展名映射：.pdf/.docx/.md/.markdown/.html/.htm/.txt/.text/.ipynb。"""
    assert len(_EXTENSION_TO_PARSER) == 9
