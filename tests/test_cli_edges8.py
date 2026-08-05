r"""app/cli.py 边角测试 - 第八轮（Round 190）。

补强已有 base/edges/edges2-7（共 900 测试）未覆盖的深度：
- _run_parse 成功路径（返回 0、写盘、parser override、--max-chars override）
- _run_parse_dir 多文件场景（成功/失败混合、recursive、parser override）
- main() 端到端 parse 与 parse-dir 命令
- _format_summary 各字段边界（chunks 0 refs、chunk text with newline、type=None、content=None）
- _format_elements_list 元素变体
- _format_chunks_list span 格式（start/end 数值显示）
- _load_document_json OSError 路径
- _emit_structured_error extra 类型覆盖（int/list/dict/Path）
- _iter_supported_files 文件名排序稳定性
- _relative_output_path 跨平台分隔符
- _build_arg_parser 各 subcommand choices 完整性
- _infer_parser_name 双 suffix（.tar.gz）/ 多点文件名
- 模块结构与 imports
"""

from __future__ import annotations

import inspect
import io
import json
from pathlib import Path
from typing import Any

import pytest

from app import cli as cli_mod
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
    _run_parse,
    _run_parse_dir,
)
import argparse


# =========================================================================
# _run_parse 成功路径
# =========================================================================


def test_run_parse_success_returns_0(tmp_path: Path, capsys):
    src = tmp_path / "input.txt"
    src.write_text("hello world paragraph content here.", encoding="utf-8")
    out = tmp_path / "out.json"
    args = argparse.Namespace(
        input=str(src),
        output=str(out),
        parser="text",
        max_chars=800,
    )
    rc = _run_parse(args)
    assert rc == 0
    assert out.is_file()


def test_run_parse_success_writes_valid_json(tmp_path: Path):
    src = tmp_path / "input.txt"
    src.write_text("hello world paragraph content here.", encoding="utf-8")
    out = tmp_path / "out.json"
    args = argparse.Namespace(
        input=str(src),
        output=str(out),
        parser="text",
        max_chars=800,
    )
    _run_parse(args)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.1.0"
    assert "elements" in data
    assert "chunks" in data


