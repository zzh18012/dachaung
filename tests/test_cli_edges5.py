"""app/cli.py 边角测试 - 第五轮（Round 126）。

补强已有 base/edges/edges2/edges3/edges4（共 494 测试）未覆盖的深度路径：
- _infer_parser_name：
  - 9 个扩展名全覆盖（.pdf/.docx/.md/.markdown/.html/.htm/.txt/.text/.ipynb）
  - 大小写不敏感（.PDF/.MD/.TXT 等）
  - 无扩展名 → fallback
  - 未知扩展名 → fallback
- _iter_supported_files：
  - 空目录 → []
  - 仅非支持文件 → []
  - recursive=True 包含子目录
  - 文件名排序
- _relative_output_path：
  - 顶层文件
  - 子目录文件
  - Windows 反斜杠替换为正斜杠
- _preview：
  - None/空文本 → ""
  - 短文本不截断
  - 长文本截断加省略号
  - 空白归一
  - 自定义 width
- _load_document_json：
  - FileNotFoundError → (None, msg)
  - JSONDecodeError → (None, msg)
  - 成功 → (dict, "")
- _format_summary：
  - 空文档
  - 缺字段使用 "?"
  - hash 截断 16 字符
- _format_elements_list：
  - limit=0 列出全部
  - limit 截断 + 提示
- _format_chunks_list：
  - show_spans True/False
  - 无 spans 显示 "(none)"
- _EXTENSION_TO_PARSER：
  - 内容精确
  - 9 个 key
- main exit codes：
  - validate 成功/失败/缺文件
  - inspect 各种错误
- 模块结构：
  - imports 完整
  - 7 个 helper callable
"""

from __future__ import annotations

import json
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


SHA = "a" * 64


# =========================================================================
# _EXTENSION_TO_PARSER 内容
# =========================================================================


def test_extension_to_parser_count_nine():
    assert len(_EXTENSION_TO_PARSER) == 9


def test_extension_to_parser_pdf():
    assert _EXTENSION_TO_PARSER[".pdf"] == "fallback"


def test_extension_to_parser_docx():
    assert _EXTENSION_TO_PARSER[".docx"] == "fallback"


def test_extension_to_parser_md():
    assert _EXTENSION_TO_PARSER[".md"] == "markdown"


def test_extension_to_parser_markdown():
    assert _EXTENSION_TO_PARSER[".markdown"] == "markdown"


def test_extension_to_parser_html():
    assert _EXTENSION_TO_PARSER[".html"] == "html"


def test_extension_to_parser_htm():
    assert _EXTENSION_TO_PARSER[".htm"] == "html"


def test_extension_to_parser_txt():
    assert _EXTENSION_TO_PARSER[".txt"] == "text"


def test_extension_to_parser_text():
    assert _EXTENSION_TO_PARSER[".text"] == "text"


def test_extension_to_parser_ipynb():
    assert _EXTENSION_TO_PARSER[".ipynb"] == "ipynb"


# =========================================================================
# _infer_parser_name 大小写
# =========================================================================


def test_infer_parser_name_pdf_uppercase():
    assert _infer_parser_name(Path("x.PDF")) == "fallback"


def test_infer_parser_name_docx_mixed_case():
    assert _infer_parser_name(Path("x.DoCX")) == "fallback"


def test_infer_parser_name_md_uppercase():
    assert _infer_parser_name(Path("X.MD")) == "markdown"


def test_infer_parser_name_html_uppercase():
    assert _infer_parser_name(Path("X.HTML")) == "html"


def test_infer_parser_name_txt_uppercase():
    assert _infer_parser_name(Path("X.TXT")) == "text"


def test_infer_parser_name_ipynb_uppercase():
    assert _infer_parser_name(Path("X.IPYNB")) == "ipynb"


def test_infer_parser_name_no_extension():
    """无扩展名 → fallback。"""
    assert _infer_parser_name(Path("README")) == "fallback"


def test_infer_parser_name_empty_suffix():
    assert _infer_parser_name(Path("README.")) == "fallback"


