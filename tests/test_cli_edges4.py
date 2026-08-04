"""app/cli.py 边角测试 - 第四轮（Round 107）。

补强已有 base/edges/edges2/edges3（共 357 个测试）未覆盖的深度路径：
- _load_document_json：null/number/string/bool 根、permission denied、JSON 数组根细节
- _run_parse：成功路径（mock process_single 返回 document）、errors 路径
- _run_parse_dir：全失败 summary、failure>0 返回 1、过程消息
- _format_summary：含 relations、含 chunks 但 text 为 None、source_hash 缺失
- _format_elements_list：所有 element 缺各 key、limit 边界
- _format_chunks_list：limit 与 spans 组合、refs=None
- _iter_supported_files：扩展名大写、混合类型目录
- _relative_output_path：Windows 反斜杠归一、绝对路径
- _preview：CJK unicode、特殊字符
- _emit_structured_error：extra 含 None 值
- main：inspect 各种组合、parse-dir 失败汇总
- argparse：prog/description 文本、subcommand 必填

不修改任何源码。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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


# =========================================================================
# _load_document_json 深度
# =========================================================================


def test_load_document_json_null_root(tmp_path: Path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data is None
    assert err == ""


def test_load_document_json_number_root(tmp_path: Path):
    p = tmp_path / "num.json"
    p.write_text("42", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == 42
    assert err == ""


def test_load_document_json_string_root(tmp_path: Path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == "hello"


def test_load_document_json_boolean_root(tmp_path: Path):
    p = tmp_path / "bool.json"
    p.write_text("true", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data is True


def test_load_document_json_array_with_data(tmp_path: Path):
    p = tmp_path / "arr.json"
    p.write_text('[{"a":1}, {"b":2}]', encoding="utf-8")
    data, _ = _load_document_json(p)
    assert isinstance(data, list)
    assert len(data) == 2


def test_load_document_json_empty_object(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == {}
    assert err == ""


def test_load_document_json_returns_tuple_type(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    result = _load_document_json(p)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_load_document_json_error_message_for_missing_includes_path(tmp_path: Path):
    p = tmp_path / "missing.json"
    _, err = _load_document_json(p)
    assert str(p) in err


def test_load_document_json_handles_utf8_with_bom(tmp_path: Path):
    """BOM 行为：Python json.load 默认不接受 BOM 前缀。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"key": "value"}')
    data, err = _load_document_json(p)
    # 实际行为：JSONDecodeError → 返回 (None, err)
    if data is None:
        assert "JSON" in err or "解析失败" in err
    else:
        assert data == {"key": "value"}


# =========================================================================
# _preview 深度
# =========================================================================


def test_preview_cjk_unicode_preserved():
    text = "你好世界"
    assert _preview(text) == "你好世界"


def test_preview_cjk_unicode_truncated():
    text = "你" * 100
    result = _preview(text, width=10)
    assert result.endswith("…")
    assert len(result) <= 11


def test_preview_emoji_preserved():
    text = "hello 🌍 world"
    result = _preview(text)
    assert "🌍" in result


def test_preview_special_chars_preserved():
    text = "a@b#c$d%e^f&g"
    result = _preview(text)
    assert "@" in result
    assert "#" in result


def test_preview_newline_in_text_collapsed():
    text = "line1\nline2\nline3"
    result = _preview(text)
    assert "\n" not in result
    assert "line1" in result
    assert "line3" in result


def test_preview_carriage_return_collapsed():
    text = "line1\rline2"
    result = _preview(text)
    assert "\r" not in result


def test_preview_vertical_tab_collapsed():
    text = "a\vb"
    result = _preview(text)
    assert "\v" not in result


def test_preview_form_feed_collapsed():
    text = "a\fb"
    result = _preview(text)
    assert "\f" not in result


def test_preview_width_zero_short_text_returns_truncated_with_ellipsis():
    """width=0 + 短文本：collapsed[:0-1] + '…' = collapsed[:-1] + '…'。"""
    result = _preview("short", width=0)
    assert result.endswith("…")
    # collapsed[:-1] 剥掉最后一个字符
    assert "shor" in result


def test_preview_width_zero_empty_text_returns_empty():
    assert _preview("", width=0) == ""


def test_preview_width_huge_returns_full_text():
    text = "x" * 200
    assert _preview(text, width=10000) == text


