r"""evaluation/runner.py 边角测试 - 第八轮（Round 194）。

补强已有 base/edges/edges2-7（共 635 测试）未覆盖的深度：
- _load_annotation 各 JSON value 类型 + 大文件 + 文件带 BOM
- _process_one monkeypatch process_single 模拟 (None, []) / 多 errors / parser_version None
- run_evaluation public_per_doc 严格剥离私有字段
- run_evaluation image_base_dir None 分支（image_dir 非 dir 时）
- run_evaluation tolerance_chars 传播
- run_evaluation parser_version_for_prov 多 doc 行为
- run_evaluation report 文件落盘与内存对象一致
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION
from evaluation.runner import (
    _load_annotation,
    _process_one,
    run_evaluation,
)


# =========================================================================
# _load_annotation JSON 内容多样性
# =========================================================================


def test_load_annotation_returns_list_value(tmp_path: Path):
    """JSON 顶层是 list 也接受（dict[str, Any] 注解但 json.load 接受任意）。"""
    p = tmp_path / "a.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, list)
    assert result == [1, 2, 3]


def test_load_annotation_returns_int_value(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("42", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 42


def test_load_annotation_returns_string_value(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('"hello"', encoding="utf-8")
    result = _load_annotation(p)
    assert result == "hello"


def test_load_annotation_returns_null_value(tmp_path: Path):
    """JSON null → Python None；但函数返回 None 也表示加载失败。需区分。"""
    p = tmp_path / "a.json"
    p.write_text("null", encoding="utf-8")
    result = _load_annotation(p)
    # json.load returns None for "null"，与失败路径返回值相同，但路径有效
    assert result is None


def test_load_annotation_returns_nested_dict(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"outer": {"inner": [1, {"x": "y"}]}}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"outer": {"inner": [1, {"x": "y"}]}}


def test_load_annotation_returns_empty_dict(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    result = _load_annotation(p)
    assert result == {}


def test_load_annotation_returns_empty_list(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("[]", encoding="utf-8")
    result = _load_annotation(p)
    assert result == []


def test_load_annotation_with_bom(tmp_path: Path):
    """encoding='utf-8' 不剥离 BOM → json.JSONDecodeError → 返回 None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": "v"}')
    result = _load_annotation(p)
    # BOM 让 json 解析失败 → None
    assert result is None


def test_load_annotation_unicode_content(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"name": "中文"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"name": "中文"}


def test_load_annotation_large_file(tmp_path: Path):
    """大文件（10k entries）。"""
    data = {f"key_{i}": i for i in range(10000)}
    p = tmp_path / "big.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    result = _load_annotation(p)
    assert len(result) == 10000
    assert result["key_9999"] == 9999