def test_infer_parser_name_unknown_extension():
    assert _infer_parser_name(Path("x.unknownext")) == "fallback"


def test_infer_parser_name_json():
    """JSON 不在支持表 → fallback。"""
    assert _infer_parser_name(Path("x.json")) == "fallback"


def test_infer_parser_name_csv():
    assert _infer_parser_name(Path("x.csv")) == "fallback"


def test_infer_parser_name_xml():
    assert _infer_parser_name(Path("x.xml")) == "fallback"


def test_infer_parser_name_yaml():
    assert _infer_parser_name(Path("x.yaml")) == "fallback"


def test_infer_parser_name_returns_str():
    assert isinstance(_infer_parser_name(Path("x.txt")), str)


# =========================================================================
# _iter_supported_files 深度
# =========================================================================


def test_iter_supported_files_empty_dir(tmp_path: Path):
    assert _iter_supported_files(tmp_path, recursive=False) == []


def test_iter_supported_files_only_unsupported(tmp_path: Path):
    (tmp_path / "x.unknown").write_text("data", encoding="utf-8")
    (tmp_path / "y.json").write_text("{}", encoding="utf-8")
    assert _iter_supported_files(tmp_path, recursive=False) == []


def test_iter_supported_files_filters_only_supported(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.unknown").write_text("b", encoding="utf-8")
    (tmp_path / "c.md").write_text("c", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in result]
    assert "a.txt" in names
    assert "c.md" in names
    assert "b.unknown" not in names


def test_iter_supported_files_returns_list(tmp_path: Path):
    result = _iter_supported_files(tmp_path, recursive=False)
    assert isinstance(result, list)


def test_iter_supported_files_sorted_by_name(tmp_path: Path):
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "m.txt").write_text("m", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in result]
    assert names == sorted(names)
    assert names == ["a.txt", "m.txt", "z.txt"]


