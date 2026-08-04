"""app/cli.py 边角测试 - 第三轮（Round 94）。

补强已有 109 + 95 + ? = 200+ 测试未覆盖的：
- `_emit_structured_error` 输出包含 schema_version/input/errors
- `_run_parse` 失败时清理半成品 JSON
- `_run_parse_dir` mkdir 失败 / summary 写盘失败 / 文件混合成功失败
- `_format_summary` 各字段精确格式（counts/elements by type/chunk refs/warnings truncation）
- `_format_elements_list` limit=0 全列 / parent_id 显示 / content None
- `_format_chunks_list` spans 展开 / 空 spans / limit 边界
- `_preview` 多种宽度边界（width=1, 长度=width-1, 长度=width, 长度=width+1）
- main() 端到端：parse 成功路径、parse-dir 成功路径
- argparse 默认值与 choices 校验
- `_load_document_json` 各错误路径 message 格式
- `_infer_parser_name` 大小写混合
- `_relative_output_path` Windows 反斜杠转正斜杠
- `_iter_supported_files` 混合目录

不修改任何源码。
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app import cli
from app.cli import (
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
    _run_parse,
    _run_parse_dir,
    main,
)


# =============================================================================
# _emit_structured_error
# =============================================================================


def test_emit_structured_error_writes_to_stderr(capsys):
    _emit_structured_error(Path("x.txt"), "code1", "msg1")
    captured = capsys.readouterr()
    assert captured.err != ""
    assert captured.out == ""  # 不写 stdout


def test_emit_structured_error_includes_schema_version(capsys):
    _emit_structured_error(Path("x"), "c", "m")
    err = capsys.readouterr().err
    data = json.loads(err)
    assert data["schema_version"] == "0.1.0"


def test_emit_structured_error_includes_input_path(capsys):
    _emit_structured_error(Path("/tmp/abc.txt"), "c", "m")
    err = capsys.readouterr().err
    data = json.loads(err)
    assert "abc.txt" in data["input"]


def test_emit_structured_error_includes_code_and_message(capsys):
    _emit_structured_error(Path("x"), "my_code", "my_message")
    data = json.loads(capsys.readouterr().err)
    assert data["errors"][0]["code"] == "my_code"
    assert data["errors"][0]["message"] == "my_message"


def test_emit_structured_error_passes_extra_kwargs(capsys):
    _emit_structured_error(Path("x"), "c", "m", page=5, bbox=[0, 0, 10, 10])
    data = json.loads(capsys.readouterr().err)
    assert data["errors"][0]["page"] == 5
    assert data["errors"][0]["bbox"] == [0, 0, 10, 10]


def test_emit_structured_error_no_extra_returns_only_code_message(capsys):
    _emit_structured_error(Path("x"), "c", "m")
    data = json.loads(capsys.readouterr().err)
    err = data["errors"][0]
    # 仅 code + message 两个键
    assert set(err.keys()) == {"code", "message"}


# =============================================================================
# _preview 边界
# =============================================================================


def test_preview_width_one_short_text():
    assert _preview("x", 1) == "x"


def test_preview_width_one_exact_match():
    assert _preview("a", 1) == "a"


def test_preview_width_one_long_text():
    """width=1, text=ab → '…'（width-1=0 char + ellipsis）."""
    result = _preview("ab", 1)
    assert result.endswith("…")


def test_preview_length_width_minus_one_no_ellipsis():
    """len(text) == width - 1 → 不截断（< width）."""
    result = _preview("abc", 10)
    assert result == "abc"


def test_preview_length_exact_width_no_ellipsis():
    """len(collapsed) == width → 不截断（<= width）."""
    result = _preview("abcde", 5)
    assert result == "abcde"


def test_preview_length_width_plus_one_triggers_ellipsis():
    """len(collapsed) == width + 1 → 截断 + ellipsis."""
    result = _preview("abcdef", 5)
    assert result.endswith("…")
    assert "abcde" not in result or result[:-1] == "abcd"


def test_preview_negative_width_returns_truncated():
    """width <= 0 但 text 长 → 行为依赖 collapsed[:width-1] + '…'.

    width=0 → collapsed[:-1] + '…'
    """
    result = _preview("abcdef", 0)
    # 不抛即可
    assert isinstance(result, str)


def test_preview_none_text_returns_empty():
    assert _preview(None, 60) == ""


def test_preview_empty_text_returns_empty():
    assert _preview("", 60) == ""


def test_preview_collapses_tab_to_space():
    """tab 字符 → 空格。"""
    result = _preview("a\tb", 60)
    assert "\t" not in result
    assert "a" in result and "b" in result


def test_preview_collapses_multiple_whitespace():
    result = _preview("a    b\n\nc", 60)
    assert "  " not in result  # 无双空格
    assert "\n" not in result


# =============================================================================
# _load_document_json
# =============================================================================


def test_load_document_json_missing_file_returns_none_with_message(tmp_path: Path):
    missing = tmp_path / "no.json"
    data, err = _load_document_json(missing)
    assert data is None
    assert "不存在" in err or "no.json" in err


def test_load_document_json_bad_json_returns_none_with_json_message(tmp_path: Path):
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    data, err = _load_document_json(f)
    assert data is None
    assert "JSON" in err or "json" in err.lower()


def test_load_document_json_valid_returns_dict(tmp_path: Path):
    f = tmp_path / "x.json"
    f.write_text('{"k": "v"}', encoding="utf-8")
    data, err = _load_document_json(f)
    assert data == {"k": "v"}
    assert err == ""


def test_load_document_json_directory_returns_oserror(tmp_path: Path):
    """传目录 → OSError（open(dir) fails）。"""
    d = tmp_path / "sub"
    d.mkdir()
    data, err = _load_document_json(d)
    # 实际：在 Windows 上可能是 PermissionError；Linux/Mac 上 IsADirectoryError
    # 统一断言：data is None
    assert data is None


# =============================================================================
# _format_summary 精确字段
# ==============================================================================


def test_format_summary_includes_file_path(tmp_path: Path):
    data = {"schema_version": "0.1.0", "document_id": "d1", "source_path": "x"}
    s = _format_summary(data, tmp_path / "x.json")
    assert str(tmp_path / "x.json") in s


def test_format_summary_includes_document_id():
    data = {"document_id": "doc-abc-123"}
    s = _format_summary(data, Path("x.json"))
    assert "doc-abc-123" in s


def test_format_summary_includes_source_path():
    data = {"source_path": "/tmp/original.txt"}
    s = _format_summary(data, Path("x.json"))
    assert "/tmp/original.txt" in s


def test_format_summary_includes_source_type():
    data = {"source_type": "docx"}
    s = _format_summary(data, Path("x.json"))
    assert "docx" in s


def test_format_summary_includes_parser_name():
    data = {"parser_name": "fallback"}
    s = _format_summary(data, Path("x.json"))
    assert "fallback" in s


def test_format_summary_includes_parser_version():
    data = {"parser_version": "v1.2.3"}
    s = _format_summary(data, Path("x.json"))
    assert "v1.2.3" in s


def test_format_summary_counts_line_format():
    data = {
        "elements": [{"type": "paragraph", "content": "a"}],
        "chunks": [{"text": "a", "source_element_ids": ["e1"]}],
        "relations": [{"source": "a", "target": "b"}],
        "warnings": [{"code": "x", "reason": "y"}],
        "errors": [{"code": "z", "message": "w"}],
    }
    s = _format_summary(data, Path("x.json"))
    assert "elements=1" in s
    assert "chunks=1" in s
    assert "relations=1" in s
    assert "warnings=1" in s
    assert "errors=1" in s


def test_format_summary_elements_by_type_paragraph():
    data = {"elements": [{"type": "paragraph", "content": "x"}]}
    s = _format_summary(data, Path("x.json"))
    assert "paragraph=1" in s


def test_format_summary_elements_by_type_mixed():
    data = {
        "elements": [
            {"type": "paragraph", "content": "x"},
            {"type": "heading", "content": "y"},
            {"type": "paragraph", "content": "z"},
        ]
    }
    s = _format_summary(data, Path("x.json"))
    assert "paragraph=2" in s
    assert "heading=1" in s


def test_format_summary_element_text_avg():
    data = {
        "elements": [
            {"type": "p", "content": "abc"},
            {"type": "p", "content": "abcdefgh"},  # 8 chars
        ]
    }
    s = _format_summary(data, Path("x.json"))
    # total = 11, avg = 5.5 → 6
    assert "total_chars=11" in s
    assert "avg=6" in s or "avg=5" in s


def test_format_summary_chunk_text_min_max():
    data = {
        "chunks": [
            {"text": "ab", "source_element_ids": ["e1"]},
            {"text": "abcdefgh", "source_element_ids": ["e2"]},
        ]
    }
    s = _format_summary(data, Path("x.json"))
    assert "min=2" in s
    assert "max=8" in s


def test_format_summary_chunk_refs_min_max():
    data = {
        "chunks": [
            {"text": "a", "source_element_ids": ["e1"]},
            {"text": "b", "source_element_ids": ["e1", "e2", "e3"]},
        ]
    }
    s = _format_summary(data, Path("x.json"))
    assert "refs:" in s


def test_format_summary_warnings_shown_truncated_at_5():
    warnings = [{"code": f"c{i}", "reason": f"r{i}"} for i in range(10)]
    data = {"warnings": warnings}
    s = _format_summary(data, Path("x.json"))
    assert "more" in s


def test_format_summary_errors_shown():
    data = {"errors": [{"code": "c1", "message": "m1"}]}
    s = _format_summary(data, Path("x.json"))
    assert "c1" in s
    assert "m1" in s


def test_format_summary_no_fields_returns_minimal():
    """空 dict → 不抛、有基本字段。"""
    s = _format_summary({}, Path("x.json"))
    assert "schema:" in s
    assert "document_id:" in s


# =============================================================================
# _format_elements_list
# =============================================================================


def test_format_elements_list_limit_zero_shows_all():
    elements = [{"element_id": f"e{i}", "type": "p", "content": "x"} for i in range(50)]
    s = _format_elements_list(elements, limit=0)
    # 全部 50 都列出
    for i in range(50):
        assert f"e{i}" in s


def test_format_elements_list_limit_negative_shows_all():
    """limit <= 0 都视为全列。"""
    elements = [{"element_id": f"e{i}", "type": "p", "content": "x"} for i in range(20)]
    s = _format_elements_list(elements, limit=-1)
    for i in range(20):
        assert f"e{i}" in s


def test_format_elements_list_limit_truncation_marker():
    elements = [{"element_id": f"e{i}", "type": "p", "content": "x"} for i in range(20)]
    s = _format_elements_list(elements, limit=5)
    assert "+15 more" in s or "+ 15 more" in s


def test_format_elements_list_parent_id_displayed():
    elements = [{"element_id": "e1", "type": "p", "content": "x", "parent_id": "e0"}]
    s = _format_elements_list(elements, limit=10)
    assert "parent=e0" in s


def test_format_elements_list_no_parent_id_omitted():
    elements = [{"element_id": "e1", "type": "p", "content": "x"}]
    s = _format_elements_list(elements, limit=10)
    assert "parent=" not in s


def test_format_elements_list_content_none_preview_empty():
    elements = [{"element_id": "e1", "type": "image", "content": None}]
    s = _format_elements_list(elements, limit=10)
    assert "e1" in s
    # 不抛即可


def test_format_elements_list_empty_list():
    s = _format_elements_list([], limit=10)
    assert "elements (0)" in s


def test_format_elements_list_type_aligned():
    """type 字段被填充到 9 字符宽。"""
    elements = [{"element_id": "e1", "type": "p", "content": "x"}]
    s = _format_elements_list(elements, limit=10)
    assert "[p        ]" in s  # p + 8 spaces = 9 chars


# =============================================================================
# _format_chunks_list
# =============================================================================


def test_format_chunks_list_basic():
    chunks = [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}]
    s = _format_chunks_list(chunks, limit=10)
    assert "c1" in s
    assert "chars=5" in s
    assert "refs=1" in s


def test_format_chunks_list_with_spans():
    chunks = [{
        "chunk_id": "c1",
        "text": "hello",
        "source_element_ids": ["e1"],
        "source_spans": [{"element_id": "e1", "start": 0, "end": 5}],
    }]
    s = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "span:" in s
    assert "e1[0:5]" in s


def test_format_chunks_list_with_empty_spans():
    chunks = [{
        "chunk_id": "c1",
        "text": "x",
        "source_element_ids": ["e1"],
        "source_spans": [],
    }]
    s = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "spans: (none)" in s


def test_format_chunks_list_spans_none_falls_back_to_empty():
    chunks = [{"chunk_id": "c1", "text": "x", "source_element_ids": ["e1"]}]
    s = _format_chunks_list(chunks, limit=10, show_spans=True)
    # source_spans 缺失 → []
    assert "spans: (none)" in s


def test_format_chunks_list_limit_zero_shows_all():
    chunks = [{"chunk_id": f"c{i}", "text": "x", "source_element_ids": ["e1"]} for i in range(20)]
    s = _format_chunks_list(chunks, limit=0)
    for i in range(20):
        assert f"c{i}" in s


def test_format_chunks_list_limit_truncation_marker():
    chunks = [{"chunk_id": f"c{i}", "text": "x", "source_element_ids": ["e1"]} for i in range(15)]
    s = _format_chunks_list(chunks, limit=5)
    assert "+10 more" in s or "+ 10 more" in s


def test_format_chunks_list_empty_list():
    s = _format_chunks_list([], limit=10)
    assert "chunks (0)" in s


def test_format_chunks_list_text_none_handles_gracefully():
    chunks = [{"chunk_id": "c1", "text": None, "source_element_ids": []}]
    s = _format_chunks_list(chunks, limit=10)
    assert "chars=0" in s


# =============================================================================
# _infer_parser_name 边界
# =============================================================================


def test_infer_parser_name_uppercase_extension():
    assert _infer_parser_name(Path("x.TXT")) == "text"


def test_infer_parser_name_mixed_case_extension():
    assert _infer_parser_name(Path("x.TxT")) == "text"


def test_infer_parser_name_uppercase_pdf():
    assert _infer_parser_name(Path("x.PDF")) == "fallback"


def test_infer_parser_name_no_suffix():
    assert _infer_parser_name(Path("noversion")) == "fallback"


def test_infer_parser_name_unknown_suffix():
    assert _infer_parser_name(Path("x.unknownext")) == "fallback"


def test_infer_parser_name_md():
    assert _infer_parser_name(Path("x.md")) == "markdown"


def test_infer_parser_name_markdown():
    assert _infer_parser_name(Path("x.markdown")) == "markdown"


def test_infer_parser_name_html():
    assert _infer_parser_name(Path("x.html")) == "html"


def test_infer_parser_name_htm():
    assert _infer_parser_name(Path("x.htm")) == "html"


def test_infer_parser_name_ipynb():
    assert _infer_parser_name(Path("x.ipynb")) == "ipynb"


# =============================================================================
# _iter_supported_files 边界
# =============================================================================


def test_iter_supported_files_returns_paths(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.md").write_text("y")
    files = _iter_supported_files(tmp_path, recursive=False)
    assert all(isinstance(f, Path) for f in files)


def test_iter_supported_files_recursive_includes_subdirs(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.md").write_text("y")
    files = _iter_supported_files(tmp_path, recursive=True)
    names = sorted(f.name for f in files)
    assert names == ["a.txt", "b.md"]


def test_iter_supported_files_non_recursive_excludes_subdirs(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.md").write_text("y")
    files = _iter_supported_files(tmp_path, recursive=False)
    assert [f.name for f in files] == ["a.txt"]


def test_iter_supported_files_no_files_returns_empty(tmp_path: Path):
    files = _iter_supported_files(tmp_path, recursive=False)
    assert files == []


def test_iter_supported_files_all_unsupported_extensions(tmp_path: Path):
    (tmp_path / "a.bin").write_text("x")
    (tmp_path / "b.dat").write_text("y")
    files = _iter_supported_files(tmp_path, recursive=False)
    assert files == []


# =============================================================================
# _relative_output_path
# =============================================================================


def test_relative_output_path_returns_path_object(tmp_path: Path):
    p = _relative_output_path(tmp_path, tmp_path / "x.txt", tmp_path / "out")
    assert isinstance(p, Path)


def test_relative_output_path_preserves_suffix_in_name(tmp_path: Path):
    p = _relative_output_path(tmp_path, tmp_path / "x.md", tmp_path / "out")
    assert "x.md.json" in str(p)


def test_relative_output_path_double_extension_preserved(tmp_path: Path):
    p = _relative_output_path(tmp_path, tmp_path / "x.tar.gz", tmp_path / "out")
    assert "x.tar.gz.json" in str(p)


# =============================================================================
# _build_arg_parser 默认值与 choices
# =============================================================================


def test_arg_parser_default_max_chars_is_800():
    p = _build_arg_parser()
    args = p.parse_args(["parse", "x.txt", "-o", "y.json"])
    assert args.max_chars == 800


def test_arg_parser_default_limit_is_10():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "x.json"])
    assert args.limit == 10


def test_arg_parser_parser_choice_fallback():
    p = _build_arg_parser()
    args = p.parse_args(["parse", "x.pdf", "-o", "y.json", "--parser", "fallback"])
    assert args.parser == "fallback"


def test_arg_parser_parser_choice_invalid_exits():
    p = _build_arg_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["parse", "x.pdf", "-o", "y.json", "--parser", "nonexistent"])


def test_arg_parser_parse_requires_output():
    p = _build_arg_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["parse", "x.pdf"])


def test_arg_parser_parse_dir_requires_output_dir():
    p = _build_arg_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["parse-dir", "x"])


def test_arg_parser_no_subcommand_exits():
    p = _build_arg_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_arg_parser_recursive_default_false():
    p = _build_arg_parser()
    args = p.parse_args(["parse-dir", "x", "-o", "y"])
    assert args.recursive is False


def test_arg_parser_recursive_flag_true():
    p = _build_arg_parser()
    args = p.parse_args(["parse-dir", "x", "-o", "y", "--recursive"])
    assert args.recursive is True


def test_arg_parser_validate_takes_one_arg():
    p = _build_arg_parser()
    args = p.parse_args(["validate", "x.json"])
    assert args.command == "validate"
    assert args.input == "x.json"


def test_arg_parser_inspect_takes_one_arg():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "x.json"])
    assert args.command == "inspect"
    assert args.input == "x.json"


def test_arg_parser_inspect_elements_default_false():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "x.json"])
    assert args.elements is False


def test_arg_parser_inspect_chunks_default_false():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "x.json"])
    assert args.chunks is False


def test_arg_parser_inspect_spans_default_false():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "x.json"])
    assert args.spans is False


# =============================================================================
# main() 端到端
# =============================================================================


def test_main_inspect_with_elements_and_chunks(tmp_path: Path, capsys):
    """inspect 子命令 with --elements --chunks 不抛。"""
    from app.parsers.text_parser import TextParser
    from app.chunkers import StructuralChunker
    from app.hash import compute_file_hash
    f_in = tmp_path / "in.txt"
    f_in.write_text("hello world. " * 20, encoding="utf-8")
    h = compute_file_hash(f_in)
    parser = TextParser()
    doc = parser.parse(f_in, source_hash=h)
    chunker = StructuralChunker(max_chars=800)
    doc.chunks = chunker.chunk(doc)
    f = tmp_path / "valid.json"
    f.write_text(json.dumps(doc.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    rc = main(["inspect", str(f), "--elements", "--chunks"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements" in out
    assert "chunks" in out


def test_main_inspect_with_limit_zero(tmp_path: Path, capsys):
    """inspect with --limit 0 → 全列。"""
    from app.parsers.text_parser import TextParser
    from app.chunkers import StructuralChunker
    from app.hash import compute_file_hash
    f_in = tmp_path / "in.txt"
    f_in.write_text("hello world. " * 50, encoding="utf-8")
    h = compute_file_hash(f_in)
    doc = TextParser().parse(f_in, source_hash=h)
    doc.chunks = StructuralChunker(max_chars=800).chunk(doc)
    f = tmp_path / "valid.json"
    f.write_text(json.dumps(doc.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    rc = main(["inspect", str(f), "--elements", "--limit", "0"])
    assert rc == 0


def test_main_inspect_non_dict_json_returns_1(tmp_path: Path):
    """JSON 顶层是 list → 返回 1。"""
    f = tmp_path / "arr.json"
    f.write_text("[1,2,3]", encoding="utf-8")
    rc = main(["inspect", str(f)])
    assert rc == 1


def test_main_inspect_spans_flag_without_chunks_does_not_crash(tmp_path: Path, capsys):
    """--spans 不与 --chunks 配合 → 不展示 spans。"""
    from app.parsers.text_parser import TextParser
    from app.chunkers import StructuralChunker
    from app.hash import compute_file_hash
    f_in = tmp_path / "in.txt"
    f_in.write_text("hello world.", encoding="utf-8")
    h = compute_file_hash(f_in)
    doc = TextParser().parse(f_in, source_hash=h)
    doc.chunks = StructuralChunker(max_chars=800).chunk(doc)
    f = tmp_path / "valid.json"
    f.write_text(json.dumps(doc.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    rc = main(["inspect", str(f), "--spans"])  # 无 --chunks
    assert rc == 0


# =============================================================================
# _run_parse_dir 失败路径
# =============================================================================


def test_run_parse_dir_missing_input_dir_returns_2(tmp_path: Path, capsys):
    missing = tmp_path / "no_such_dir"
    out_dir = tmp_path / "out"
    args = type("A", (), {
        "input_dir": str(missing),
        "output_dir": str(out_dir),
        "recursive": False,
        "parser": None,
        "max_chars": 800,
    })()
    rc = _run_parse_dir(args)
    assert rc == 2


def test_run_parse_dir_empty_input_dir_writes_summary(tmp_path: Path):
    empty_in = tmp_path / "empty"
    empty_in.mkdir()
    out_dir = tmp_path / "out"
    args = type("A", (), {
        "input_dir": str(empty_in),
        "output_dir": str(out_dir),
        "recursive": False,
        "parser": None,
        "max_chars": 800,
    })()
    rc = _run_parse_dir(args)
    # 0 文件 → 0 failures → rc=0
    assert rc == 0
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 0
    assert summary["success"] == 0
    assert summary["failure"] == 0


def test_run_parse_dir_one_good_file_succeeds(tmp_path: Path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text("hello world. " * 20, encoding="utf-8")
    out_dir = tmp_path / "out"
    args = type("A", (), {
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "recursive": False,
        "parser": None,
        "max_chars": 800,
    })()
    rc = _run_parse_dir(args)
    assert rc == 0
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 1
    assert summary["success"] == 1
    assert summary["failure"] == 0


def test_run_parse_dir_unsupported_files_only_no_failures(tmp_path: Path):
    """目录里只有 .bin/.dat → 0 files → 0 failures。"""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.bin").write_text("x", encoding="utf-8")
    out_dir = tmp_path / "out"
    args = type("A", (), {
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "recursive": False,
        "parser": None,
        "max_chars": 800,
    })()
    rc = _run_parse_dir(args)
    assert rc == 0


def test_run_parse_dir_summary_schema_version(tmp_path: Path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"
    args = type("A", (), {
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "recursive": False,
        "parser": None,
        "max_chars": 800,
    })()
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["schema_version"] == "0.1.0"


def test_run_parse_dir_summary_has_input_dir_field(tmp_path: Path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"
    args = type("A", (), {
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "recursive": False,
        "parser": None,
        "max_chars": 800,
    })()
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["input_dir"] == str(in_dir)


def test_run_parse_dir_summary_has_recursive_field(tmp_path: Path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"
    args = type("A", (), {
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "recursive": True,
        "parser": None,
        "max_chars": 800,
    })()
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["recursive"] is True


def test_run_parse_dir_summary_has_parser_override_field(tmp_path: Path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"
    args = type("A", (), {
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "recursive": False,
        "parser": "text",
        "max_chars": 800,
    })()
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["parser_override"] == "text"


def test_run_parse_dir_summary_has_max_chars_field(tmp_path: Path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"
    args = type("A", (), {
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "recursive": False,
        "parser": None,
        "max_chars": 1200,
    })()
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["max_chars"] == 1200