def test_load_annotation_truncated_json_returns_none(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"', encoding="utf-8")  # 缺右括号
    assert _load_annotation(p) is None


def test_load_annotation_extra_data_returns_none(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"} extra', encoding="utf-8")  # 尾部多余
    assert _load_annotation(p) is None


def test_load_annotation_empty_file_returns_none(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_only_whitespace_returns_none(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("   \n  \t ", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_true_value(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("true", encoding="utf-8")
    assert _load_annotation(p) is True


def test_load_annotation_false_value(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("false", encoding="utf-8")
    assert _load_annotation(p) is False


def test_load_annotation_float_value(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("3.14", encoding="utf-8")
    assert _load_annotation(p) == 3.14


# =========================================================================
# _process_one monkeypatch process_single 路径
# =========================================================================


class _FakeDoc:
    """模拟 DocumentEntry。"""

    def __init__(self, path: Path, doc_id: str = "doc-x", source_type: str = "text",
                 expectations: dict | None = None, annotation_resolved: Path | None = None):
        self.resolved_path = path
        self.doc_id = doc_id
        self.source_type = source_type
        self.expectations = expectations
        self.annotation_resolved = annotation_resolved


class _FakeManifest:
    """模拟 Manifest。"""

    def __init__(self, tmp_path: Path, docs=None, efs=None):
        self.project_root = tmp_path
        self.documents = docs or []
        self.expected_failures = efs or []
        self.devset_status = "incomplete"
        self.file_count = 0
        self.pdf_count = 0
        self.docx_count = 0
        self.content_group_count = 0
        self.categories_covered = []


class _FakeExpectedFailure:
    def __init__(self, path: Path, doc_id: str = "ef1",
                 expected_error_code: str = "file_not_found"):
        self.resolved_path = path
        self.doc_id = doc_id
        self.expected_error_code = expected_error_code


class _FakeError:
    def __init__(self, code: str = "X", message: str = "boom"):
        self.code = code
        self.message = message

    def to_dict(self):
        return {"code": self.code, "message": self.message}


class _FakeDocument:
    def __init__(self, source_hash: str = "a" * 64, parser_version: str = "v1"):
        self.source_hash = source_hash
        self.parser_version = parser_version

    def to_dict(self):
        return {
            "source_hash": self.source_hash,
            "source_type": "text",
            "document_id": "doc-x",
            "elements": [],
            "chunks": [],
            "warnings": [],
            "parser_name": "text",
            "parser_version": self.parser_version,
        }


def test_process_one_no_errors_no_document_returns_unknown(tmp_path: Path,
                                                             monkeypatch):
    """process_single 返回 (None, []) → _process_one 返回 unknown error。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p)

    def fake_process_single(*args, **kwargs):
        return None, []

    import evaluation.runner as runner_mod
    monkeypatch.setattr(runner_mod, "process_single", fake_process_single)
    document_dict, error_dict, _, _, _ = _process_one(doc, tmp_path, "text", 800)
    assert document_dict is None
    assert error_dict is not None
    assert error_dict["code"] == "unknown"
    assert "process_single returned None" in error_dict["message"]


def test_process_one_errors_take_precedence_over_document(tmp_path: Path, monkeypatch):
    """process_single 返回 (document, [err]) → 走 errors 分支，document 被丢弃。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p)
    fake_doc = _FakeDocument()
    fake_err = _FakeError(code="PARSE_FAILED")

    def fake_process_single(*args, **kwargs):
        return fake_doc, [fake_err]

    import evaluation.runner as runner_mod
    monkeypatch.setattr(runner_mod, "process_single", fake_process_single)
    document_dict, error_dict, _, parser_version, _ = _process_one(
        doc, tmp_path, "text", 800
    )
    assert document_dict is None
    assert error_dict == {"code": "PARSE_FAILED", "message": "boom"}
    assert parser_version is None  # 走 errors 分支 → parser_version=None


def test_process_one_returns_first_error_when_multiple(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p)
    err1 = _FakeError(code="FIRST")
    err2 = _FakeError(code="SECOND")

    def fake_process_single(*args, **kwargs):
        return None, [err1, err2]

    import evaluation.runner as runner_mod
    monkeypatch.setattr(runner_mod, "process_single", fake_process_single)
    _, error_dict, _, _, _ = _process_one(doc, tmp_path, "text", 800)
    assert error_dict["code"] == "FIRST"


def test_process_one_success_returns_document_dict(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p)
    fake_doc = _FakeDocument(parser_version="v9.9")

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    import evaluation.runner as runner_mod
    monkeypatch.setattr(runner_mod, "process_single", fake_process_single)
    document_dict, error_dict, _, parser_version, _ = _process_one(
        doc, tmp_path, "text", 800
    )
    assert document_dict is not None
    assert document_dict["parser_version"] == "v9.9"
    assert error_dict is None
    assert parser_version == "v9.9"


def test_process_one_image_dir_none_when_document_none(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p)

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError()]

    import evaluation.runner as runner_mod
    monkeypatch.setattr(runner_mod, "process_single", fake_process_single)
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "text", 800)
    assert image_dir is None


def test_process_one_creates_per_doc_dir_even_on_failure(tmp_path: Path):
    """失败时 out_stub.parent.mkdir 仍被调用。"""
    p = tmp_path / "missing.txt"
    doc = _FakeDoc(p)
    output_root = tmp_path / "out"
    _process_one(doc, output_root, "text", 800)
    assert (output_root / "_per_doc").is_dir()


def test_process_one_out_stub_unlinks_after_failure(tmp_path: Path):
    """失败路径同样清理 out_stub。"""
    p = tmp_path / "missing.txt"
    doc = _FakeDoc(p, doc_id="d_fail")
    output_root = tmp_path / "out"
    _process_one(doc, output_root, "text", 800)
    stub = output_root / "_per_doc" / "d_fail.json"
    assert not stub.is_file()


def test_process_one_total_seconds_nonzero_after_some_work(tmp_path: Path):
    """成功路径的 elapsed > 0（极快但通常仍 > 0）。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p)
    _, _, total, _, _ = _process_one(doc, tmp_path, "text", 800)
    assert total >= 0.0
    assert isinstance(total, float)


def test_process_one_calls_process_single_with_correct_args(tmp_path: Path,
                                                              monkeypatch):
    """验证 process_single 的关键字参数（parser_name/max_chars/write_json）。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p)

    captured_args = []

    def fake_process_single(path, output_path, *, parser_name, max_chars, write_json):
        captured_args.append({
            "path": path,
            "output_path": output_path,
            "parser_name": parser_name,
            "max_chars": max_chars,
            "write_json": write_json,
        })
        return _FakeDocument(), []

    import evaluation.runner as runner_mod
    monkeypatch.setattr(runner_mod, "process_single", fake_process_single)
    _process_one(doc, tmp_path, "custom_parser", 1234)
    assert len(captured_args) == 1
    args = captured_args[0]
    assert args["parser_name"] == "custom_parser"
    assert args["max_chars"] == 1234
    assert args["write_json"] is False


def test_process_one_out_stub_path_uses_doc_id(tmp_path: Path, monkeypatch):
    """out_stub = output_root / '_per_doc' / f'{doc_id}.json'。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p, doc_id="my_custom_id")

    captured = []

    def fake_process_single(path, output_path, **kwargs):
        captured.append(output_path)
        return _FakeDocument(), []

    import evaluation.runner as runner_mod
    monkeypatch.setattr(runner_mod, "process_single", fake_process_single)
    _process_one(doc, tmp_path, "text", 800)
    assert captured[0].name == "my_custom_id.json"
    assert captured[0].parent.name == "_per_doc"


def test_process_one_image_dir_uses_image_output_dir_for(tmp_path: Path, monkeypatch):
    """image_dir 通过 image_output_dir_for(out_stub, source_hash) 推导。"""
    from app.pipeline import image_output_dir_for
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    fake_doc = _FakeDocument(source_hash="b" * 64)
    doc = _FakeDoc(p)

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    import evaluation.runner as runner_mod
    monkeypatch.setattr(runner_mod, "process_single", fake_process_single)
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "text", 800)
    # image_dir 应等于 image_output_dir_for(out_stub, source_hash)
    expected = image_output_dir_for(
        tmp_path / "_per_doc" / "doc-x.json", "b" * 64
    )
    assert image_dir == expected


def test_process_one_unlink_silent_on_oserror(tmp_path: Path, monkeypatch):
    """out_stub.unlink 抛 OSError → 静默吞掉（pass）。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p)

    def fake_unlink(self):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "unlink", fake_unlink)
    # 不应抛
    _process_one(doc, tmp_path, "text", 800)


# =========================================================================
# run_evaluation public_per_doc 严格剥离私有字段
# =========================================================================


def _make_minimal_doc_file(tmp_path: Path, name: str = "x.txt") -> Path:
    p = tmp_path / name
    p.write_text("hello world paragraph content here.", encoding="utf-8")
    return p


def test_run_evaluation_per_doc_strips_annotation_present(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "_annotation_present" not in result["per_doc"][0]


def test_run_evaluation_per_doc_strips_tolerance_chars(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "_tolerance_chars" not in result["per_doc"][0]


def test_run_evaluation_per_doc_strips_missing_markers(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "_missing_markers" not in result["per_doc"][0]


def test_run_evaluation_per_doc_keeps_only_4_public_keys(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert set(result["per_doc"][0].keys()) == {
        "doc_id", "source_type", "metrics", "wall_time_seconds"
    }


def test_run_evaluation_per_doc_wall_time_total_only(tmp_path: Path):
    """per_doc.wall_time_seconds 含 total/parse/chunk/parse_reason/chunk_reason。"""
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert "total" in wt
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_report_contains_six_top_level_keys(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert set(result.keys()) == {
        "report_version", "provenance", "devset", "summary",
        "per_doc", "expected_failures"
    }


def test_run_evaluation_report_version_matches_constant(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["report_version"] == REPORT_VERSION


def test_run_evaluation_expected_failures_empty_by_default(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["expected_failures"] == []


# =========================================================================
# run_evaluation 空场景
# =========================================================================


def test_run_evaluation_empty_manifest_per_doc_empty(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["per_doc"] == []


def test_run_evaluation_empty_manifest_expected_failures_empty(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["expected_failures"] == []


def test_run_evaluation_no_docs_with_expected_failure_only(tmp_path: Path):
    ef_path = tmp_path / "missing.txt"
    manifest = _FakeManifest(
        tmp_path,
        docs=[],
        efs=[_FakeExpectedFailure(ef_path, doc_id="ef1")],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert len(result["expected_failures"]) == 1
    assert result["per_doc"] == []


def test_run_evaluation_multiple_docs(tmp_path: Path):
    p1 = tmp_path / "x1.txt"
    p1.write_text("content one", encoding="utf-8")
    p2 = tmp_path / "x2.txt"
    p2.write_text("content two", encoding="utf-8")
    manifest = _FakeManifest(
        tmp_path,
        docs=[
            _FakeDoc(p1, doc_id="d1"),
            _FakeDoc(p2, doc_id="d2"),
        ],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert len(result["per_doc"]) == 2
    doc_ids = {d["doc_id"] for d in result["per_doc"]}
    assert doc_ids == {"d1", "d2"}


# =========================================================================
# run_evaluation parser_version_for_prov 行为
# =========================================================================


def test_run_evaluation_provenance_parser_version_set_on_success(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["provenance"]["parser_version"] is not None


def test_run_evaluation_provenance_parser_version_none_when_all_fail(tmp_path: Path):
    """所有 doc 失败 → parser_version_for_prov 仍 None。"""
    missing = tmp_path / "missing.txt"
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(missing, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["provenance"]["parser_version"] is None


def test_run_evaluation_parser_version_takes_first_success(tmp_path: Path, monkeypatch):
    """多 doc：parser_version 取第一个成功的；后续失败不覆盖。"""
    p1 = tmp_path / "x1.txt"
    p1.write_text("ok", encoding="utf-8")
    p2 = tmp_path / "missing.txt"  # fail
    manifest = _FakeManifest(
        tmp_path,
        docs=[
            _FakeDoc(p1, doc_id="d1"),
            _FakeDoc(p2, doc_id="d2"),
        ],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    # 第一个成功 → version 已设；第二个失败不覆盖
    assert result["provenance"]["parser_version"] is not None


def test_run_evaluation_provenance_parser_name_propagated(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["provenance"]["parser_name"] == "text"


def test_run_evaluation_provenance_max_chars_propagated(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text", max_chars=4321)
    assert result["provenance"]["max_chars"] == 4321


# =========================================================================
# run_evaluation 落盘文件与内存对象一致
# =========================================================================


def test_run_evaluation_writes_file_to_disk(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    run_evaluation(manifest, output, parser_name="text")
    assert output.is_file()


def test_run_evaluation_file_content_matches_returned_dict(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    with output.open("r", encoding="utf-8") as f:
        disk = json.load(f)
    assert disk == result


def test_run_evaluation_creates_parent_dirs(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "deep" / "nested" / "report.json"
    run_evaluation(manifest, output, parser_name="text")
    assert output.is_file()


def test_run_evaluation_file_uses_utf8_with_unicode(tmp_path: Path):
    """报告文件应是合法 UTF-8（可被 decode）。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world ascii content", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    run_evaluation(manifest, output, parser_name="text")
    raw = output.read_bytes()
    # 报告可被 UTF-8 解码（不抛 UnicodeDecodeError）
    decoded = raw.decode("utf-8")
    assert "report_version" in decoded


def test_run_evaluation_file_is_indented(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    run_evaluation(manifest, output, parser_name="text")
    text = output.read_text(encoding="utf-8")
    assert "\n  " in text  # indent=2


# =========================================================================
# run_evaluation tolerance_chars
# =========================================================================


def test_run_evaluation_default_tolerance_chars_used(tmp_path: Path):
    """不传 tolerance_chars → 默认 30。"""
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    # chunk_boundary_metrics 应有 tolerance_chars=30（虽然 _tolerance_chars 字段被剥离）
    # 检查 metrics 内是否有相关项
    metrics = result["per_doc"][0]["metrics"]
    # 至少有 chunk_boundary_precision 等 key
    assert "chunk_boundary_precision" in metrics


def test_run_evaluation_custom_tolerance_chars(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    # tolerance_chars=100 应被接受
    result = run_evaluation(manifest, output, parser_name="text", tolerance_chars=100)
    assert "chunk_boundary_precision" in result["per_doc"][0]["metrics"]


def test_run_evaluation_signature_tolerance_chars_default_30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_signature_parser_name_default_fallback():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_signature_max_chars_default_800():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


# =========================================================================
# run_evaluation metrics 包含完整集合
# =========================================================================


def test_run_evaluation_metrics_includes_pipeline_metrics(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    metrics = result["per_doc"][0]["metrics"]
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert expected_keys.issubset(metrics.keys())


def test_run_evaluation_metrics_includes_annotation_metrics(tmp_path: Path):
    """metrics 包含 figure_caption / chunk_boundary 项（无 annotation 时各为 null）。"""
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    metrics = result["per_doc"][0]["metrics"]
    annotation_keys = {
        "figure_caption_precision", "figure_caption_recall",
        "chunk_boundary_precision", "chunk_boundary_recall",
    }
    assert annotation_keys.issubset(metrics.keys())


def test_run_evaluation_metrics_includes_silent_flag_when_no_annotation(tmp_path: Path):
    """无 annotation → chunk_boundary 含 _silent_drop 等（被剥离），
    metrics 中仍可看到 'no_annotation' reason。"""
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    metrics = result["per_doc"][0]["metrics"]
    # figure_caption_precision value 为 None（无 annotation）
    assert metrics["figure_caption_precision"]["value"] is None


# =========================================================================
# run_evaluation expected_failures 多场景
# =========================================================================


def test_run_evaluation_expected_failure_matches_other_code(tmp_path: Path):
    """expected='unsupported_type' 但 actual='file_not_found' → matches=False。"""
    p = _make_minimal_doc_file(tmp_path)
    ef_path = tmp_path / "missing.txt"
    manifest = _FakeManifest(
        tmp_path,
        docs=[_FakeDoc(p, doc_id="d1")],
        efs=[_FakeExpectedFailure(
            ef_path, doc_id="ef1",
            expected_error_code="unsupported_type",
        )],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    ef = result["expected_failures"][0]
    assert ef["expected_error_code"] == "unsupported_type"
    assert ef["actual_error_code"] == "file_not_found"
    assert ef["matches"] is False


def test_run_evaluation_expected_failure_multiple(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    ef1 = tmp_path / "missing1.txt"
    ef2 = tmp_path / "missing2.txt"
    manifest = _FakeManifest(
        tmp_path,
        docs=[_FakeDoc(p, doc_id="d1")],
        efs=[
            _FakeExpectedFailure(ef1, doc_id="ef1"),
            _FakeExpectedFailure(ef2, doc_id="ef2"),
        ],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert len(result["expected_failures"]) == 2


def test_run_evaluation_expected_failure_success_doc_no_actual_code(tmp_path: Path,
                                                                     monkeypatch):
    """EF doc 实际成功（无 errors） → actual_code=None，matches 取决于 expected。"""
    p = _make_minimal_doc_file(tmp_path)
    ef_path = tmp_path / "x_ef.txt"
    ef_path.write_text("ef content here.", encoding="utf-8")
    manifest = _FakeManifest(
        tmp_path,
        docs=[_FakeDoc(p, doc_id="d1")],
        efs=[_FakeExpectedFailure(
            ef_path, doc_id="ef1",
            expected_error_code="some_error",
        )],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    ef = result["expected_failures"][0]
    assert ef["actual_error_code"] is None
    assert ef["matches"] is False  # None != "some_error"


def test_run_evaluation_expected_failure_actual_code_present(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    ef_path = tmp_path / "missing.txt"
    manifest = _FakeManifest(
        tmp_path,
        docs=[_FakeDoc(p, doc_id="d1")],
        efs=[_FakeExpectedFailure(
            ef_path, doc_id="ef1",
            expected_error_code="file_not_found",
        )],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    ef = result["expected_failures"][0]
    assert ef["actual_error_code"] == "file_not_found"


# =========================================================================
# 模块结构与签名
# =========================================================================


def test_module_all_exports_run_evaluation():
    import evaluation.runner as m
    assert m.__all__ == ["run_evaluation"]


def test_module_imports_json():
    import evaluation.runner as m
    assert hasattr(m, "json")


def test_module_imports_time():
    import evaluation.runner as m
    assert hasattr(m, "time")


def test_module_imports_path():
    import evaluation.runner as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import evaluation.runner as m
    assert hasattr(m, "Any")


def test_module_imports_process_single():
    import evaluation.runner as m
    assert hasattr(m, "process_single")
    assert callable(m.process_single)


def test_module_imports_image_output_dir_for():
    import evaluation.runner as m
    assert hasattr(m, "image_output_dir_for")
    assert callable(m.image_output_dir_for)


def test_module_imports_report_version():
    import evaluation.runner as m
    assert hasattr(m, "REPORT_VERSION")


def test_module_imports_compute_automatic_metrics():
    import evaluation.runner as m
    assert hasattr(m, "compute_automatic_metrics")


def test_module_imports_chunk_boundary_prf():
    import evaluation.runner as m
    assert hasattr(m, "chunk_boundary_prf")


def test_module_imports_figure_caption_prf():
    import evaluation.runner as m
    assert hasattr(m, "figure_caption_prf")


def test_module_imports_aggregate_summary():
    import evaluation.runner as m
    assert hasattr(m, "aggregate_summary")


def test_module_imports_build_devset_section():
    import evaluation.runner as m
    assert hasattr(m, "build_devset_section")


def test_module_imports_build_provenance():
    import evaluation.runner as m
    assert hasattr(m, "build_provenance")


def test_load_annotation_signature():
    sig = inspect.signature(_load_annotation)
    assert set(sig.parameters) == {"path"}


def test_load_annotation_path_annotation():
    sig = inspect.signature(_load_annotation)
    annotation = str(sig.parameters["path"].annotation)
    assert "Path" in annotation
    assert "None" in annotation


def test_load_annotation_return_annotation():
    sig = inspect.signature(_load_annotation)
    annotation = str(sig.return_annotation)
    assert "dict" in annotation or "None" in annotation


def test_process_one_signature():
    sig = inspect.signature(_process_one)
    assert set(sig.parameters) == {"doc", "output_root", "parser_name", "max_chars"}


def test_process_one_return_annotation_tuple():
    sig = inspect.signature(_process_one)
    assert "tuple" in str(sig.return_annotation).lower()


def test_run_evaluation_signature_parameters():
    sig = inspect.signature(run_evaluation)
    assert set(sig.parameters) == {
        "manifest", "output_path", "parser_name",
        "max_chars", "tolerance_chars"
    }


def test_run_evaluation_manifest_param_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_run_evaluation_output_path_param_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


def test_run_evaluation_keyword_only_after_output_path():
    """parser_name/max_chars/tolerance_chars 是 keyword-only（在 * 之后）。"""
    sig = inspect.signature(run_evaluation)
    # manifest, output_path 是位置或关键字；其余是 keyword-only
    params = list(sig.parameters.values())
    found_star = False
    for p in params:
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            break
        if p.name == "parser_name":
            assert p.kind == inspect.Parameter.KEYWORD_ONLY
            found_star = True
    assert found_star


def test_run_evaluation_return_annotation_dict():
    sig = inspect.signature(run_evaluation)
    assert "dict" in str(sig.return_annotation)


def test_load_annotation_callable():
    assert callable(_load_annotation)


def test_process_one_callable():
    assert callable(_process_one)


def test_run_evaluation_callable():
    assert callable(run_evaluation)


# =========================================================================
# idempotency / 不变性
# =========================================================================


def test_load_annotation_idempotent(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": [1, 2, 3]}', encoding="utf-8")
    assert _load_annotation(p) == _load_annotation(p)


def test_run_evaluation_idempotent_identical_inputs(tmp_path: Path):
    """同样输入两次跑 → 报告内容应一致（数值字段稳定）。"""
    p1 = tmp_path / "x1.txt"
    p1.write_text("hello world content", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p1, doc_id="d1")])

    out1 = tmp_path / "out1" / "r.json"
    out2 = tmp_path / "out2" / "r.json"
    r1 = run_evaluation(manifest, out1, parser_name="text")
    r2 = run_evaluation(manifest, out2, parser_name="text")
    # 比较 per_doc 结构（不计 total 时间）
    assert r1["per_doc"][0]["doc_id"] == r2["per_doc"][0]["doc_id"]
    assert (
        r1["per_doc"][0]["metrics"]["element_count_total"]
        == r2["per_doc"][0]["metrics"]["element_count_total"]
    )


# =========================================================================
# 综合行为
# =========================================================================


def test_run_evaluation_real_text_pipeline(tmp_path: Path):
    """完整 text pipeline：单 txt 文件 → 报告含正确 metrics。"""
    p = tmp_path / "doc.txt"
    p.write_text("Hello World Paragraph Content.", encoding="utf-8")
    manifest = _FakeManifest(
        tmp_path,
        docs=[_FakeDoc(p, doc_id="d1", source_type="text")],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    pd = result["per_doc"][0]
    assert pd["doc_id"] == "d1"
    assert pd["source_type"] == "text"
    assert pd["metrics"]["pipeline_success"]["value"] is True
    assert pd["metrics"]["element_count_total"]["value"] >= 1


def test_run_evaluation_failed_doc_still_in_per_doc(tmp_path: Path):
    """失败 doc 仍出现在 per_doc（带 pipeline_failed reason）。"""
    missing = tmp_path / "missing.txt"
    manifest = _FakeManifest(
        tmp_path,
        docs=[_FakeDoc(missing, doc_id="d1")],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    pd = result["per_doc"][0]
    assert pd["metrics"]["pipeline_success"]["value"] is False
    assert pd["metrics"]["error_code"]["value"] == "file_not_found"
    assert pd["metrics"]["element_count_total"]["value"] is None


def test_run_evaluation_mixed_success_failure(tmp_path: Path):
    """混合 doc：一个成功一个失败。"""
    ok = tmp_path / "ok.txt"
    ok.write_text("hello world content", encoding="utf-8")
    bad = tmp_path / "bad.txt"  # 不存在
    manifest = _FakeManifest(
        tmp_path,
        docs=[
            _FakeDoc(ok, doc_id="d_ok"),
            _FakeDoc(bad, doc_id="d_bad"),
        ],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert len(result["per_doc"]) == 2
    by_id = {d["doc_id"]: d for d in result["per_doc"]}
    assert by_id["d_ok"]["metrics"]["pipeline_success"]["value"] is True
    assert by_id["d_bad"]["metrics"]["pipeline_success"]["value"] is False


def test_run_evaluation_summary_has_devset_section(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "devset" in result
    assert "status" in result["devset"]


def test_run_evaluation_summary_present(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "summary" in result


def test_run_evaluation_provenance_present(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "provenance" in result
    # provenance 含 evaluator_version / git_commit 等字段
    assert "evaluator_version" in result["provenance"]


def test_run_evaluation_per_doc_source_type_preserved(tmp_path: Path):
    p = _make_minimal_doc_file(tmp_path)
    manifest = _FakeManifest(
        tmp_path,
        docs=[_FakeDoc(p, doc_id="d1", source_type="custom_source")],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["per_doc"][0]["source_type"] == "custom_source"