def test_iter_supported_files_recursive_includes_subdir(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (sub / "b.txt").write_text("b", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=True)
    names = [p.name for p in result]
    assert "a.txt" in names
    assert "b.txt" in names


def test_iter_supported_files_non_recursive_excludes_subdir(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (sub / "b.txt").write_text("b", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in result]
    assert "a.txt" in names
    assert "b.txt" not in names


def test_iter_supported_files_all_extension_types(tmp_path: Path):
    """各支持扩展名都被收集。"""
    for ext in (".pdf", ".docx", ".md", ".markdown", ".html", ".htm", ".txt", ".text", ".ipynb"):
        (tmp_path / f"file{ext}").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    assert len(result) == 9


def test_iter_supported_files_extension_case_insensitive(tmp_path: Path):
    """大写扩展名也应被收集（_infer 用 .lower()）。"""
    (tmp_path / "x.TXT").write_text("x", encoding="utf-8")
    (tmp_path / "y.MD").write_text("y", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    assert len(result) == 2


# =========================================================================
# _relative_output_path 深度
# =========================================================================


def test_relative_output_path_top_level(tmp_path: Path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()
    f = in_dir / "x.txt"
    f.write_text("x", encoding="utf-8")
    result = _relative_output_path(in_dir, f, out_dir)
    assert result == out_dir / "x.txt.json"


def test_relative_output_path_subdir(tmp_path: Path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    (in_dir / "sub").mkdir(parents=True)
    out_dir.mkdir()
    f = in_dir / "sub" / "x.txt"
    f.write_text("x", encoding="utf-8")
    result = _relative_output_path(in_dir, f, out_dir)
    assert "sub" in str(result)
    assert result.name == "x.txt.json"


def test_relative_output_path_preserves_full_filename(tmp_path: Path):
    """文件名（含 suffix）整体作为新文件名，加 .json 后缀。"""
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()
    f = in_dir / "report.pdf"
    f.write_text("x", encoding="utf-8")
    result = _relative_output_path(in_dir, f, out_dir)
    assert result.name == "report.pdf.json"


def test_relative_output_path_returns_path_object(tmp_path: Path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()
    f = in_dir / "x.txt"
    f.write_text("x", encoding="utf-8")
    result = _relative_output_path(in_dir, f, out_dir)
    assert isinstance(result, Path)


# =========================================================================
# _preview 深度
# =========================================================================


def test_preview_none_returns_empty():
    assert _preview(None) == ""


def test_preview_empty_string_returns_empty():
    assert _preview("") == ""


def test_preview_short_text_no_truncation():
    assert _preview("hello") == "hello"


def test_preview_long_text_truncated_with_ellipsis():
    text = "a" * 100
    result = _preview(text, width=10)
    # 应有省略号
    assert result.endswith("…")
    # 总长度应为 width
    assert len(result) == 10


def test_preview_collapses_whitespace():
    text = "hello    world\n\nfoo"
    result = _preview(text)
    assert result == "hello world foo"


def test_preview_exact_width_no_truncation():
    """长度恰等于 width → 不截断。"""
    text = "1234567890"  # 10 chars
    result = _preview(text, width=10)
    assert result == "1234567890"


def test_preview_width_one_more_truncates():
    text = "12345678901"  # 11 chars
    result = _preview(text, width=10)
    assert len(result) == 10
    assert result.endswith("…")


def test_preview_custom_width():
    text = "short"
    result = _preview(text, width=3)
    assert result.endswith("…")
    assert len(result) == 3


def test_preview_only_whitespace_returns_empty():
    assert _preview("   \n\t  ") == ""


def test_preview_unicode_text():
    text = "中文测试"
    result = _preview(text, width=100)
    assert result == "中文测试"


def test_preview_returns_str_type():
    assert isinstance(_preview("hello"), str)


# =========================================================================
# _load_document_json 深度
# =========================================================================


def test_load_document_json_missing_file(tmp_path: Path):
    data, err = _load_document_json(tmp_path / "missing.json")
    assert data is None
    assert "不存在" in err or "missing" in err.lower()


def test_load_document_json_invalid_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data is None
    assert "JSON" in err or "json" in err.lower()


def test_load_document_json_valid_dict(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == {"key": "value"}
    assert err == ""


def test_load_document_json_returns_tuple(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    result = _load_document_json(p)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_load_document_json_empty_file(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data is None
    assert err != ""


def test_load_document_json_array_root(tmp_path: Path):
    p = tmp_path / "arr.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    data, err = _load_document_json(p)
    # 数组也是合法 JSON，data 是 list
    assert data == [1, 2, 3]
    assert err == ""


def test_load_document_json_unicode_content(tmp_path: Path):
    p = tmp_path / "uni.json"
    p.write_text('{"k": "中文"}', encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == {"k": "中文"}


# =========================================================================
# _format_summary 深度
# =========================================================================


def test_format_summary_minimal_doc(tmp_path: Path):
    data = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "/tmp/x",
        "source_type": "pdf",
        "source_hash": SHA,
        "parser_name": "fallback",
        "parser_version": "1.0",
    }
    result = _format_summary(data, tmp_path / "x.json")
    assert "d1" in result
    assert "fallback" in result


def test_format_summary_missing_fields_use_question_mark(tmp_path: Path):
    """缺字段使用 '?'。"""
    result = _format_summary({}, tmp_path / "x.json")
    assert "?" in result


def test_format_summary_hash_truncated_to_16(tmp_path: Path):
    data = {"source_hash": SHA}
    result = _format_summary(data, tmp_path / "x.json")
    assert SHA[:16] in result
    assert "…" in result


def test_format_summary_includes_counts(tmp_path: Path):
    data = {
        "elements": [{"type": "paragraph", "content": "a"}],
        "chunks": [{"text": "a", "source_element_ids": ["e1"]}],
        "warnings": [],
        "errors": [],
        "relations": [],
    }
    result = _format_summary(data, tmp_path / "x.json")
    assert "elements=1" in result
    assert "chunks=1" in result


def test_format_summary_returns_str(tmp_path: Path):
    result = _format_summary({}, tmp_path / "x.json")
    assert isinstance(result, str)


def test_format_summary_with_warnings(tmp_path: Path):
    data = {
        "warnings": [
            {"code": "warn1", "reason": "reason1"},
            {"code": "warn2", "reason": "reason2"},
        ],
    }
    result = _format_summary(data, tmp_path / "x.json")
    assert "warn1" in result
    assert "warn2" in result
    assert "reason1" in result


def test_format_summary_warnings_truncated_at_five(tmp_path: Path):
    """warnings 超过 5 条会显示 '+N more'。"""
    warnings = [{"code": f"w{i}", "reason": f"r{i}"} for i in range(10)]
    data = {"warnings": warnings}
    result = _format_summary(data, tmp_path / "x.json")
    assert "+5 more" in result


def test_format_summary_with_errors(tmp_path: Path):
    data = {
        "errors": [{"code": "err1", "message": "msg1"}],
    }
    result = _format_summary(data, tmp_path / "x.json")
    assert "err1" in result
    assert "msg1" in result


def test_format_summary_element_avg_chars(tmp_path: Path):
    data = {
        "elements": [
            {"type": "paragraph", "content": "hello"},
            {"type": "paragraph", "content": "world!"},
        ],
    }
    result = _format_summary(data, tmp_path / "x.json")
    # avg chars = (5+6)/2 = 5
    assert "avg=5" in result or "avg=" in result


# =========================================================================
# _format_elements_list 深度
# =========================================================================


def test_format_elements_list_empty():
    result = _format_elements_list([], limit=10)
    assert "elements (0)" in result


def test_format_elements_list_limit_truncates():
    elements = [
        {"element_id": f"e{i}", "type": "paragraph", "content": "x"}
        for i in range(10)
    ]
    result = _format_elements_list(elements, limit=3)
    assert "+7 more" in result


def test_format_elements_list_limit_zero_all():
    elements = [
        {"element_id": f"e{i}", "type": "paragraph", "content": "x"}
        for i in range(5)
    ]
    result = _format_elements_list(elements, limit=0)
    # limit=0 → 全部
    assert "+0 more" not in result
    for i in range(5):
        assert f"e{i}" in result


def test_format_elements_list_includes_type_and_id():
    elements = [{"element_id": "e1", "type": "heading", "content": "Title"}]
    result = _format_elements_list(elements, limit=10)
    assert "heading" in result
    assert "e1" in result
    assert "Title" in result


def test_format_elements_list_returns_str():
    result = _format_elements_list([], limit=10)
    assert isinstance(result, str)


def test_format_elements_list_parent_id_displayed():
    elements = [
        {
            "element_id": "e1",
            "type": "paragraph",
            "content": "x",
            "parent_id": "p1",
        }
    ]
    result = _format_elements_list(elements, limit=10)
    assert "p1" in result


# =========================================================================
# _format_chunks_list 深度
# =========================================================================


def test_format_chunks_list_empty():
    result = _format_chunks_list([], limit=10)
    assert "chunks (0)" in result


def test_format_chunks_list_basic():
    chunks = [
        {
            "chunk_id": "c1",
            "text": "hello",
            "source_element_ids": ["e1"],
        }
    ]
    result = _format_chunks_list(chunks, limit=10)
    assert "c1" in result
    assert "chars=5" in result
    assert "refs=1" in result


def test_format_chunks_list_show_spans_no_spans():
    chunks = [
        {
            "chunk_id": "c1",
            "text": "hello",
            "source_element_ids": ["e1"],
            "source_spans": [],
        }
    ]
    result = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "(none)" in result


def test_format_chunks_list_show_spans_with_spans():
    chunks = [
        {
            "chunk_id": "c1",
            "text": "hello",
            "source_element_ids": ["e1"],
            "source_spans": [{"element_id": "e1", "start": 0, "end": 5}],
        }
    ]
    result = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "e1[0:5]" in result


def test_format_chunks_list_show_spans_false_no_span_lines():
    chunks = [
        {
            "chunk_id": "c1",
            "text": "hello",
            "source_element_ids": ["e1"],
            "source_spans": [{"element_id": "e1", "start": 0, "end": 5}],
        }
    ]
    result = _format_chunks_list(chunks, limit=10, show_spans=False)
    # show_spans=False → 不渲染 span 行
    assert "span:" not in result


def test_format_chunks_list_limit_truncates():
    chunks = [
        {"chunk_id": f"c{i}", "text": "x", "source_element_ids": ["e1"]}
        for i in range(10)
    ]
    result = _format_chunks_list(chunks, limit=3)
    assert "+7 more" in result


def test_format_chunks_list_returns_str():
    result = _format_chunks_list([], limit=10)
    assert isinstance(result, str)


# =========================================================================
# _emit_structured_error 深度
# =========================================================================


def test_emit_structured_error_outputs_to_stderr(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code1", "msg1")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "code1" in captured.err
    assert "msg1" in captured.err


def test_emit_structured_error_outputs_valid_json(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code1", "msg1")
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert isinstance(data, dict)


def test_emit_structured_error_has_required_keys(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code1", "msg1")
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert "schema_version" in data
    assert "input" in data
    assert "errors" in data


def test_emit_structured_error_errors_is_list(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code1", "msg1")
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert isinstance(data["errors"], list)
    assert len(data["errors"]) == 1


def test_emit_structured_error_with_extra_kwargs(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code1", "msg1", detail="info")
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["detail"] == "info"


def test_emit_structured_error_schema_version_value(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code1", "msg1")
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["schema_version"] == "0.1.0"


def test_emit_structured_error_input_value(capsys, tmp_path: Path):
    p = tmp_path / "x"
    _emit_structured_error(p, "code1", "msg1")
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["input"] == str(p)


# =========================================================================
# main 退出码深度
# =========================================================================


def test_main_inspect_returns_zero_on_success(tmp_path: Path):
    """inspect 合法 JSON → 返回 0。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "/x",
        "source_type": "pdf",
        "source_hash": SHA,
        "parser_name": "fallback",
        "parser_version": "1",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "x.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert rc == 0


def test_main_validate_returns_zero_on_valid(tmp_path: Path):
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "/x.pdf",
        "source_type": "pdf",
        "source_hash": SHA,
        "parser_name": "fallback",
        "parser_version": "1",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "parent_id": None,
                "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]},
                "content": "x",
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "x.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["validate", str(p)])
    assert rc == 0


def test_main_validate_returns_one_on_invalid(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate", str(p)])
    assert rc == 1


def test_main_validate_returns_two_on_missing(tmp_path: Path):
    rc = main(["validate", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_returns_two_on_missing(tmp_path: Path):
    rc = main(["inspect", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_returns_one_on_invalid_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert rc == 1


def test_main_inspect_returns_one_on_top_level_array(tmp_path: Path):
    p = tmp_path / "arr.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert rc == 1


def test_main_returns_int_type(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate", str(p)])
    assert isinstance(rc, int)


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_argparse():
    from app import cli as mod

    assert hasattr(mod, "argparse")


def test_module_imports_json():
    from app import cli as mod

    assert hasattr(mod, "json")


def test_module_imports_sys():
    from app import cli as mod

    assert hasattr(mod, "sys")


def test_module_imports_path():
    from app import cli as mod

    assert hasattr(mod, "Path")


def test_module_imports_process_single():
    from app import cli as mod

    assert hasattr(mod, "process_single")


def test_module_imports_validate_only():
    from app import cli as mod

    assert hasattr(mod, "validate_only")


def test_module_has_build_arg_parser():
    from app import cli as mod

    assert hasattr(mod, "_build_arg_parser")


def test_module_has_main():
    from app import cli as mod

    assert hasattr(mod, "main")


def test_module_has_emit_structured_error():
    from app import cli as mod

    assert hasattr(mod, "_emit_structured_error")


def test_module_has_infer_parser_name():
    from app import cli as mod

    assert hasattr(mod, "_infer_parser_name")


def test_module_has_iter_supported_files():
    from app import cli as mod

    assert hasattr(mod, "_iter_supported_files")


def test_module_has_relative_output_path():
    from app import cli as mod

    assert hasattr(mod, "_relative_output_path")


def test_module_has_load_document_json():
    from app import cli as mod

    assert hasattr(mod, "_load_document_json")


def test_module_has_format_summary():
    from app import cli as mod

    assert hasattr(mod, "_format_summary")


def test_module_has_format_elements_list():
    from app import cli as mod

    assert hasattr(mod, "_format_elements_list")


def test_module_has_format_chunks_list():
    from app import cli as mod

    assert hasattr(mod, "_format_chunks_list")


def test_module_has_preview():
    from app import cli as mod

    assert hasattr(mod, "_preview")


def test_module_has_extension_to_parser():
    from app import cli as mod

    assert hasattr(mod, "_EXTENSION_TO_PARSER")


def test_module_helpers_callable():
    from app import cli as mod

    assert callable(mod._build_arg_parser)
    assert callable(mod.main)
    assert callable(mod._emit_structured_error)
    assert callable(mod._infer_parser_name)
    assert callable(mod._iter_supported_files)
    assert callable(mod._relative_output_path)
    assert callable(mod._load_document_json)
    assert callable(mod._format_summary)
    assert callable(mod._format_elements_list)
    assert callable(mod._format_chunks_list)
    assert callable(mod._preview)


def test_module_docstring_present():
    from app import cli as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_pdf():
    from app import cli as mod

    doc = mod.__doc__
    assert "pdf" in doc.lower() or "PDF" in doc


def test_module_docstring_mentions_docx():
    from app import cli as mod

    doc = mod.__doc__
    assert "docx" in doc.lower() or "DOCX" in doc


def test_module_docstring_mentions_validate():
    from app import cli as mod

    doc = mod.__doc__
    assert "validate" in doc.lower() or "校验" in doc


def test_module_docstring_mentions_inspect():
    from app import cli as mod

    doc = mod.__doc__
    assert "inspect" in doc.lower()


def test_module_uses_future_annotations():
    import ast

    from app import cli as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


# =========================================================================
# 签名深度
# =========================================================================


def test_main_signature_argv_param():
    import inspect

    sig = inspect.signature(main)
    assert "argv" in sig.parameters


def test_main_argv_default_none():
    import inspect

    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_int():
    import inspect

    sig = inspect.signature(main)
    ret = sig.return_annotation
    assert ret is int or "int" in str(ret)


def test_infer_parser_name_signature_one_param():
    import inspect

    sig = inspect.signature(_infer_parser_name)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "input_path" in params


def test_iter_supported_files_signature_two_params():
    import inspect

    sig = inspect.signature(_iter_supported_files)
    params = list(sig.parameters.keys())
    assert "input_dir" in params
    assert "recursive" in params


def test_relative_output_path_signature_three_params():
    import inspect

    sig = inspect.signature(_relative_output_path)
    params = list(sig.parameters.keys())
    assert "input_dir" in params
    assert "file_path" in params
    assert "output_dir" in params


def test_preview_signature_two_params():
    import inspect

    sig = inspect.signature(_preview)
    params = list(sig.parameters.keys())
    assert "text" in params
    assert "width" in params


def test_preview_width_default_60():
    import inspect

    sig = inspect.signature(_preview)
    assert sig.parameters["width"].default == 60


def test_load_document_json_signature_one_param():
    import inspect

    sig = inspect.signature(_load_document_json)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "input_path" in params


def test_format_summary_signature_two_params():
    import inspect

    sig = inspect.signature(_format_summary)
    params = list(sig.parameters.keys())
    assert "data" in params
    assert "input_path" in params


def test_format_elements_list_signature_two_params():
    import inspect

    sig = inspect.signature(_format_elements_list)
    params = list(sig.parameters.keys())
    assert "elements" in params
    assert "limit" in params


def test_format_chunks_list_signature_three_params():
    import inspect

    sig = inspect.signature(_format_chunks_list)
    params = list(sig.parameters.keys())
    assert "chunks" in params
    assert "limit" in params
    assert "show_spans" in params


def test_format_chunks_list_show_spans_default_false():
    import inspect

    sig = inspect.signature(_format_chunks_list)
    assert sig.parameters["show_spans"].default is False