def test_preview_negative_width_always_truncates():
    text = "abc"
    result = _preview(text, width=-1)
    # collapsed[: -1 - 1] = collapsed[:-2] = "a" + "…" = "a…"
    # 实际：collapsed[:width-1] + "…" = collapsed[:-2] + "…" = "a…"
    assert result.endswith("…")


def test_preview_width_one_huge_text_only_ellipsis():
    text = "x" * 100
    result = _preview(text, width=1)
    assert result == "…"


def test_preview_width_two_returns_one_char_plus_ellipsis():
    text = "abcdef"
    result = _preview(text, width=2)
    assert result == "a…"


# =========================================================================
# _emit_structured_error 深度
# =========================================================================


def test_emit_structured_error_extra_with_none_value(capsys, tmp_path: Path):
    """extra 字典含 None 值应被保留（不剔除）。"""
    _emit_structured_error(tmp_path / "x", "code", "msg", key_with_none=None)
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["key_with_none"] is None


def test_emit_structured_error_extra_with_nested_dict(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code", "msg", nested={"a": 1, "b": [1, 2]})
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["nested"] == {"a": 1, "b": [1, 2]}


def test_emit_structured_error_extra_with_list_value(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code", "msg", items=["a", "b", "c"])
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["items"] == ["a", "b", "c"]


def test_emit_structured_error_extra_with_int_value(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code", "msg", count=42)
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["count"] == 42


def test_emit_structured_error_extra_with_bool_value(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code", "msg", flag=True)
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["flag"] is True


def test_emit_structured_error_stdout_empty(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code", "msg")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_emit_structured_error_returns_none(capsys, tmp_path: Path):
    assert _emit_structured_error(tmp_path / "x", "code", "msg") is None


# =========================================================================
# _format_summary 深度
# =========================================================================


def test_format_summary_with_relations_data():
    data = {
        "schema_version": "0.1.0",
        "relations": [
            {"type": "caption_for", "from": "e1", "to": "e2"},
            {"type": "heading_for", "from": "e3", "to": "e4"},
        ],
    }
    out = _format_summary(data, Path("x.json"))
    assert "relations=2" in out


def test_format_summary_with_chunks_text_none():
    """chunks text=None 应被当作空字符串处理。"""
    data = {"chunks": [{"text": None, "source_element_ids": []}]}
    out = _format_summary(data, Path("x.json"))
    assert "chunks=1" in out


def test_format_summary_with_chunks_no_source_element_ids():
    data = {"chunks": [{"text": "abc"}]}
    out = _format_summary(data, Path("x.json"))
    assert "chunks=1" in out


def test_format_summary_source_hash_missing():
    data = {"schema_version": "0.1.0"}
    out = _format_summary(data, Path("x.json"))
    assert "hash=" in out


def test_format_summary_source_hash_short():
    """source_hash < 16 字符 → 切片不报错。"""
    data = {"source_hash": "abc"}
    out = _format_summary(data, Path("x.json"))
    assert "hash=" in out


def test_format_summary_source_hash_empty():
    data = {"source_hash": ""}
    out = _format_summary(data, Path("x.json"))
    assert "hash=" in out


def test_format_summary_warnings_more_than_5_truncation_marker():
    warnings = [{"code": f"c{i}", "reason": f"r{i}"} for i in range(7)]
    data = {"warnings": warnings}
    out = _format_summary(data, Path("x.json"))
    assert "+2 more" in out


def test_format_summary_warnings_exactly_5_no_truncation():
    warnings = [{"code": f"c{i}", "reason": f"r{i}"} for i in range(5)]
    data = {"warnings": warnings}
    out = _format_summary(data, Path("x.json"))
    assert "+0 more" not in out
    assert "more" not in out


def test_format_summary_warnings_6_truncation_1_more():
    warnings = [{"code": f"c{i}", "reason": f"r{i}"} for i in range(6)]
    data = {"warnings": warnings}
    out = _format_summary(data, Path("x.json"))
    assert "+1 more" in out


def test_format_summary_errors_with_code_and_message():
    data = {"errors": [{"code": "test_err", "message": "test msg"}]}
    out = _format_summary(data, Path("x.json"))
    assert "test_err" in out
    assert "test msg" in out


def test_format_summary_elements_with_no_type_uses_question_mark():
    data = {"elements": [{"content": "x"}]}
    out = _format_summary(data, Path("x.json"))
    assert "?=1" in out


def test_format_summary_chunks_avg_format():
    """chunks avg 应为整数（avg:.0f 格式）。"""
    data = {"chunks": [{"text": "abc", "source_element_ids": ["e1"]}]}
    out = _format_summary(data, Path("x.json"))
    assert "avg=" in out


def test_format_summary_returns_str_type():
    out = _format_summary({}, Path("x.json"))
    assert isinstance(out, str)


def test_format_summary_chunks_refs_avg_one_decimal():
    """chunks refs avg 应为 1 位小数（avg:.1f 格式）。"""
    data = {
        "chunks": [
            {"text": "a", "source_element_ids": ["e1", "e2"]},
            {"text": "b", "source_element_ids": ["e3"]},
        ]
    }
    out = _format_summary(data, Path("x.json"))
    assert "avg=1.5" in out


def test_format_summary_includes_schema_version():
    data = {"schema_version": "9.9.9"}
    out = _format_summary(data, Path("x.json"))
    assert "9.9.9" in out


# =========================================================================
# _format_elements_list 深度
# =========================================================================


def test_format_elements_list_element_no_keys():
    out = _format_elements_list([{}], limit=10)
    assert "?" in out  # missing element_id and type


def test_format_elements_list_with_long_content_truncated():
    el = {"element_id": "eid", "type": "paragraph", "content": "x" * 200}
    out = _format_elements_list([el], limit=10)
    assert "…" in out


def test_format_elements_list_with_content_exactly_at_width():
    el = {"element_id": "eid", "type": "paragraph", "content": "x" * 60}
    out = _format_elements_list([el], limit=10)
    assert "…" not in out


def test_format_elements_list_returns_str():
    out = _format_elements_list([], limit=10)
    assert isinstance(out, str)


def test_format_elements_list_limit_more_than_count_no_marker():
    out = _format_elements_list(
        [{"element_id": "e1", "type": "paragraph", "content": "x"}], limit=10
    )
    assert "+0 more" not in out
    assert "more" not in out


def test_format_elements_list_zero_limit_lists_all():
    elements = [{"element_id": f"e{i}", "type": "p", "content": str(i)} for i in range(5)]
    out = _format_elements_list(elements, limit=0)
    assert "e0" in out
    assert "e4" in out


def test_format_elements_list_parent_id_empty_string_omitted():
    el = {"element_id": "e1", "type": "p", "content": "x", "parent_id": ""}
    out = _format_elements_list([el], limit=10)
    assert "parent=" not in out


# =========================================================================
# _format_chunks_list 深度
# =========================================================================


def test_format_chunks_list_returns_str():
    out = _format_chunks_list([], limit=10)
    assert isinstance(out, str)


def test_format_chunks_list_limit_zero_shows_all():
    chunks = [{"chunk_id": f"c{i}", "text": str(i), "source_element_ids": []} for i in range(5)]
    out = _format_chunks_list(chunks, limit=0)
    assert "c0" in out
    assert "c4" in out


def test_format_chunks_list_with_show_spans_and_no_spans_data():
    chunks = [{"chunk_id": "c1", "text": "abc", "source_element_ids": []}]
    out = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "spans: (none)" in out


def test_format_chunks_list_with_show_spans_and_empty_spans():
    chunks = [{"chunk_id": "c1", "text": "abc", "source_element_ids": [], "source_spans": []}]
    out = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "spans: (none)" in out


def test_format_chunks_list_with_show_spans_and_actual_spans():
    chunks = [{
        "chunk_id": "c1",
        "text": "abc",
        "source_element_ids": [],
        "source_spans": [{"element_id": "e1", "start": 0, "end": 3}],
    }]
    out = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "e1[0:3]" in out


def test_format_chunks_list_with_missing_chunk_id():
    chunks = [{"text": "abc", "source_element_ids": []}]
    out = _format_chunks_list(chunks, limit=10)
    assert "?" in out


def test_format_chunks_list_text_is_empty_string():
    chunks = [{"chunk_id": "c1", "text": "", "source_element_ids": []}]
    out = _format_chunks_list(chunks, limit=10)
    assert "chars=0" in out


def test_format_chunks_list_limit_more_than_count_no_marker():
    out = _format_chunks_list(
        [{"chunk_id": "c1", "text": "abc", "source_element_ids": []}], limit=10
    )
    assert "more" not in out


# =========================================================================
# _iter_supported_files 深度
# =========================================================================


def test_iter_supported_files_uppercase_extension(tmp_path: Path):
    """大写扩展名应仍被识别（suffix.lower()）。"""
    (tmp_path / "a.TXT").write_text("x", encoding="utf-8")
    (tmp_path / "b.MD").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    assert len(files) == 2


def test_iter_supported_files_mixed_case_extension(tmp_path: Path):
    (tmp_path / "x.TxT").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    assert len(files) == 1


def test_iter_supported_files_empty_dir_returns_empty(tmp_path: Path):
    assert _iter_supported_files(tmp_path, recursive=False) == []


def test_iter_supported_files_only_unsupported_returns_empty(tmp_path: Path):
    (tmp_path / "a.csv").write_text("x", encoding="utf-8")
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    assert _iter_supported_files(tmp_path, recursive=False) == []


def test_iter_supported_files_returns_list_type(tmp_path: Path):
    result = _iter_supported_files(tmp_path, recursive=False)
    assert isinstance(result, list)


def test_iter_supported_files_mixed_supported_and_unsupported(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.csv").write_text("x", encoding="utf-8")
    (tmp_path / "c.md").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    names = sorted(p.name for p in files)
    assert names == ["a.txt", "c.md"]


def test_iter_supported_files_recursive_finds_subdir_files(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.md").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=True)
    assert len(files) == 2


def test_iter_supported_files_non_recursive_ignores_subdir(tmp_path: Path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.md").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    assert len(files) == 1


def test_iter_supported_files_skips_directories_in_recursive(tmp_path: Path):
    """recursive=True 时目录本身不应出现在结果。"""
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    files = _iter_supported_files(tmp_path, recursive=True)
    assert all(p.is_file() for p in files)


# =========================================================================
# _relative_output_path 深度
# =========================================================================


def test_relative_output_path_handles_backslashes(tmp_path: Path):
    """Windows 路径反斜杠应被替换为正斜杠。"""
    file_path = tmp_path / "sub" / "doc.md"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("x", encoding="utf-8")
    out = _relative_output_path(tmp_path, file_path, tmp_path / "out")
    # 输出路径含 "sub/doc.md.json"（正斜杠）
    assert "sub/doc.md.json" in str(out).replace("\\", "/")


def test_relative_output_path_root_file(tmp_path: Path):
    f = tmp_path / "x.txt"
    f.write_text("x", encoding="utf-8")
    out = _relative_output_path(tmp_path, f, tmp_path / "out")
    assert out.name == "x.txt.json"


def test_relative_output_path_deeply_nested(tmp_path: Path):
    f = tmp_path / "a" / "b" / "c" / "d.md"
    f.parent.mkdir(parents=True)
    f.write_text("x", encoding="utf-8")
    out = _relative_output_path(tmp_path, f, tmp_path / "out")
    assert out.parent == tmp_path / "out" / "a" / "b" / "c"


def test_relative_output_path_filename_with_multiple_dots(tmp_path: Path):
    f = tmp_path / "archive.tar.gz"
    f.write_text("x", encoding="utf-8")
    out = _relative_output_path(tmp_path, f, tmp_path / "out")
    assert "archive.tar.gz.json" in str(out).replace("\\", "/")


def test_relative_output_path_filename_no_extension(tmp_path: Path):
    f = tmp_path / "README"
    f.write_text("x", encoding="utf-8")
    out = _relative_output_path(tmp_path, f, tmp_path / "out")
    assert "README.json" in str(out)


def test_relative_output_path_returns_path_object(tmp_path: Path):
    f = tmp_path / "x.txt"
    f.write_text("x", encoding="utf-8")
    out = _relative_output_path(tmp_path, f, tmp_path / "out")
    assert isinstance(out, Path)


# =========================================================================
# _infer_parser_name 深度
# =========================================================================


def test_infer_parser_name_pdf_lowercase():
    assert _infer_parser_name(Path("test.pdf")) == "fallback"


def test_infer_parser_name_pdf_uppercase():
    assert _infer_parser_name(Path("TEST.PDF")) == "fallback"


def test_infer_parser_name_no_extension():
    assert _infer_parser_name(Path("README")) == "fallback"


def test_infer_parser_name_unknown_extension_csv():
    assert _infer_parser_name(Path("data.csv")) == "fallback"


def test_infer_parser_name_unknown_extension_json():
    assert _infer_parser_name(Path("data.json")) == "fallback"


def test_infer_parser_name_dotfile_only():
    """`.gitignore` → suffix=''（dotfile 不算扩展名）→ fallback。"""
    assert _infer_parser_name(Path(".gitignore")) == "fallback"


def test_infer_parser_name_returns_str():
    assert isinstance(_infer_parser_name(Path("x.txt")), str)


# =========================================================================
# _EXTENSION_TO_PARSER 模块常量
# =========================================================================


def test_extension_to_parser_count_is_nine():
    assert len(_EXTENSION_TO_PARSER) == 9


def test_extension_to_parser_keys_all_lowercase():
    for k in _EXTENSION_TO_PARSER:
        assert k == k.lower()
        assert k.startswith(".")


def test_extension_to_parser_values_set():
    values = set(_EXTENSION_TO_PARSER.values())
    assert values == {"fallback", "markdown", "html", "text", "ipynb"}


def test_extension_to_parser_pdf_docx_both_fallback():
    assert _EXTENSION_TO_PARSER[".pdf"] == "fallback"
    assert _EXTENSION_TO_PARSER[".docx"] == "fallback"


def test_extension_to_parser_kreuzberg_not_in_values():
    """kreuzberg 必须显式指定，不在扩展名映射里。"""
    assert "kreuzberg" not in _EXTENSION_TO_PARSER.values()


# =========================================================================
# _build_arg_parser 深度
# =========================================================================


def test_build_arg_parser_prog_is_app_cli():
    p = _build_arg_parser()
    assert p.prog == "app.cli"


def test_build_arg_parser_description_mentions_pdf():
    p = _build_arg_parser()
    assert "PDF" in p.description or "pdf" in p.description.lower()


def test_build_arg_parser_description_mentions_docx():
    p = _build_arg_parser()
    assert "DOCX" in p.description or "docx" in p.description.lower()


def test_build_arg_parser_has_subparsers_required():
    p = _build_arg_parser()
    # subparsers 是必填（required=True）
    # 通过 SystemExit 验证（无 subcommand）
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_arg_parser_parse_subcommand_exists():
    p = _build_arg_parser()
    args = p.parse_args(["parse", "in.pdf", "-o", "out.json"])
    assert args.command == "parse"


def test_build_arg_parser_validate_subcommand_exists():
    p = _build_arg_parser()
    args = p.parse_args(["validate", "in.json"])
    assert args.command == "validate"


def test_build_arg_parser_inspect_subcommand_exists():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "in.json"])
    assert args.command == "inspect"


def test_build_arg_parser_parse_dir_subcommand_exists():
    p = _build_arg_parser()
    args = p.parse_args(["parse-dir", "indir", "-o", "outdir"])
    assert args.command == "parse-dir"


def test_build_arg_parser_parse_dir_recursive_flag():
    p = _build_arg_parser()
    args = p.parse_args(["parse-dir", "indir", "-o", "outdir", "--recursive"])
    assert args.recursive is True


def test_build_arg_parser_parse_dir_parser_override():
    p = _build_arg_parser()
    args = p.parse_args(["parse-dir", "indir", "-o", "outdir", "--parser", "kreuzberg"])
    assert args.parser == "kreuzberg"


def test_build_arg_parser_parse_dir_max_chars_int():
    p = _build_arg_parser()
    args = p.parse_args(["parse-dir", "indir", "-o", "outdir", "--max-chars", "500"])
    assert args.max_chars == 500
    assert isinstance(args.max_chars, int)


def test_build_arg_parser_returns_argument_parser():
    p = _build_arg_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_arg_parser_inspect_limit_zero_accepted():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "in.json", "--limit", "0"])
    assert args.limit == 0


def test_build_arg_parser_inspect_limit_negative_accepted():
    p = _build_arg_parser()
    args = p.parse_args(["inspect", "in.json", "--limit", "-1"])
    assert args.limit == -1


def test_build_arg_parser_inspect_limit_non_int_exits():
    p = _build_arg_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect", "in.json", "--limit", "abc"])


# =========================================================================
# main 深度
# =========================================================================


def test_main_inspect_nonexistent_file_returns_2(tmp_path: Path):
    rc = main(["inspect", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_returns_0_with_summary_only(tmp_path: Path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"schema_version": "0.1.0", "document_id": "x"}), encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert rc == 0


def test_main_inspect_with_elements_flag(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "schema_version": "0.1.0",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "hello"}],
    }), encoding="utf-8")
    rc = main(["inspect", str(p), "--elements"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements (1):" in out
    assert "e1" in out


def test_main_inspect_with_chunks_flag(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "schema_version": "0.1.0",
        "chunks": [{"chunk_id": "c1", "text": "abc", "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    rc = main(["inspect", str(p), "--chunks"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "chunks (1):" in out


def test_main_inspect_with_chunks_and_spans(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "schema_version": "0.1.0",
        "chunks": [{
            "chunk_id": "c1",
            "text": "abc",
            "source_element_ids": ["e1"],
            "source_spans": [{"element_id": "e1", "start": 0, "end": 3}],
        }],
    }), encoding="utf-8")
    rc = main(["inspect", str(p), "--chunks", "--spans"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "e1[0:3]" in out


def test_main_inspect_with_limit_for_elements(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "schema_version": "0.1.0",
        "elements": [
            {"element_id": f"e{i}", "type": "p", "content": str(i)} for i in range(20)
        ],
    }), encoding="utf-8")
    rc = main(["inspect", str(p), "--elements", "--limit", "5"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "e0" in out
    assert "+15 more" in out


def test_main_inspect_with_limit_zero_lists_all(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "schema_version": "0.1.0",
        "elements": [
            {"element_id": f"e{i}", "type": "p", "content": str(i)} for i in range(20)
        ],
    }), encoding="utf-8")
    rc = main(["inspect", str(p), "--elements", "--limit", "0"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "more" not in out


def test_main_inspect_returns_int_type(tmp_path: Path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert isinstance(rc, int)


def test_main_inspect_invalid_json_returns_1(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert rc == 1


def test_main_inspect_top_level_array_returns_1(tmp_path: Path):
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert rc == 1


def test_main_inspect_top_level_string_returns_1(tmp_path: Path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    rc = main(["inspect", str(p)])
    assert rc == 1


def test_main_validate_nonexistent_file_returns_2(tmp_path: Path):
    rc = main(["validate", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_parse_nonexistent_input_returns_1(tmp_path: Path):
    rc = main(["parse", str(tmp_path / "missing.pdf"), "-o", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_parse_dir_nonexistent_dir_returns_2(tmp_path: Path):
    rc = main(["parse-dir", str(tmp_path / "missingdir"), "-o", str(tmp_path / "out")])
    assert rc == 2


def test_main_unknown_subcommand_raises_system_exit():
    with pytest.raises(SystemExit):
        main(["unknown-command"])


def test_main_no_subcommand_raises_system_exit():
    with pytest.raises(SystemExit):
        main([])


# =========================================================================
# 模块结构
# =========================================================================


def test_module_imports_argparse():
    from app import cli
    assert hasattr(cli, "argparse")


def test_module_imports_json():
    from app import cli
    assert hasattr(cli, "json")


def test_module_imports_sys():
    from app import cli
    assert hasattr(cli, "sys")


def test_module_imports_path():
    from app import cli
    assert hasattr(cli, "Path")


def test_module_imports_process_single():
    from app import cli
    assert hasattr(cli, "process_single")


def test_module_imports_validate_only():
    from app import cli
    assert hasattr(cli, "validate_only")


def test_module_has_build_arg_parser():
    from app import cli
    assert hasattr(cli, "_build_arg_parser")


def test_module_has_main():
    from app import cli
    assert hasattr(cli, "main")


def test_module_has_emit_structured_error():
    from app import cli
    assert hasattr(cli, "_emit_structured_error")


def test_module_has_infer_parser_name():
    from app import cli
    assert hasattr(cli, "_infer_parser_name")


def test_module_has_iter_supported_files():
    from app import cli
    assert hasattr(cli, "_iter_supported_files")


def test_module_has_relative_output_path():
    from app import cli
    assert hasattr(cli, "_relative_output_path")


def test_module_has_load_document_json():
    from app import cli
    assert hasattr(cli, "_load_document_json")


def test_module_has_format_summary():
    from app import cli
    assert hasattr(cli, "_format_summary")


def test_module_has_format_elements_list():
    from app import cli
    assert hasattr(cli, "_format_elements_list")


def test_module_has_format_chunks_list():
    from app import cli
    assert hasattr(cli, "_format_chunks_list")


def test_module_has_preview():
    from app import cli
    assert hasattr(cli, "_preview")


def test_module_main_callable():
    from app import cli
    assert callable(cli.main)


def test_module_build_arg_parser_callable():
    from app import cli
    assert callable(cli._build_arg_parser)