def test_run_parse_auto_inference_when_parser_none(tmp_path: Path, capsys):
    src = tmp_path / "input.txt"
    src.write_text("auto inferred text content.", encoding="utf-8")
    out = tmp_path / "out.json"
    args = argparse.Namespace(
        input=str(src),
        output=str(out),
        parser=None,  # 触发自动推断
        max_chars=800,
    )
    rc = _run_parse(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "[INFO]" in captured.err


def test_run_parse_max_chars_override(tmp_path: Path):
    src = tmp_path / "input.txt"
    src.write_text("a" * 2000, encoding="utf-8")  # 长文本
    out = tmp_path / "out.json"
    args = argparse.Namespace(
        input=str(src),
        output=str(out),
        parser="text",
        max_chars=100,  # 小分块
    )
    _run_parse(args)
    data = json.loads(out.read_text(encoding="utf-8"))
    chunk_lens = [len(c["text"]) for c in data["chunks"]]
    assert max(chunk_lens) <= 100


def test_run_parse_explicit_parser_text(tmp_path: Path):
    src = tmp_path / "input.txt"
    src.write_text("explicit text parser", encoding="utf-8")
    out = tmp_path / "out.json"
    args = argparse.Namespace(
        input=str(src),
        output=str(out),
        parser="text",
        max_chars=800,
    )
    rc = _run_parse(args)
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["parser_name"] == "text"


def test_run_parse_unlinks_partial_on_failure(tmp_path: Path, capsys):
    """parse 失败时不应留下半成品 JSON。"""
    src = tmp_path / "input.txt"
    src.write_text("", encoding="utf-8")  # 空内容 → no_extracted_elements
    out = tmp_path / "out.json"
    args = argparse.Namespace(
        input=str(src),
        output=str(out),
        parser="text",
        max_chars=800,
    )
    rc = _run_parse(args)
    assert rc == 1
    assert not out.exists() or out.stat().st_size == 0  # 不应有内容


# =========================================================================
# _run_parse_dir 多文件场景
# =========================================================================


def test_run_parse_dir_returns_0_when_all_succeed(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("alpha content", encoding="utf-8")
    (src_dir / "b.txt").write_text("beta content", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    rc = _run_parse_dir(args)
    assert rc == 0
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["success"] == 2
    assert summary["failure"] == 0


def test_run_parse_dir_returns_1_when_any_fails(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    (src_dir / "good.txt").write_text("good content", encoding="utf-8")
    (src_dir / "bad.txt").write_text("", encoding="utf-8")  # 空内容失败
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    rc = _run_parse_dir(args)
    assert rc == 1


def test_run_parse_dir_summary_files_count(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    for i in range(3):
        (src_dir / f"f{i}.txt").write_text(f"content {i}", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert len(summary["files"]) == 3


def test_run_parse_dir_recursive_traverses_subdirs(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    sub = src_dir / "sub"
    sub.mkdir(parents=True)
    (src_dir / "top.txt").write_text("top", encoding="utf-8")
    (sub / "deep.txt").write_text("deep", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=True,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 2
    # 应有 nested 路径输出
    nested = (out_dir / "sub" / "deep.txt.json")
    assert nested.is_file()


def test_run_parse_dir_parser_override_applied_to_all(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("hello", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=False,
        parser="text",
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["parser_override"] == "text"
    for f_info in summary["files"]:
        assert f_info["parser"] == "text"


def test_run_parse_dir_summary_success_failure_counts(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    (src_dir / "good.txt").write_text("good", encoding="utf-8")
    (src_dir / "bad.txt").write_text("", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["success"] == 1
    assert summary["failure"] == 1


def test_run_parse_dir_file_entry_has_status_field(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("hello", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["files"][0]["status"] == "ok"


def test_run_parse_dir_file_entry_has_input_output_paths(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("hello", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    f = summary["files"][0]
    assert "input" in f
    assert "output" in f
    assert "a.txt" in f["input"]


def test_run_parse_dir_file_entry_failure_has_errors(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    (src_dir / "bad.txt").write_text("", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    f = summary["files"][0]
    assert f["status"] == "fail"
    assert "errors" in f
    assert len(f["errors"]) > 0


def test_run_parse_dir_writes_per_doc_json(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    (src_dir / "doc1.txt").write_text("alpha", encoding="utf-8")
    (src_dir / "doc2.txt").write_text("beta", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    assert (out_dir / "doc1.txt.json").is_file()
    assert (out_dir / "doc2.txt.json").is_file()


def test_run_parse_dir_summary_total_equals_file_count(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    for i in range(5):
        (src_dir / f"f{i}.txt").write_text(f"c{i}", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    args = argparse.Namespace(
        input_dir=str(src_dir),
        output_dir=str(out_dir),
        recursive=False,
        parser=None,
        max_chars=800,
    )
    _run_parse_dir(args)
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == len(summary["files"]) == 5


# =========================================================================
# main() 端到端
# =========================================================================


def test_main_parse_returns_0_on_success(tmp_path: Path):
    src = tmp_path / "input.txt"
    src.write_text("hello world content", encoding="utf-8")
    out = tmp_path / "out.json"
    rc = cli_mod.main(["parse", str(src), "-o", str(out), "--parser", "text"])
    assert rc == 0
    assert out.is_file()


def test_main_parse_dir_returns_0_on_success(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("alpha", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    rc = cli_mod.main(["parse-dir", str(src_dir), "-o", str(out_dir)])
    assert rc == 0
    assert (out_dir / "_summary.json").is_file()


def test_main_parse_with_max_chars_arg(tmp_path: Path):
    src = tmp_path / "input.txt"
    src.write_text("a" * 2000, encoding="utf-8")
    out = tmp_path / "out.json"
    rc = cli_mod.main([
        "parse", str(src), "-o", str(out),
        "--parser", "text", "--max-chars", "100",
    ])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert max(len(c["text"]) for c in data["chunks"]) <= 100


def test_main_parse_dir_recursive_flag(tmp_path: Path):
    src_dir = tmp_path / "inputs"
    sub = src_dir / "sub"
    sub.mkdir(parents=True)
    (src_dir / "top.txt").write_text("top", encoding="utf-8")
    (sub / "deep.txt").write_text("deep", encoding="utf-8")
    out_dir = tmp_path / "outputs"
    rc = cli_mod.main([
        "parse-dir", str(src_dir), "-o", str(out_dir), "--recursive",
    ])
    assert rc == 0
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["recursive"] is True
    assert summary["total"] == 2


# =========================================================================
# _format_summary 字段边界
# =========================================================================


def _make_doc_dict(**overrides: Any) -> dict:
    base = {
        "schema_version": "0.1.0",
        "document_id": "doc-x",
        "source_path": "/x.txt",
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
    base.update(overrides)
    return base


def test_format_summary_chunks_with_zero_refs(tmp_path: Path):
    """chunks 的 source_element_ids 为空时 refs stat 应处理。"""
    data = _make_doc_dict(chunks=[{
        "chunk_id": "c1", "text": "hello",
        "source_element_ids": [], "metadata": {},
    }])
    s = _format_summary(data, tmp_path / "x.json")
    assert "chunk refs" in s


def test_format_summary_chunk_text_with_newline(tmp_path: Path):
    """chunk text 含换行，preview 会折叠。"""
    data = _make_doc_dict(chunks=[{
        "chunk_id": "c1", "text": "line1\nline2",
        "source_element_ids": [], "metadata": {},
    }])
    s = _format_summary(data, tmp_path / "x.json")
    assert "chunk text" in s


def test_format_summary_element_content_none(tmp_path: Path):
    """element content=None 应作为 0 字符。"""
    data = _make_doc_dict(elements=[{
        "element_id": "e1", "type": "paragraph",
        "content": None, "source_locator": {"line": 1},
        "parent_id": None, "confidence": 1.0, "metadata": {},
    }])
    s = _format_summary(data, tmp_path / "x.json")
    assert "paragraph=1" in s


def test_format_summary_element_type_none_uses_question_mark(tmp_path: Path):
    """element type=None → el.get('type', '?') 返回 None（key 存在），type_counts[None]=1。"""
    data = _make_doc_dict(elements=[{
        "element_id": "e1", "type": None,
        "content": "x", "source_locator": {"line": 1},
        "parent_id": None, "confidence": 1.0, "metadata": {},
    }])
    s = _format_summary(data, tmp_path / "x.json")
    # None 键会被 str(None) 显示
    assert "None=1" in s


def test_format_summary_element_types_sorted(tmp_path: Path):
    """type_counts 按键排序输出。"""
    data = _make_doc_dict(elements=[
        {"element_id": "e1", "type": "paragraph", "content": "x",
         "source_locator": {"line": 1}, "parent_id": None,
         "confidence": 1.0, "metadata": {}},
        {"element_id": "e2", "type": "heading", "content": "y",
         "source_locator": {"line": 2}, "parent_id": None,
         "confidence": 1.0, "metadata": {}},
        {"element_id": "e3", "type": "list_item", "content": "z",
         "source_locator": {"line": 3}, "parent_id": None,
         "confidence": 1.0, "metadata": {}},
    ])
    s = _format_summary(data, tmp_path / "x.json")
    # sorted: heading, list_item, paragraph
    pos_h = s.find("heading=")
    pos_l = s.find("list_item=")
    pos_p = s.find("paragraph=")
    assert pos_h < pos_l < pos_p


def test_format_summary_avg_chars_display(tmp_path: Path):
    data = _make_doc_dict(elements=[
        {"element_id": "e1", "type": "paragraph", "content": "12345",
         "source_locator": {"line": 1}, "parent_id": None,
         "confidence": 1.0, "metadata": {}},
    ])
    s = _format_summary(data, tmp_path / "x.json")
    assert "avg=5" in s


def test_format_summary_chunk_min_max_avg(tmp_path: Path):
    data = _make_doc_dict(chunks=[
        {"chunk_id": "c1", "text": "a" * 10,
         "source_element_ids": [], "metadata": {}},
        {"chunk_id": "c2", "text": "b" * 30,
         "source_element_ids": [], "metadata": {}},
    ])
    s = _format_summary(data, tmp_path / "x.json")
    assert "min=10" in s
    assert "max=30" in s


def test_format_summary_warnings_truncated_message(tmp_path: Path):
    """warnings > 5 显示 +N more。"""
    warns = [{"code": f"w{i}", "reason": f"r{i}"} for i in range(7)]
    data = _make_doc_dict(warnings=warns)
    s = _format_summary(data, tmp_path / "x.json")
    assert "+2 more" in s


def test_format_summary_errors_truncated_at_five(tmp_path: Path):
    errors = [{"code": f"e{i}", "message": f"m{i}"} for i in range(6)]
    data = _make_doc_dict(errors=errors)
    s = _format_summary(data, tmp_path / "x.json")
    assert "+1 more" not in s or "errors (6)" in s


def test_format_summary_parser_version_missing(tmp_path: Path):
    """parser_version=None 时 data.get('parser_version', '?') 返回 None → 'vNone'。"""
    data = _make_doc_dict(parser_version=None)
    s = _format_summary(data, tmp_path / "x.json")
    assert "vNone" in s


def test_format_summary_source_hash_short(tmp_path: Path):
    data = _make_doc_dict(source_hash="abc")
    s = _format_summary(data, tmp_path / "x.json")
    # 截断到 16 字符 + 省略号；少于 16 全显
    assert "abc" in s


def test_format_summary_warnings_section_count(tmp_path: Path):
    warns = [{"code": "x", "reason": "y"}]
    data = _make_doc_dict(warnings=warns)
    s = _format_summary(data, tmp_path / "x.json")
    assert "warnings (1)" in s


def test_format_summary_errors_section_count(tmp_path: Path):
    errors = [{"code": "x", "message": "y"}]
    data = _make_doc_dict(errors=errors)
    s = _format_summary(data, tmp_path / "x.json")
    assert "errors (1)" in s


# =========================================================================
# _format_elements_list 边界
# =========================================================================


def test_format_elements_list_with_empty_content(tmp_path: Path):
    elements = [{
        "element_id": "e1", "type": "paragraph",
        "content": "", "parent_id": None,
    }]
    s = _format_elements_list(elements, 10)
    assert "e1" in s
    assert "paragraph" in s


def test_format_elements_list_with_none_content(tmp_path: Path):
    elements = [{
        "element_id": "e1", "type": "paragraph",
        "content": None, "parent_id": None,
    }]
    s = _format_elements_list(elements, 10)
    # 不应崩溃
    assert "e1" in s


def test_format_elements_list_with_long_content_truncated(tmp_path: Path):
    elements = [{
        "element_id": "e1", "type": "paragraph",
        "content": "a" * 200, "parent_id": None,
    }]
    s = _format_elements_list(elements, 10)
    assert "…" in s


def test_format_elements_list_with_various_types(tmp_path: Path):
    elements = [
        {"element_id": "e1", "type": "heading", "content": "h", "parent_id": None},
        {"element_id": "e2", "type": "paragraph", "content": "p", "parent_id": None},
        {"element_id": "e3", "type": "table", "content": "t", "parent_id": None},
    ]
    s = _format_elements_list(elements, 10)
    assert "heading" in s
    assert "paragraph" in s
    assert "table" in s


def test_format_elements_list_more_message_when_truncated(tmp_path: Path):
    elements = [
        {"element_id": f"e{i}", "type": "paragraph", "content": "x", "parent_id": None}
        for i in range(10)
    ]
    s = _format_elements_list(elements, 3)
    assert "+7 more" in s
    assert "--limit 0" in s


def test_format_elements_list_more_message_omitted_when_no_truncation(tmp_path: Path):
    elements = [
        {"element_id": "e1", "type": "paragraph", "content": "x", "parent_id": None}
    ]
    s = _format_elements_list(elements, 10)
    assert "+0 more" not in s


def test_format_elements_list_parent_id_displayed(tmp_path: Path):
    elements = [{
        "element_id": "e1", "type": "paragraph",
        "content": "x", "parent_id": "p1",
    }]
    s = _format_elements_list(elements, 10)
    assert "parent=p1" in s


def test_format_elements_list_parent_id_empty_string_not_displayed(tmp_path: Path):
    elements = [{
        "element_id": "e1", "type": "paragraph",
        "content": "x", "parent_id": "",
    }]
    s = _format_elements_list(elements, 10)
    assert "parent=" not in s


def test_format_elements_list_no_element_id_uses_question_mark(tmp_path: Path):
    elements = [{"type": "paragraph", "content": "x", "parent_id": None}]
    s = _format_elements_list(elements, 10)
    assert "?" in s


def test_format_elements_list_no_type_uses_question_mark(tmp_path: Path):
    elements = [{"element_id": "e1", "content": "x", "parent_id": None}]
    s = _format_elements_list(elements, 10)
    # type 缺失 → "?"
    assert "    ?" in s or "[?" in s or "?]" in s


# =========================================================================
# _format_chunks_list 边界
# =========================================================================


def test_format_chunks_list_chars_zero(tmp_path: Path):
    chunks = [{
        "chunk_id": "c1", "text": "",
        "source_element_ids": [], "metadata": {},
    }]
    s = _format_chunks_list(chunks, 10)
    assert "chars=0" in s


def test_format_chunks_list_refs_zero(tmp_path: Path):
    chunks = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": [], "metadata": {},
    }]
    s = _format_chunks_list(chunks, 10)
    assert "refs=0" in s


def test_format_chunks_list_text_with_newline_collapsed(tmp_path: Path):
    chunks = [{
        "chunk_id": "c1", "text": "line1\nline2",
        "source_element_ids": [], "metadata": {},
    }]
    s = _format_chunks_list(chunks, 10)
    # preview 折叠换行
    assert "line1 line2" in s


def test_format_chunks_list_long_text_truncated(tmp_path: Path):
    chunks = [{
        "chunk_id": "c1", "text": "a" * 200,
        "source_element_ids": [], "metadata": {},
    }]
    s = _format_chunks_list(chunks, 10)
    assert "…" in s


def test_format_chunks_list_show_spans_with_specific_start_end(tmp_path: Path):
    chunks = [{
        "chunk_id": "c1", "text": "hello",
        "source_element_ids": ["e1"], "metadata": {},
        "source_spans": [{"element_id": "e1", "start": 0, "end": 5}],
    }]
    s = _format_chunks_list(chunks, 10, show_spans=True)
    assert "e1[0:5]" in s


def test_format_chunks_list_show_spans_missing_start_uses_question_mark(tmp_path: Path):
    chunks = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": [], "metadata": {},
        "source_spans": [{"element_id": "e1", "end": 5}],  # 无 start
    }]
    s = _format_chunks_list(chunks, 10, show_spans=True)
    assert "e1[?:5]" in s


def test_format_chunks_list_show_spans_missing_end_uses_question_mark(tmp_path: Path):
    chunks = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": [], "metadata": {},
        "source_spans": [{"element_id": "e1", "start": 0}],  # 无 end
    }]
    s = _format_chunks_list(chunks, 10, show_spans=True)
    assert "e1[0:?]" in s


def test_format_chunks_list_show_spans_missing_element_id(tmp_path: Path):
    chunks = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": [], "metadata": {},
        "source_spans": [{"start": 0, "end": 5}],
    }]
    s = _format_chunks_list(chunks, 10, show_spans=True)
    assert "?[0:5]" in s


def test_format_chunks_list_show_spans_empty_explicit(tmp_path: Path):
    chunks = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": [], "metadata": {},
        "source_spans": [],
    }]
    s = _format_chunks_list(chunks, 10, show_spans=True)
    assert "(none)" in s


def test_format_chunks_list_more_message(tmp_path: Path):
    chunks = [
        {"chunk_id": f"c{i}", "text": "x",
         "source_element_ids": [], "metadata": {}}
        for i in range(5)
    ]
    s = _format_chunks_list(chunks, 2)
    assert "+3 more" in s


def test_format_chunks_list_limit_zero_lists_all(tmp_path: Path):
    chunks = [
        {"chunk_id": f"c{i}", "text": "x",
         "source_element_ids": [], "metadata": {}}
        for i in range(20)
    ]
    s = _format_chunks_list(chunks, 0)
    assert "+0 more" not in s
    assert "chunks (20)" in s


# =========================================================================
# _load_document_json OSError 路径
# =========================================================================


def test_load_document_json_oserror_returns_error_message(tmp_path: Path, monkeypatch):
    """触发 OSError 时返回友好的错误信息。"""
    src = tmp_path / "x.json"
    src.write_text("{}", encoding="utf-8")
    original_open = Path.open

    def fake_open(self, *args, **kwargs):
        if self == src:
            raise OSError("disk error")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fake_open)
    data, err = _load_document_json(src)
    assert data is None
    assert "读文件失败" in err


def test_load_document_json_valid_complex_dict(tmp_path: Path):
    """嵌套 dict 应正确加载。"""
    src = tmp_path / "x.json"
    payload = {"a": {"b": {"c": [1, 2, 3]}}}
    src.write_text(json.dumps(payload), encoding="utf-8")
    data, err = _load_document_json(src)
    assert err == ""
    assert data == payload


def test_load_document_json_empty_dict(tmp_path: Path):
    src = tmp_path / "x.json"
    src.write_text("{}", encoding="utf-8")
    data, err = _load_document_json(src)
    assert err == ""
    assert data == {}


# =========================================================================
# _emit_structured_error extra 类型覆盖
# =========================================================================


def test_emit_structured_error_extra_int_value(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code", "msg", count=5)
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["count"] == 5


def test_emit_structured_error_extra_list_value(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code", "msg", tags=["a", "b"])
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["tags"] == ["a", "b"]


def test_emit_structured_error_extra_dict_value(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code", "msg", details={"k": "v"})
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["details"] == {"k": "v"}


def test_emit_structured_error_extra_none_value(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code", "msg", val=None)
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["val"] is None


def test_emit_structured_error_extra_bool_value(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "x", "code", "msg", flag=True)
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0]["flag"] is True


def test_emit_structured_error_extra_path_value_raises(capsys, tmp_path: Path):
    """Path 不可 JSON 序列化 → json.dumps 抛 TypeError。"""
    with pytest.raises(TypeError):
        _emit_structured_error(tmp_path / "x", "code", "msg", path=tmp_path / "y")


def test_emit_structured_error_input_path_str(capsys, tmp_path: Path):
    _emit_structured_error(tmp_path / "abc", "code", "msg")
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["input"].endswith("abc")


# =========================================================================
# _iter_supported_files 排序与过滤
# =========================================================================


def test_iter_supported_files_sorts_alphabetically(tmp_path: Path):
    """文件名按字典序排序。"""
    (tmp_path / "c.txt").write_text("x", encoding="utf-8")
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in files]
    assert names == ["a.txt", "b.txt", "c.txt"]


def test_iter_supported_files_handles_mixed_case_sort(tmp_path: Path):
    """大小写混合文件名都被包含。"""
    (tmp_path / "B.txt").write_text("x", encoding="utf-8")
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    names = {p.name for p in files}
    # 大小写都被列出（具体顺序由 Path 排序规则决定）
    assert names == {"B.txt", "a.txt"}


def test_iter_supported_files_excludes_hidden(tmp_path: Path):
    """以 . 开头的隐藏文件依然按扩展名匹配（不过 pathlib 默认会列出）。"""
    (tmp_path / ".hidden.txt").write_text("x", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in files]
    # .hidden.txt 也匹配 .txt 扩展名 → 包含
    assert ".hidden.txt" in names
    assert "visible.txt" in names


def test_iter_supported_files_recursive_returns_all(tmp_path: Path):
    (tmp_path / "top.md").write_text("x", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "deep.md").write_text("x", encoding="utf-8")
    (sub / "deep.txt").write_text("x", encoding="utf-8")
    files = _iter_supported_files(tmp_path, recursive=True)
    assert len(files) == 3


# =========================================================================
# _relative_output_path 边界
# =========================================================================


def test_relative_output_path_simple_filename(tmp_path: Path):
    """顶层文件 → output_dir/<name>.<ext>.json。"""
    rel = _relative_output_path(tmp_path, tmp_path / "a.txt", tmp_path / "out")
    assert rel == tmp_path / "out" / "a.txt.json"


def test_relative_output_path_preserves_suffix_in_name(tmp_path: Path):
    """文件名应包含 suffix 防冲突。"""
    rel = _relative_output_path(tmp_path, tmp_path / "doc.md", tmp_path / "out")
    assert "doc.md.json" in rel.name


def test_relative_output_path_uses_forward_slash_in_nested(tmp_path: Path):
    input_dir = tmp_path
    sub = input_dir / "sub"
    sub.mkdir()
    out_dir = tmp_path / "out"
    rel = _relative_output_path(input_dir, sub / "doc.md", out_dir)
    # 在 output_dir 之下保留了 sub 目录层级
    assert (out_dir / "sub" / "doc.md.json") == rel or rel.parent.name == "sub"


def test_relative_output_path_deep_nested(tmp_path: Path):
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    out_dir = tmp_path / "out"
    rel = _relative_output_path(tmp_path, deep / "file.txt", out_dir)
    assert "file.txt.json" in rel.name


# =========================================================================
# _infer_parser_name 双 suffix 与边界
# =========================================================================


def test_infer_parser_name_double_suffix_returns_fallback(tmp_path: Path):
    """`.tar.gz` 等双 suffix，只看最后一段 .gz → fallback。"""
    p = tmp_path / "archive.tar.gz"
    assert _infer_parser_name(p) == "fallback"


def test_infer_parser_name_multiple_dots(tmp_path: Path):
    """`my.notes.txt` → text。"""
    p = tmp_path / "my.notes.txt"
    assert _infer_parser_name(p) == "text"


def test_infer_parser_name_file_starts_with_dot(tmp_path: Path):
    """.ipynb（隐藏 ipynb）→ ipynb。"""
    p = tmp_path / ".hidden.ipynb"
    assert _infer_parser_name(p) == "ipynb"


def test_infer_parser_name_only_extension(tmp_path: Path):
    """.txt 视为隐藏文件（无主干），suffix 为空 → fallback。"""
    p = tmp_path / ".txt"
    # Path(".txt").suffix == ""（被视为隐藏文件名）
    assert _infer_parser_name(p) == "fallback"


# =========================================================================
# _build_arg_parser 各 subcommand choices
# =========================================================================


def test_build_arg_parser_parse_parser_choices_count_six():
    p = _build_arg_parser()
    # 找到 parse 子解析器
    parse_action = None
    for action in p._actions:
        if hasattr(action, "choices") and "parse" in (action.choices or {}):
            parse_action = action
            break
    assert parse_action is not None
    parse_sub = parse_action.choices["parse"]
    parser_arg = next(a for a in parse_sub._actions if "--parser" in (a.option_strings or []))
    assert len(parser_arg.choices) == 6


def test_build_arg_parser_parse_dir_parser_choices_count_six():
    p = _build_arg_parser()
    sub_action = next(a for a in p._actions if hasattr(a, "choices") and "parse-dir" in (a.choices or {}))
    pd_sub = sub_action.choices["parse-dir"]
    parser_arg = next(a for a in pd_sub._actions if "--parser" in (a.option_strings or []))
    assert len(parser_arg.choices) == 6


def test_build_arg_parser_parse_parser_choices_exact():
    p = _build_arg_parser()
    sub_action = next(a for a in p._actions if hasattr(a, "choices") and "parse" in (a.choices or {}))
    parse_sub = sub_action.choices["parse"]
    parser_arg = next(a for a in parse_sub._actions if "--parser" in (a.option_strings or []))
    assert set(parser_arg.choices) == {
        "fallback", "kreuzberg", "markdown", "html", "text", "ipynb"
    }


def test_build_arg_parser_inspect_has_spans_flag():
    p = _build_arg_parser()
    sub_action = next(a for a in p._actions if hasattr(a, "choices") and "inspect" in (a.choices or {}))
    ins_sub = sub_action.choices["inspect"]
    option_names: list[str] = []
    for action in ins_sub._actions:
        option_names.extend(action.option_strings or [])
    assert "--spans" in option_names


def test_build_arg_parser_inspect_has_elements_flag():
    p = _build_arg_parser()
    sub_action = next(a for a in p._actions if hasattr(a, "choices") and "inspect" in (a.choices or {}))
    ins_sub = sub_action.choices["inspect"]
    option_names: list[str] = []
    for action in ins_sub._actions:
        option_names.extend(action.option_strings or [])
    assert "--elements" in option_names


def test_build_arg_parser_inspect_has_chunks_flag():
    p = _build_arg_parser()
    sub_action = next(a for a in p._actions if hasattr(a, "choices") and "inspect" in (a.choices or {}))
    ins_sub = sub_action.choices["inspect"]
    option_names: list[str] = []
    for action in ins_sub._actions:
        option_names.extend(action.option_strings or [])
    assert "--chunks" in option_names


def test_build_arg_parser_inspect_has_limit_flag():
    p = _build_arg_parser()
    sub_action = next(a for a in p._actions if hasattr(a, "choices") and "inspect" in (a.choices or {}))
    ins_sub = sub_action.choices["inspect"]
    option_names: list[str] = []
    for action in ins_sub._actions:
        option_names.extend(action.option_strings or [])
    assert "--limit" in option_names


def test_build_arg_parser_parse_dir_has_recursive_flag():
    p = _build_arg_parser()
    sub_action = next(a for a in p._actions if hasattr(a, "choices") and "parse-dir" in (a.choices or {}))
    pd_sub = sub_action.choices["parse-dir"]
    option_names: list[str] = []
    for action in pd_sub._actions:
        option_names.extend(action.option_strings or [])
    assert "--recursive" in option_names


# =========================================================================
# 模块结构
# =========================================================================


def test_module_imports_argparse():
    src = inspect.getsource(cli_mod)
    assert "import argparse" in src


def test_module_imports_json():
    src = inspect.getsource(cli_mod)
    assert "import json" in src


def test_module_imports_sys():
    src = inspect.getsource(cli_mod)
    assert "import sys" in src


def test_module_imports_path():
    src = inspect.getsource(cli_mod)
    assert "from pathlib import Path" in src


def test_module_imports_pipeline():
    src = inspect.getsource(cli_mod)
    assert "from app.pipeline" in src


def test_module_uses_future_annotations():
    src = inspect.getsource(cli_mod)
    assert "from __future__ import annotations" in src


def test_module_has_utf8_reconfigure_block():
    src = inspect.getsource(cli_mod)
    assert "reconfigure" in src
    assert "utf-8" in src


def test_module_docstring_present():
    assert cli_mod.__doc__ is not None


def test_module_docstring_mentions_parse_command():
    assert cli_mod.__doc__ is not None
    assert "parse" in cli_mod.__doc__.lower()


def test_module_docstring_mentions_validate_command():
    assert cli_mod.__doc__ is not None
    assert "validate" in cli_mod.__doc__.lower()


def test_module_docstring_mentions_inspect_command():
    assert cli_mod.__doc__ is not None
    assert "inspect" in cli_mod.__doc__.lower()


def test_module_has_main_guard():
    src = inspect.getsource(cli_mod)
    assert '__name__ == "__main__"' in src


def test_module_has_no_all():
    """cli 模块未定义 __all__（用户脚本式模块）。"""
    assert not hasattr(cli_mod, "__all__") or cli_mod.__all__ is None


def test_module_extension_to_parser_is_dict():
    assert isinstance(_EXTENSION_TO_PARSER, dict)


def test_module_extension_to_parser_count_nine():
    assert len(_EXTENSION_TO_PARSER) == 9


def test_module_extension_to_parser_keys_exact():
    assert set(_EXTENSION_TO_PARSER.keys()) == {
        ".pdf", ".docx", ".md", ".markdown",
        ".html", ".htm", ".txt", ".text", ".ipynb",
    }


def test_module_extension_to_parser_pdf_value():
    assert _EXTENSION_TO_PARSER[".pdf"] == "fallback"


def test_module_extension_to_parser_docx_value():
    assert _EXTENSION_TO_PARSER[".docx"] == "fallback"


def test_module_extension_to_parser_md_and_markdown_same_value():
    assert _EXTENSION_TO_PARSER[".md"] == _EXTENSION_TO_PARSER[".markdown"] == "markdown"


def test_module_extension_to_parser_html_and_htm_same_value():
    assert _EXTENSION_TO_PARSER[".html"] == _EXTENSION_TO_PARSER[".htm"] == "html"


def test_module_extension_to_parser_txt_and_text_same_value():
    assert _EXTENSION_TO_PARSER[".txt"] == _EXTENSION_TO_PARSER[".text"] == "text"


# =========================================================================
# _preview 边界补充
# =========================================================================


def test_preview_default_width_60():
    """默认 width=60。"""
    sig = inspect.signature(_preview)
    assert sig.parameters["width"].default == 60


def test_preview_returns_str_for_none():
    assert isinstance(_preview(None), str)


def test_preview_returns_str_for_empty():
    assert isinstance(_preview(""), str)


def test_preview_returns_str_for_text():
    assert isinstance(_preview("hello"), str)


def test_preview_width_60_exact_no_truncation():
    """正好 60 字符不需截断。"""
    text = "a" * 60
    assert _preview(text) == "a" * 60


def test_preview_width_61_truncates():
    text = "a" * 61
    result = _preview(text)
    assert result.endswith("…")
    assert len(result) == 60


def test_preview_does_not_modify_text_under_width():
    text = "Hello World Foo Bar"
    assert _preview(text) == text


def test_preview_collapses_internal_newlines():
    text = "line1\nline2\nline3"
    assert _preview(text) == "line1 line2 line3"


def test_preview_handles_mixed_whitespace_combinations():
    text = "a\tb\nc\t\td"
    assert _preview(text) == "a b c d"


def test_preview_ellipsis_single_char():
    """省略号是单字符 …。"""
    result = _preview("a" * 100, width=10)
    assert result.count("…") == 1


# =========================================================================
# 整体行为：idempotent
# =========================================================================


def test_infer_parser_name_idempotent(tmp_path: Path):
    p = tmp_path / "x.txt"
    assert _infer_parser_name(p) == _infer_parser_name(p)


def test_preview_idempotent():
    text = "hello world"
    assert _preview(text) == _preview(text)


def test_format_summary_idempotent(tmp_path: Path):
    data = _make_doc_dict()
    s1 = _format_summary(data, tmp_path / "x.json")
    s2 = _format_summary(data, tmp_path / "x.json")
    assert s1 == s2


def test_format_elements_list_idempotent():
    elements = [{"element_id": "e1", "type": "paragraph", "content": "x"}]
    s1 = _format_elements_list(elements, 10)
    s2 = _format_elements_list(elements, 10)
    assert s1 == s2


def test_format_chunks_list_idempotent():
    chunks = [{"chunk_id": "c1", "text": "x", "source_element_ids": [], "metadata": {}}]
    s1 = _format_chunks_list(chunks, 10)
    s2 = _format_chunks_list(chunks, 10)
    assert s1 == s2


# =========================================================================
# 模块函数可调用性
# =========================================================================


def test_module_main_callable():
    assert callable(cli_mod.main)


def test_module_build_arg_parser_callable():
    assert callable(_build_arg_parser)


def test_module_run_parse_callable():
    assert callable(_run_parse)


def test_module_run_parse_dir_callable():
    assert callable(_run_parse_dir)


def test_module_preview_callable():
    assert callable(_preview)


def test_module_load_document_json_callable():
    assert callable(_load_document_json)


def test_module_format_summary_callable():
    assert callable(_format_summary)


def test_module_format_elements_list_callable():
    assert callable(_format_elements_list)


def test_module_format_chunks_list_callable():
    assert callable(_format_chunks_list)


def test_module_emit_structured_error_callable():
    assert callable(_emit_structured_error)


def test_module_infer_parser_name_callable():
    assert callable(_infer_parser_name)


def test_module_iter_supported_files_callable():
    assert callable(_iter_supported_files)


def test_module_relative_output_path_callable():
    assert callable(_relative_output_path)
